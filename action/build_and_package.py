#!/usr/bin/env python3
"""
Packages a PlatformIO project's already-built example environments into a self-contained
GitHub Pages-ready folder: this repo's web app (index.html/wizard.html/config.js/videos),
a manifest.json describing each example (name/description/variables/hardware/custom
videos from the consuming repo's flasher-manifest.yml, files/offsets discovered from the
PlatformIO build output) plus an optional site-wide branding block (also from
flasher-manifest.yml's `site:` key - title/subtitle/video overrides applied regardless
of which firmware is selected), and the compiled binaries themselves. manifest.json's
shape is `{"site": {...}, "firmwares": {"env_name": {...}, ...}}`.

Expects `pio run` to have already been run in the consuming repo (this script only
collects and packages its output - it doesn't invoke PlatformIO itself, so it works the
same whether called from the reusable Action or run locally to preview a build).

Usage: build_and_package.py --project-dir . --output-dir docs
"""
import argparse
import configparser
import json
import os
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required (pip install pyyaml)")

# Standard ESP32 Arduino/PlatformIO merged-image flash offsets. bootloader.bin is the
# one exception - its offset depends on the target chip (see BOOTLOADER_OFFSET_BY_MCU
# below); the value here is only the fallback used when a board's MCU can't be
# determined at all.
FLASH_OFFSETS = {
    "bootloader.bin": 0x0000,
    "partitions.bin": 0x8000,
    "boot_app0.bin": 0xE000,
    "firmware.bin": 0x10000,
}
# The second-stage bootloader's flash offset is chip-specific, not a fixed constant:
# ESP32/S2's ROM loader looks for it at 0x1000, while S3/C-series/H-series look at 0x0
# (P4 differs again, at 0x2000, listed here for completeness even though nothing in
# this repo's boards uses it yet). Getting this wrong doesn't fail the flash write -
# esptool happily writes bootloader.bin whatever offset it's told - it fails at boot:
# the chip's ROM can't find a valid image header at ITS fixed lookup offset, prints
# "invalid header: 0x......." on repeat, and watchdog-resets in a loop forever. This
# was hit for real: FLASH_OFFSETS used to hardcode 0x0 unconditionally (correct for
# this repo's original S3 boards, e.g. "T-Display-AMOLED" -> mcu esp32s3), which
# silently corrupted flashing for a later-added plain-ESP32 board ("esp32dev", mcu
# esp32) with exactly that symptom.
BOOTLOADER_OFFSET_BY_MCU = {
    "esp32": 0x1000,
    "esp32s2": 0x1000,
    "esp32s3": 0x0000,
    "esp32c2": 0x0000,
    "esp32c3": 0x0000,
    "esp32c6": 0x0000,
    "esp32h2": 0x0000,
    "esp32p4": 0x2000,
}
WEBAPP_ASSETS = ["index.html", "wizard.html", "config.js", "boot_mode.webm", "reset_only.webm"]


