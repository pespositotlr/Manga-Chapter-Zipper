# Manga Chapter Zipper

Splits a finished manga volume folder into **one zip per chapter**, plus one
zip of the whole volume, ready for release.

It's the last step after
[Manga Filename Chapter Renamer](../Manga-Filename-Chapter-Renamer), which
gives raw scan pages the chapter-tagged names this tool reads.

## Requirements

Python 3.10+ (standard library only, nothing to install).

## Usage

```bash
python chapter_zipper.py "/path/to/Volume_Folder"
python chapter_zipper.py "/path/to/Volume_Folder" --dry-run
python chapter_zipper.py "/path/to/Volume_Folder" -o "/path/to/output"
python chapter_zipper.py "/path/to/Series_Folder"
```

| Option | Meaning |
|---|---|
| `path` | A volume folder of images, or a folder whose subfolders are volume folders. |
| `-o`, `--output` | Where to write the zips. Default: inside the volume folder itself. |
| `--dry-run` | List every zip and the files it would contain, without writing anything. |

## Expected filenames

```
<prefix>_ch<NNN>_<page>.<ext>            Manga_Title_v13_ch123_003.png
<prefix>_extra_<page>.<ext>              Manga_Title_v13_extra_190.png
<prefix>_extra_credits_<page>.<ext>      Manga_Title_v13_extra_credits_194.png
```

Anything after the tag counts as the page, so pages like `000a` or `105_color`
are fine. Image types: `png`, `jpg`, `jpeg`, `webp`, `gif`, `bmp`, `tiff`.

## What goes in each zip

- **One zip per chapter**, named by its number: `123.zip`, `124.zip`, …
- **`ch000` pages** (covers, title page, table of contents) go into the
  **first** chapter's zip. If a folder only has `ch000` pages, they get their own
  `000.zip`.
- **`extra` and `extra_credits` pages** go into the **last** chapter's zip.
- **The credits page** is added to **every** chapter zip. It's taken to be the
  alphabetically last file in the folder, so name it to sort last (e.g.
  `extra_credits_<page>`).
- **A zip of the whole volume**, named after the folder, e.g.
  `Manga_Title_v13_[Group].zip`.

Files within each zip are sorted by name.

Example: a `Manga_Title` volume 13 folder with chapters 123–128
produces:

```
123.zip   ch000 pages + chapter 123 + credits page
124.zip   chapter 124 + credits page
...
128.zip   chapter 128 + extra pages + credits page
Manga_Title_v13_[Group].zip   every image
```

## Batch mode

If `path` has no images directly in it, each immediate subfolder that does is
processed as its own volume. It only looks one level down.

## Notes

- **Unrecognised filenames** are listed as a warning and left out of the chapter
  zips, but they're still included in the whole-volume zip.
- **`.psd` files are ignored.** Point it at the exported images, not the
  Photoshop working files.
- **Zips are overwritten** if they already exist in the output folder.
