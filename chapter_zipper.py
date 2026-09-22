#!/usr/bin/env python3
"""
chapter_zipper.py

Splits a manga/comic volume folder into one zip per chapter.

Expected filename shape (the part before the extension):
    <anything>_ch<NNN>_<page>          e.g. ..._ch012_005.png
    <anything>_extra_<page>            e.g. ..._extra_187.png
    <anything>_extra_credits_<page>    e.g. ..._extra_credits_194.png

Rules applied:
    - Files are grouped by their chNNN number.
    - All ch000 files are merged into the FIRST real chapter's zip
      (i.e. the lowest chNNN > 0). If ch000 is the only chapter present,
      it becomes its own zip.
    - All "extra" / "extra_credits" files are merged into the LAST
      chapter's zip.
    - The credits page (the alphabetically-last filename in the folder)
      is added to every zip, even if it wasn't already included by the
      rules above.
    - Each chapter zip is named just after its number, e.g. "012.zip".
    - One extra zip containing every image file in the folder is also
      created, named after the volume folder itself, e.g.
      "Manga_Title_v02_[Group].zip".

Usage:
    python chapter_zipper.py "/path/to/Volume_Folder"
    python chapter_zipper.py "/path/to/Series_Parent_Folder"
    python chapter_zipper.py "/path/to/Volume_Folder" --dry-run
    python chapter_zipper.py "/path/to/Volume_Folder" -o "/path/to/output"
"""

import argparse
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

# Matches: <prefix>_ch<digits>_<page>  OR  <prefix>_extra_credits_<page>  OR  <prefix>_extra_<page>
FILENAME_RE = re.compile(
    r'^(?P<prefix>.*)_(?P<tag>ch(?P<chnum>\d+)|extra_credits|extra)_(?P<page>.+)$'
)

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff'}


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTS


def parse_filename(path: Path):
    """Return {'kind': 'chapter'|'extra', 'num': int|None} or None if no match."""
    m = FILENAME_RE.match(path.stem)
    if not m:
        return None
    chnum = m.group('chnum')
    if chnum is not None:
        return {'kind': 'chapter', 'num': int(chnum)}
    return {'kind': 'extra', 'num': None}


def process_volume(folder: Path, output_dir: Path | None, dry_run: bool):
    files = sorted(p for p in folder.iterdir() if is_image(p))
    if not files:
        print(f"  [skip] no image files found in {folder}")
        return

    # "Credits page" = alphabetically last filename in the folder.
    credits_file = files[-1]

    chapter_files = defaultdict(list)  # chnum -> [Path, ...]
    extra_files = []
    unmatched = []

    for f in files:
        info = parse_filename(f)
        if info is None:
            unmatched.append(f)
        elif info['kind'] == 'chapter':
            chapter_files[info['num']].append(f)
        else:
            extra_files.append(f)

    if unmatched:
        print(f"  [warn] {len(unmatched)} file(s) didn't match the expected naming "
              f"pattern and were skipped:")
        for u in unmatched:
            print(f"         {u.name}")

    if not chapter_files:
        print(f"  [skip] no 'chNNN' files found in {folder}")
        return

    real_chapter_nums = sorted(n for n in chapter_files if n != 0)
    if not real_chapter_nums:
        # Only ch000 exists -- treat it as the sole chapter.
        real_chapter_nums = sorted(chapter_files.keys())

    first_chapter = real_chapter_nums[0]
    last_chapter = real_chapter_nums[-1]

    zips = {num: list(chapter_files[num]) for num in real_chapter_nums}

    # Merge the ch000 "prologue" files into the first real chapter.
    if 0 in chapter_files and 0 != first_chapter:
        zips[first_chapter] = list(chapter_files[0]) + zips[first_chapter]

    # Merge extras/credits into the last chapter.
    if extra_files:
        zips[last_chapter] = zips[last_chapter] + extra_files

    # Every zip gets the credits page, even if it isn't there already.
    for flist in zips.values():
        if credits_file not in flist:
            flist.append(credits_file)

    volume_name = folder.name
    out_dir = output_dir or folder
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for num in sorted(zips.keys()):
        # De-dupe while keeping things tidy.
        seen = set()
        ordered = []
        for f in zips[num]:
            if f not in seen:
                seen.add(f)
                ordered.append(f)
        ordered.sort()

        zip_name = f"{num:03d}.zip"
        zip_path = out_dir / zip_name
        print(f"  -> {zip_name}  ({len(ordered)} files)")

        if dry_run:
            for f in ordered:
                print(f"       {f.name}")
            continue

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in ordered:
                zf.write(f, arcname=f.name)

    # One extra zip with every image file in the folder, named after the
    # volume folder itself.
    everything_zip_name = f"{volume_name}.zip"
    everything_zip_path = out_dir / everything_zip_name
    print(f"  -> {everything_zip_name}  ({len(files)} files)")

    if dry_run:
        for f in files:
            print(f"       {f.name}")
        return

    with zipfile.ZipFile(everything_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.name)


def find_volumes(root: Path):
    """Yield folders that directly contain image files (root itself, or its subfolders)."""
    if any(is_image(p) for p in root.iterdir()):
        yield root
        return
    for child in sorted(root.iterdir()):
        if child.is_dir() and any(is_image(p) for p in child.iterdir()):
            yield child


def main():
    ap = argparse.ArgumentParser(
        description="Split a manga/comic volume folder into one zip per chapter."
    )
    ap.add_argument(
        'path',
        help="Path to a single volume folder, or a parent folder containing several "
             "volume folders."
    )
    ap.add_argument(
        '-o', '--output',
        help="Where to write the zips (default: alongside each volume folder)."
    )
    ap.add_argument(
        '--dry-run', action='store_true',
        help="Show what would be zipped without creating any files."
    )
    args = ap.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        sys.exit(f"Path not found: {root}")

    output_dir = Path(args.output).expanduser().resolve() if args.output else None

    volumes = list(find_volumes(root))
    if not volumes:
        sys.exit("No volume folders with image files were found.")

    for vol in volumes:
        print(f"Processing: {vol}")
        process_volume(vol, output_dir, args.dry_run)


if __name__ == '__main__':
    main()