def read_boards(project_dir: Path) -> tuple[dict, str]:
    """Maps env name -> board id by reading platformio.ini directly (no `pio` CLI call
    needed). Resolves `board` the same way PlatformIO itself does: an env's own
    `board =` wins if set; otherwise it's inherited via `extends = env:<name>` (which
    can chain - e.g. this repo's `env:webRAW-CYD` sets no board of its own at all,
    only `extends = env:webJPEG-CYD`, which does); if that still doesn't produce a
    board, [env] is consulted as a last resort - unconditionally, whether or not the
    section also has its own `extends`, since PlatformIO itself always implicitly
    merges [env] into every [env:*] section regardless of other inheritance. A
    section with no resolvable board anywhere gets None - get_board_mcu() already
    handles that by falling back to FLASH_OFFSETS' default and printing a warning,
    so this only needs to not crash on it (e.g. a cycle, or an extends target that
    doesn't exist).
    interpolation=None since we only need literal string values; PlatformIO's own
    `${env.foo}` syntax isn't ConfigParser's `%(foo)s` syntax, but disabling
    interpolation avoids any edge cases with unusual ini content."""
    ini_path = project_dir / "platformio.ini"
    if not ini_path.is_file():
        return {}, "boards"
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ini_path)

    def resolve_board(section: str, seen: set) -> str | None:
        if not parser.has_section(section) or section in seen:
            return None
        seen.add(section)
        own_board = parser.get(section, "board", fallback=None)
        if own_board:
            return own_board
        extends = parser.get(section, "extends", fallback=None)
        board = None
        if extends:
            # `extends` can be a comma/whitespace-separated list; PlatformIO applies
            # them left-to-right with later ones overriding earlier ones, so the
            # *last* one that actually resolves to a board wins - walk in order and
            # keep going.
            for target in extends.replace(",", " ").split():
                resolved = resolve_board(target, seen)
                if resolved:
                    board = resolved
        if board:
            return board
        # PlatformIO always implicitly merges the base [env] section into every
        # [env:*] section for options that section doesn't set itself - regardless
        # of whether it also uses `extends` for something else - so [env] is the
        # last fallback here too, not just when `extends` is absent. Without this,
        # a project where no [env:*] section repeats `board =` or `extends = env`
        # (which is most projects, since it's redundant for PlatformIO itself)
        # resolves to no board at all, and bootloader_offset silently falls back to
        # the wrong default for every environment - see the FLASH_OFFSETS comment
        # above for what that actually breaks.
        if section != "env":
            return resolve_board("env", seen)
        return None

    boards = {}
    for section in parser.sections():
        if section.startswith("env:"):
            env_name = section[len("env:"):]
            boards[env_name] = resolve_board(section, set())
    boards_dir = parser.get("platformio", "boards_dir", fallback="boards") if parser.has_section("platformio") else "boards"
    return boards, boards_dir


def get_board_mcu(board_id: str, project_dir: Path, boards_dir: str) -> str | None:
    """Resolves a PlatformIO board id (e.g. "esp32dev", "T-Display-AMOLED") to its
    `build.mcu` field (e.g. "esp32", "esp32s3") by locating that board's JSON
    definition. Checks the project's own custom boards_dir first (a custom board
    overrides a built-in one of the same name), then falls back to the boards/
    directory of whichever installed espressif32 platform package(s) `pio run` already
    populated under PIO's core dir - no `pio` CLI call needed, since the packages are
    already on disk by the time this script runs (after `pio run`)."""
    if not board_id:
        return None
    candidates = [project_dir / boards_dir / f"{board_id}.json"]
    core_dir = Path(os.environ.get("PLATFORMIO_CORE_DIR", str(Path.home() / ".platformio")))
    candidates += sorted(core_dir.glob(f"platforms/espressif32*/boards/{board_id}.json"))
    for path in candidates:
        if path.is_file():
            try:
                return json.loads(path.read_text()).get("build", {}).get("mcu")
            except (json.JSONDecodeError, OSError):
                continue
    return None


# Per-firmware fields copied through verbatim from flasher-manifest.yml if present -
# see that file's own comments, or README.md's manifest schema section, for what each
# one does in the web app. expectedBehavior is wizard.html-only (step 4's bulleted "What
# to Expect" list, with {variable} placeholders substituted with the values the user
# entered) - falls back to a single-item list built from `description` if not set.
# sourceUrl is an optional link (e.g. to the example's source or README on GitHub) shown
# on its firmware card/info panel, for users who want to see what they're about to flash.
# recommended (bool) sorts that firmware to the top of the list with a badge - at most
# one example should set this.
OPTIONAL_ENTRY_FIELDS = ["bootModeVideo", "resetVideo", "expectedBehavior", "sourceUrl", "recommended"]


