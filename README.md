# Media File Renamer

A powerful, user-friendly application for automatically renaming media files (photos and videos) based on their metadata, including date/time, GPS location, and city information.

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
2. **Install Python dependencies:**
   ```bash
   pip install pillow pillow-heif exifread
   ```
3. **Run the application:**
   ```bash
   python main.py
   ```

### Basic Usage

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

## 📋 Requirements

### System Requirements
- **Python 3.7+**
- **Windows 10/11** (primary), Linux/macOS (compatible)
- **Internet connection** (for GPS city lookups)

### Python Dependencies
```bash
pip install pillow pillow-heif exifread
```

**Required:**
- `pillow` - Image processing
- `pillow-heif` - HEIC/HEIF support

**Recommended:**
- `exifread` - Enhanced RAW file support

### Optional Tools
- **ffprobe** - Enhanced video metadata (auto-detected)

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
2. **Install** dependencies: `pip install pillow pillow-heif exifread`
3. **Run** the application: `python main.py`
4. **Select** your photo folder
5. **Preview** the results
6. **Process** your files!

**Transform your messy photo collection into an organized, searchable library with meaningful filenames!**

---

*Made with ❤️ for photographers and digital asset managers*