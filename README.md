# FrameTags

**FrameTags - Batch metadata editor for photographers.**

FrameTags is a PySide6 desktop utility for applying metadata to large photo sets in bulk without Lightroom or command-line workflows.

## Who it is for

Photographers who need repeatable metadata workflows across export folders, trip folders, and archives.

## What it does in v1

- Select one or more root directories
- Scan with optional recursive traversal
- Select exactly which metadata fields to apply
- Preview real per-file change sets before writing
- Apply metadata writes through ExifTool
- Save, load, update, and delete reusable presets

This tool does not edit image pixels. It only reads and writes metadata.

## Supported formats

- RAW: `.cr2`, `.nef`, `.arw`, `.dng`, `.orf`, `.raf`
- Standard image: `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.png`

PNG metadata support depends on ExifTool capabilities and file metadata blocks.

## Supported metadata fields

- Artist
- Copyright
- Credit
- Source
- Creator Email
- Creator Website
- Usage Terms / License
- Location Name
- City
- State / Province
- Country
- GPS Latitude
- GPS Longitude
- Caption / Description
- Headline
- Keywords

Keywords accept comma-separated input and are handled as distinct values.

## Metadata model and architecture

FrameTags separates UI fields from raw metadata tags using a registry in `app/metadata_fields.py`.

- UI controls bind to normalized internal keys (for example `artist`, `caption`, `keywords`)
- Mapping to Exif/IPTC/XMP tag targets is centralized in field definitions and `app/metadata_mapper.py`
- Preview and apply share the same change-set datamodel (`FileChangeSet`, `FileChangeAction`)

This keeps the app extensible for future inspector, normalization, reporting, and copy workflows.

## Write behavior

- `overwrite`: replace existing values
- `write_if_empty`: write only where current value is blank
- `append_keywords`: append non-duplicate keywords

RAW handling is strategy-based from day one:

- embedded for JPEG/TIFF
- sidecar-aware strategies for RAW formats
- user option: prefer sidecar for RAW

## Presets

Presets are stored in `data/presets.json`.

- Save current checked non-empty field values as a named preset
- Load preset values into the form
- Update or delete existing presets

Only selected fields with values are persisted.

## Preview workflow

Preview is required before apply.

Preview pipeline:

1. scan candidate files
2. read existing metadata through ExifTool
3. compare against selected field values and write mode
4. build per-file change sets
5. show only files that would actually change

Apply consumes the exact preview change-set model.

### How "Changed Fields" is counted

`Changed Fields` in preview means fields whose value would actually change on that file.

- A checked field is not counted if the existing value already matches the entered value.
- This is true even when using `overwrite` mode.
- So if 6 fields are checked, a file may show 3/4/5 changed fields depending on what already matches.

## Settings persistence

General settings are saved in `data/settings.json`:

- last selected preset
- last used directories
- recurse option
- write mode
- RAW sidecar preference
- window geometry

## Dependency: ExifTool

FrameTags requires `PyExifTool` and an ExifTool executable. FrameTags first checks for `exiftool.exe` next to the app, then falls back to system `PATH`.

- ExifTool: [https://exiftool.org/](https://exiftool.org/)

If ExifTool is missing, preview/apply actions will be blocked with an error message.

## Run locally

From the `frametags` directory:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Requires Python 3.12+.

## Build Windows distributable

From `E:\FrameTags\frametags` in `cmd`:

```bat
.venv\Scripts\activate
build.bat
```

`build.bat` will:

1. install build dependency from `build-requirements.txt`
2. run `PyInstaller` with `frametags.spec`
3. create output in `dist\FrameTags`

Distribution layout:

```text
dist\\FrameTags\\
  FrameTags.exe
  exiftool.exe
  exiftool_files\\
  data\\
  [PyInstaller runtime files]
```

Zip `dist\FrameTags` and share it. Users can run `FrameTags.exe` directly.

## Future planned features

- Metadata inspector (single-file normalized view)
- Metadata normalization scans and standardization workflows
- Metadata reporting (value distributions and keyword counts)
- RAW -> JPEG metadata copy workflows
- richer sidecar-aware workflows