def build_manifest(project_dir: Path, manifest_config_path: Path) -> tuple[dict, dict]:
    config = {}
    site = {}
    if manifest_config_path.is_file():
        parsed = yaml.safe_load(manifest_config_path.read_text()) or {}
        config = parsed.get("examples", {})
        site = parsed.get("site", {})

    pio_build_dir = project_dir / ".pio" / "build"
    if not pio_build_dir.is_dir():
        sys.exit(f"No .pio/build directory found under {project_dir} - run `pio run` first")

    boards, boards_dir = read_boards(project_dir)
    manifest = {}
    for env_dir in sorted(p for p in pio_build_dir.iterdir() if p.is_dir()):
        env_name = env_dir.name
        found = {name: env_dir / name for name in FLASH_OFFSETS if (env_dir / name).is_file()}
        if "firmware.bin" not in found:
            print(f"Skipping '{env_name}': no firmware.bin in {env_dir}")
            continue

        mcu = get_board_mcu(boards.get(env_name), project_dir, boards_dir)
        bootloader_offset = BOOTLOADER_OFFSET_BY_MCU.get(mcu)
        if bootloader_offset is None:
            bootloader_offset = FLASH_OFFSETS["bootloader.bin"]
            print(f"'{env_name}': unrecognized MCU {mcu!r} for board {boards.get(env_name)!r} - "
                  f"defaulting bootloader.bin to 0x{bootloader_offset:04x}, verify this is correct")
        offsets = {**FLASH_OFFSETS, "bootloader.bin": bootloader_offset}

        # boot_app0.bin is never in `found` (PlatformIO doesn't produce it - it's a
        # static file bundled with this Action, see copy_binaries()) but is always
        # present in the packaged output, so it's always listed here too.
        entry_config = config.get(env_name, {})
        files = [
            {"path": f"firmware/{env_name}/{name}", "offset": offsets[name]}
            for name in ["bootloader.bin", "partitions.bin", "boot_app0.bin", "firmware.bin"]
            if name in found or name == "boot_app0.bin"
        ]
        entry = {
            "name": entry_config.get("name", env_name),
            "description": entry_config.get("description", ""),
            "files": files,
        }
        # Lets the flasher UI gray out/sort firmwares the connected device's actual
        # chip (from esptool-js's own post-sync chip detection, not just the vendor
        # ID used to guess a reset strategy) can't run - e.g. don't offer an esp32s3
        # firmware once an esp32 has already answered the sync. None if the board's
        # MCU couldn't be resolved (see get_board_mcu()) - the UI should treat that as
        # "unknown, don't gate" rather than "known incompatible".
        if mcu:
            entry["mcu"] = mcu
        hardware = entry_config.get("hardware", boards.get(env_name))
        if hardware:
            entry["hardware"] = hardware
        if "variables" in entry_config:
            entry["variables"] = entry_config["variables"]
        for field in OPTIONAL_ENTRY_FIELDS:
            if field in entry_config:
                entry[field] = entry_config[field]

        manifest[env_name] = entry
        manifest[env_name]["_source_files"] = found  # consumed by copy step below, stripped after
    return manifest, site


def copy_binaries(manifest: dict, action_dir: Path, output_dir: Path):
    firmware_dir = output_dir / "firmware"
    boot_app0 = action_dir / "boot_app0.bin"

    for env_name, entry in manifest.items():
        dest_dir = firmware_dir / env_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        for name, src in entry.pop("_source_files").items():
            shutil.copyfile(src, dest_dir / name)

        dest_boot_app0 = dest_dir / "boot_app0.bin"
        if not dest_boot_app0.exists():
            shutil.copyfile(boot_app0, dest_boot_app0)


def copy_webapp(action_dir: Path, output_dir: Path):
    repo_root = action_dir.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    for asset in WEBAPP_ASSETS:
        src = repo_root / asset
        if src.is_file():
            shutil.copyfile(src, output_dir / asset)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest-config", type=Path, default=Path("flasher-manifest.yml"))
    args = parser.parse_args()

    action_dir = Path(__file__).resolve().parent
    project_dir = args.project_dir.resolve()
    output_dir = args.output_dir.resolve()

    manifest, site = build_manifest(project_dir, project_dir / args.manifest_config)
    if not manifest:
        sys.exit("No built environments with a firmware.bin found - nothing to package")

    copy_webapp(action_dir, output_dir)
    copy_binaries(manifest, action_dir, output_dir)

    output = {"site": site, "firmwares": manifest}
    (output_dir / "manifest.json").write_text(json.dumps(output, indent=2) + "\n")
    print(f"Packaged {len(manifest)} firmware(s) into {output_dir}")


if __name__ == "__main__":
    main()
