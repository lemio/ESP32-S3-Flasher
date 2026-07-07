#!/usr/bin/env python3
"""
Packages a PlatformIO project's already-built example environments into a self-contained
GitHub Pages-ready folder: this repo's web app (index.html/wizard.html/config.js/videos),
a manifest.json describing each example (name/description/variables from the consuming
repo's flasher-manifest.yml, files/offsets discovered from the PlatformIO build output),
and the compiled binaries themselves.

Expects `pio run` to have already been run in the consuming repo (this script only
collects and packages its output - it doesn't invoke PlatformIO itself, so it works the
same whether called from the reusable Action or run locally to preview a build).

Usage: build_and_package.py --project-dir . --output-dir docs
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required (pip install pyyaml)")

# Standard ESP32 Arduino/PlatformIO merged-image flash offsets.
FLASH_OFFSETS = {
    "bootloader.bin": 0x0000,
    "partitions.bin": 0x8000,
    "boot_app0.bin": 0xE000,
    "firmware.bin": 0x10000,
}
WEBAPP_ASSETS = ["index.html", "wizard.html", "config.js", "boot_mode.webm", "reset_only.webm"]


def build_manifest(project_dir: Path, manifest_config_path: Path) -> dict:
    config = {}
    if manifest_config_path.is_file():
        config = yaml.safe_load(manifest_config_path.read_text()).get("examples", {})

    pio_build_dir = project_dir / ".pio" / "build"
    if not pio_build_dir.is_dir():
        sys.exit(f"No .pio/build directory found under {project_dir} - run `pio run` first")

    manifest = {}
    for env_dir in sorted(p for p in pio_build_dir.iterdir() if p.is_dir()):
        env_name = env_dir.name
        found = {name: env_dir / name for name in FLASH_OFFSETS if (env_dir / name).is_file()}
        if "firmware.bin" not in found:
            print(f"Skipping '{env_name}': no firmware.bin in {env_dir}")
            continue

        # boot_app0.bin is never in `found` (PlatformIO doesn't produce it - it's a
        # static file bundled with this Action, see copy_binaries()) but is always
        # present in the packaged output, so it's always listed here too.
        entry_config = config.get(env_name, {})
        files = [
            {"path": f"firmware/{env_name}/{name}", "offset": FLASH_OFFSETS[name]}
            for name in ["bootloader.bin", "partitions.bin", "boot_app0.bin", "firmware.bin"]
            if name in found or name == "boot_app0.bin"
        ]
        entry = {
            "name": entry_config.get("name", env_name),
            "description": entry_config.get("description", ""),
            "files": files,
        }
        if "variables" in entry_config:
            entry["variables"] = entry_config["variables"]

        manifest[env_name] = entry
        manifest[env_name]["_source_files"] = found  # consumed by copy step below, stripped after
    return manifest


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

    manifest = build_manifest(project_dir, project_dir / args.manifest_config)
    if not manifest:
        sys.exit("No built environments with a firmware.bin found - nothing to package")

    copy_webapp(action_dir, output_dir)
    copy_binaries(manifest, action_dir, output_dir)

    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Packaged {len(manifest)} firmware(s) into {output_dir}")


if __name__ == "__main__":
    main()
