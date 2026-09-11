# MediaUtils
Built with Kiro IDE - Advanced development environment for enhanced productivity

Two desktop tools for organising photo and video collections:

| Tool | Run | What it does |
|------|-----|--------------|
| **Media File Renamer** | `python main.py` | Renames photos and videos from their metadata: date/time, GPS location and city |
| **EXIF Date Restorer** | `python restore_dates_gui.py` | The reverse: reads the date from the filename and writes it into files that have no date. Also gathers iPhone Live Photo clips |

Both share the same dependencies and are installed once (see Quick Start). The EXIF Date Restorer has its own section further down.

The **Media File Renamer** automatically renames media files (photos and videos) based on their metadata, including date/time, GPS location, and city information.

## 🌟 Features

### Core Functionality
- **Automatic Renaming** - Rename files based on EXIF metadata
- **GPS Location Support** - Extract GPS coordinates and convert to city names
- **Date/Time Extraction** - Use original capture date from metadata
- **Batch Processing** - Process hundreds of files at once
- **Safe Operation** - Only renames files, never deletes or modifies content

### File Format Support
- **Standard Images**: JPG, PNG, GIF, BMP, TIFF, WebP, HEIC, HEIF
- **RAW Formats**: NEF (Nikon), CR2/CR3 (Canon), ARW (Sony), DNG (Adobe), ORF (Olympus), RW2 (Panasonic), PEF (Pentax), RAF (Fujifilm)
- **Videos**: MP4, AVI, MOV, MKV, WMV, FLV, WebM
- **XMP Sidecar Files** - Automatic detection and renaming alongside images

### Advanced Features
- **XMP Sidecar Support** - Extract metadata from Lightroom/Capture NX-D XMP files
- **City Cache** - Intelligent caching of GPS lookups for faster processing
- **Conflict Resolution** - Automatic handling of duplicate filenames
- **Session Logging** - Detailed logs of all operations
- **Error Recovery** - Graceful handling of corrupted files and network issues
- **Format Validation** - Real-time validation with helpful suggestions

## 📸 Example

**Before:**
```
DSC_1234.NEF
IMG_5678.CR2
P1000123.RW2
```

**After:**
```
2024.03.14-11.56.10.001.Athens.nef
2024.03.14-15.30.45.002.Paris.cr2
2024.03.15-09.20.15.003.Tokyo.rw2
```

## 🚀 Quick Start

### Installation

