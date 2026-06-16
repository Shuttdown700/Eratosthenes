import subprocess
from pathlib import Path

# ROM folders to process. Edit these to match your actual paths.
SOURCE_DIRS = [
    r"T:\ShuttFlix-Temp\Games\xbox360"
]

# extract-xiso.exe lives in ../bin/ relative to this script's location
EXTRACT_XISO = (Path(__file__).resolve().parent / ".." / "bin" / "extract-xiso.exe").resolve()

OUTPUT_DIRNAME = "trimmed"


def trim_iso(iso_path: Path, output_dir: Path) -> bool:
    original_size = iso_path.stat().st_size
    output_dir.mkdir(parents=True, exist_ok=True)

    before = set(output_dir.glob("*"))

    cmd = [str(EXTRACT_XISO), "-r", "-d", str(output_dir), str(iso_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  FAILED: {result.stderr.strip() or result.stdout.strip()}")
        return False

    after = set(output_dir.glob("*"))
    new_files = after - before

    if not new_files:
        print(f"  WARNING: no new file produced in {output_dir}")
        return False

    produced = next((f for f in new_files if f.suffix.lower() == ".iso"), None)
    if produced is None:
        print(f"  WARNING: unexpected output: {new_files}")
        return False

    # Rename to match the original filename, if extract-xiso changed it
    target = output_dir / iso_path.name
    if produced != target:
        produced.rename(target)
        produced = target

    new_size = produced.stat().st_size
    saved = original_size - new_size
    pct = (saved / original_size * 100) if original_size else 0
    print(f"  {original_size/1e9:.2f} GB -> {new_size/1e9:.2f} GB "
          f"(saved {saved/1e9:.2f} GB, {pct:.1f}%)")
    return True


def process_dir(source_dir: Path):
    if not source_dir.is_dir():
        print(f"Skipping (not found): {source_dir}")
        return

    output_dir = source_dir / OUTPUT_DIRNAME
    isos = sorted(source_dir.glob("*.iso"))

    if not isos:
        print(f"No .iso files found in {source_dir}")
        return

    print(f"\n=== {source_dir} ===")
    print(f"Found {len(isos)} ISO(s). Trimmed copies go to: {output_dir}\n")

    for iso in isos:
        print(f"Processing: {iso.name}")
        trim_iso(iso, output_dir)
        print()


def main():
    if not EXTRACT_XISO.exists():
        print(f"extract-xiso.exe not found at: {EXTRACT_XISO}")
        return

    for source_dir in SOURCE_DIRS:
        process_dir(Path(source_dir))

    print("\nDone. Verify the trimmed copies boot correctly before deleting originals.")


if __name__ == "__main__":
    main()