1. **Clone or download** this repository
2. **Create a virtual environment and install the dependencies:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   source .venv/bin/activate       # Linux / macOS
   pip install -r requirements.txt exifread
   ```
   On Ubuntu/Debian install venv and Tk first with `sudo apt install python3-venv python3-tk`, and create the environment with `python3 -m venv .venv`. Activate the environment again in every new terminal.
3. **Run a tool:**
   ```bash
   python main.py               # Media File Renamer
   python restore_dates_gui.py  # EXIF Date Restorer
   ```

### Basic Usage (Media File Renamer)

1. **Select Folder** - Choose folder containing your media files
2. **Configure Format** - Customize filename pattern (optional)
3. **Show Files** - Preview what files will be renamed
4. **Process Files** - Rename selected files

## 🎯 Filename Patterns

### Default Pattern
```
%Y.%m.%d-%H.%M.%S.{increment:03d}.{city}.{ext}
```

### Example Outputs
- `2024.03.14-11.56.10.001.Athens.jpg`
- `2024.03.14-11.56.10.002.nef`
- `2024.03.15-09.20.15.001.Tokyo.mp4`

### Available Placeholders

**Date/Time:**
- `%Y` - 4-digit year (2024)
- `%m` - Month (01-12)
- `%d` - Day (01-31)
- `%H` - Hour 24-hour (00-23)
- `%M` - Minute (00-59)
- `%S` - Second (00-59)

**Custom:**
- `{increment:03d}` - 3-digit number (001, 002, etc.)
- `{city}` - City name from GPS
- `{ext}` - File extension (required)

## 🗺️ GPS & Location Features

### GPS Sources
1. **Image EXIF data** (primary)
2. **XMP sidecar files** (fallback)
3. **Video metadata** (for supported formats)

### City Lookup
- Automatic reverse geocoding
- Intelligent caching for performance
- Offline cache persistence
- Fallback to coordinates if city lookup fails
- Respects OpenStreetMap's usage policy: at most one request per second, automatic back-off after `HTTP 429`, and a 5-minute pause if the server keeps refusing. Files whose city could not be found are retried on the next run

### Supported GPS Formats
- Decimal degrees
- Degrees, minutes, seconds
- XMP attribute format
- Various manufacturer formats

## 📁 XMP Sidecar File Support

Perfect for **Lightroom** and **Capture NX-D** users!

### What are XMP Files?
XMP files store metadata separately from your original images, commonly created by:
- Adobe Lightroom
- Adobe Camera Raw
- Nikon Capture NX-D
- GPS tagging software

### How It Works
```
photo.nef       ← Original RAW file (no GPS)
photo.xmp       ← XMP sidecar (has GPS from Lightroom)
```

**Result:** GPS data from XMP is used for renaming, and both files are renamed together.

### Supported XMP Patterns
- `photo.xmp` - Standard naming
- `photo.XMP` - Uppercase extension
- `photo.nef.xmp` - Appended naming
- `photo.nef.XMP` - Appended uppercase

## 🛡️ Safety Features

### File Safety
- **Only renames files** - Never deletes, moves, or modifies content
- **Same directory** - Files stay in original folder
- **Conflict resolution** - Automatic handling of duplicate names
- **Backup logs** - Record of all rename operations
- **User confirmation** - Preview before processing

### Error Handling
- **Graceful recovery** from corrupted files
- **Network retry** for GPS lookups
- **Permission handling** for protected files
- **Detailed logging** for troubleshooting

## 🔧 Advanced Configuration

### Custom Formats
Create your own filename patterns:
```
%Y-%m-%d_%H%M%S_{city}_{increment:03d}.{ext}
→ 2024-03-14_115610_Athens_001.jpg

{city}_%Y%m%d_{increment:02d}.{ext}
→ Athens_20240314_01.jpg
```

### Settings
- **Window geometry** - Remembers size and position
- **Recent formats** - Quick access to used patterns
- **Cache settings** - Configure GPS cache size
- **Logging levels** - Control detail level

## 📊 Logging & Monitoring

### Session Logs
- **Operation tracking** - Record of all renames
- **Error logging** - Detailed error information
- **Performance metrics** - Processing statistics
- **Timestamped entries** - Full audit trail

### Cache Statistics
- **Hit rate monitoring** - Cache performance
- **Entry management** - Automatic cleanup
- **Size tracking** - Memory usage
- **Persistence** - Survives application restarts

## 🧪 Testing & Verification

### Test Suite
Run comprehensive tests:
```bash
python test_raw_file_support.py    # RAW format support
python test_xmp_support.py         # XMP sidecar files
python test_rename_safety.py       # Safety verification
python test_gps_extraction_logic.py # GPS functionality
```

### Diagnostic Tools
```bash
python diagnose_nef_gps.py photo.nef    # GPS troubleshooting
python demo_raw_support.py              # RAW format demo
python test_real_xmp.py                 # XMP testing
```

## 🗓️ EXIF Date Restorer

The reverse of the renamer: it reads the date **from the filename** and writes it **into the file's metadata**, but only for files that have no date yet. Useful for scanned photos, old videos and exports that sort wrongly in Google Photos, Windows Photos or iOS because they carry no capture date.

```bash
python restore_dates_gui.py
```

### How to use
1. **Folder**: choose the folder to scan
2. **Include sub-folders (recursive)**: also scan every sub-folder, at any depth
3. **Include videos (MP4/MOV)**: handle videos as well as JPEG
4. **Scan**: the table lists only files **without** a date, with the full path, the date that will be written and a note. Files that already have a date are hidden and counted in the summary line
5. **Write dates**: asks for confirmation, then writes. Failures stay in the table with the reason in the **Note** column

### Filename formats
The date can appear anywhere in the name. Prefixes such as `_` or `IMG_`, and anything after the date, are ignored.

| Filename | Date written |
|----------|--------------|
| `1999.12.05.jpg` | 1999-12-05 00:00:00 |
| `1999.12.05-21.00.jpg` or `1999.12.05.21.00.jpg` | 1999-12-05 21:00:00 |
| `1999.7.22.jpg` | 1999-07-22 00:00:00 |
| `2008.05.mp4` | 2008-05-01 00:00:00 |
| `1999.00.00.jpg` | 1999-01-01 00:00:00 |
| `_2022.10.28-12.02.27.018.JPG` | 2022-10-28 12:02:27 |
| `20150629_004718.jpg` | 2015-06-29 00:47:18 |
| `IMG_20211224_120000.jpg` | 2021-12-24 12:00:00 |

Rules:
- No time means 00:00:00
- No day means the 1st of the month
- A month or day of `00` becomes `01`
- Year and month are required
- Invalid values (month 13, 30 February) are rejected

### What is written
| Type | Where | How |
|------|-------|-----|
| **JPEG** (`.jpg`, `.jpeg`) | EXIF `DateTimeOriginal`, `CreateDate`, `ModifyDate` | Only the EXIF block is rewritten. The image data is not re-encoded |
| **Video** (`.mp4`, `.mov`, `.m4v`, `.3gp`) | `creation_time` in the `mvhd`, `tkhd` and `mdhd` headers | Fixed-size fields are patched in place. Streams are untouched, the file size does not change, and ffmpeg is not needed |

- **Existing dates are never overwritten.** A JPEG counts as dated if it has any of the three EXIF date tags. A video counts as dated if its QuickTime headers already carry a creation time.
- **Not supported, by design:** DNG and other RAW formats (their EXIF is left alone), and MKV/AVI/WMV/FLV/WebM (these cannot be edited without rebuilding the file).
- QuickTime stores video times as UTC. The filename time is written unchanged, so some players show it shifted by your time-zone offset.

### 📱 Live Photo organiser
The **Find Live Photos** button finds the `.mov` clips that belong to iPhone Live Photos. After confirmation it moves each clip into a `livephoto` sub-folder **inside the clip's own folder**.

- Detection uses the QuickTime key `com.apple.quicktime.content.identifier`, which is what `exiftool -ContentIdentifier` reports. It is read directly from the file, so exiftool is not required
- Follows the **Include sub-folders** option
- Never overwrites: a name clash becomes `IMG_0001 (1).MOV`
- Safe to re-run: clips already inside a `livephoto` folder are skipped
- Only the `.mov` clips move; the still photos stay where they are

Logs are written to `logs/restore_dates_<timestamp>.log`.

## 📋 Requirements

### System Requirements
- **Python 3.9+** (the Media File Renamer on its own runs on 3.7+)
- **Windows 10/11** or **Linux** (e.g. Ubuntu); macOS compatible
- **Internet connection** (for GPS city lookups)

### Python Dependencies
```bash
pip install -r requirements.txt exifread
```

**Required** (listed in `requirements.txt`):
- `pillow` - Image processing
- `pillow-heif` - HEIC/HEIF support
- `piexif` - Writing EXIF dates (EXIF Date Restorer)

**Recommended:**
- `exifread` - Enhanced RAW file support

### Optional Tools
- **ffprobe** - Video dates and GPS for the Media File Renamer (auto-detected). On Ubuntu: `sudo apt install ffmpeg`. The EXIF Date Restorer does not need it

## 🎨 User Interface

### Main Window
- **Folder selection** with browse button
- **Format editor** with real-time validation
- **File preview** with metadata display
- **Progress tracking** with detailed status
- **Statistics display** with cache info

### Validation Features
- **Real-time format checking**
- **Error highlighting** with suggestions
- **Example preview** with sample output
- **Format suggestions** with common patterns

## 🔍 Troubleshooting

### Common Issues

**GPS not working for RAW files?**
```bash
pip install exifread
```

**XMP files not detected?**
- Check XMP file is in same folder as image
- Verify filename matches (photo.nef → photo.xmp)
- Ensure XMP contains GPS data

**Files not renaming?**
- Check file permissions
- Verify format is valid
- Review application logs in `logs/` folder

**City missing and `HTTP Error 429` in the logs?**
- OpenStreetMap allows one free lookup per second. The renamer spaces its requests and backs off automatically
- If lookups were paused, run the scan again later. Cities already found are cached and are not requested again

**`No module named 'pillow_heif'` (or another module)?**
- The dependencies are not installed in the Python you are running. Activate the virtual environment from Quick Start and run `pip install -r requirements.txt exifread`

**Date Restorer shows "Write error" in the Note column?**
- `No mvhd/tkhd/mdhd atom found`: the file is not a real MP4/MOV container (for example an old MPEG renamed to `.mp4`), so its date cannot be edited in place
- `Permission denied` or `Read-only file system`: the drive is mounted read-only or you lack write access

### Getting Help

1. **Check logs** - `logs/` directory contains detailed information
2. **Run diagnostics** - Use provided diagnostic tools
3. **Verify format** - Use built-in format validation
4. **Test with sample** - Try with a few files first

## 📚 Documentation

### Detailed Guides
- [RAW File Support](RAW_FILE_SUPPORT.md) - Complete RAW format guide
- [XMP Sidecar Support](XMP_SIDECAR_SUPPORT.md) - XMP file documentation
- [Safety Confirmation](SAFETY_CONFIRMATION.md) - Security verification
- [Installation Guide](INSTALL_EXIFREAD.md) - Setup instructions

### Technical Documentation
- [GPS Extraction Status](GPS_EXTRACTION_STATUS.md) - GPS troubleshooting
- [Rename Safety Verification](RENAME_SAFETY_VERIFICATION.md) - Safety analysis

## 🏗️ Architecture

### Core Components
- **`main.py`** - Application entry point
- **`gui_components.py`** - User interface
- **`media_processor.py`** - Metadata extraction
- **`filename_generator.py`** - Name generation and validation
- **`file_operations.py`** - File system operations
- **`xmp_handler.py`** - XMP sidecar file support

### Supporting Modules
- **`city_cache.py`** - GPS caching system
- **`logging_manager.py`** - Session and application logging
- **`error_recovery.py`** - Error handling and recovery
- **`settings_manager.py`** - Configuration management

### EXIF Date Restorer
- **`restore_dates_gui.py`** - User interface and entry point
- **`exif_date_restorer.py`** - Filename date parsing, JPEG EXIF read/write, scan and apply
- **`video_date_restorer.py`** - In-place creation time for MP4/MOV/M4V/3GP
- **`livephoto_detector.py`** - Live Photo detection and organiser

## 🤝 Contributing

### Development Setup
1. Clone repository
2. Install dependencies
3. Run tests to verify setup
4. Make changes
5. Run tests again
6. Submit pull request

### Code Style
- **Python PEP 8** compliance
- **Comprehensive logging** for debugging
- **Error handling** for all operations
- **Unit tests** for new features

## 📄 License

This project is open source. Feel free to use, modify, and distribute according to your needs.

## 🙏 Acknowledgments

### Libraries Used
- **Pillow** - Image processing
- **exifread** - EXIF data extraction
- **pillow-heif** - HEIC/HEIF support
- **tkinter** - GUI framework

### Special Thanks
- Camera manufacturers for EXIF standards
- Adobe for XMP format specification
- Open source community for excellent libraries

---

## 🚀 Get Started Now!

1. **Download** the application
2. **Install** dependencies: `pip install -r requirements.txt exifread`
3. **Run** `python main.py` (renamer) or `python restore_dates_gui.py` (date restorer)
4. **Select** your photo folder
5. **Preview** the results
6. **Process** your files!

**Transform your messy photo collection into an organized, searchable library with meaningful filenames!**

---

