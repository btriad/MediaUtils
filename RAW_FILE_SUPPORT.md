# RAW File Format Support

## Overview

The Media File Renamer now supports RAW image formats from major camera manufacturers, including Nikon .NEF files and many others.

## Supported RAW Formats

The following RAW formats are now supported:

| Extension | Camera Brand | Description |
|-----------|--------------|-------------|
| `.nef` | Nikon | Nikon Electronic Format |
| `.cr2` | Canon | Canon RAW 2 (older models) |
| `.cr3` | Canon | Canon RAW 3 (newer models) |
| `.arw` | Sony | Sony Alpha RAW |
| `.dng` | Adobe | Digital Negative (universal RAW) |
| `.orf` | Olympus | Olympus RAW Format |
| `.rw2` | Panasonic | Panasonic RAW 2 |
| `.pef` | Pentax | Pentax Electronic File |
| `.raf` | Fujifilm | RAW File Format |

## How It Works

### Metadata Extraction

The application uses a two-tier approach for extracting metadata from RAW files:

1. **Primary Method: exifread library** (recommended)
   - Provides robust EXIF data extraction from RAW files
   - Handles manufacturer-specific RAW formats
   - Extracts date/time and GPS coordinates accurately

2. **Fallback Method: PIL/Pillow**
   - Used when exifread is not available
   - Limited RAW support depending on PIL capabilities
   - Works best with DNG and some other formats

### Installation

For full RAW file support, install the `exifread` library:

```bash
pip install exifread
```

Without exifread, the application will still work but with limited RAW file support.

## Features

### Date/Time Extraction

The application extracts the original capture date/time from RAW files using EXIF data:

- `EXIF DateTimeOriginal` (preferred)
- `EXIF DateTimeDigitized` (fallback)
- `Image DateTime` (last resort)

### GPS Coordinate Extraction

GPS coordinates are extracted from RAW files when available:

- Latitude and longitude in decimal degrees
- Automatic conversion from degrees/minutes/seconds format
- Support for N/S/E/W reference directions

### City Lookup

When GPS coordinates are found in RAW files, the application:

1. Extracts latitude and longitude
2. Looks up the city name using reverse geocoding
3. Caches results for faster subsequent lookups
4. Includes city name in the filename if configured

## Usage

RAW files are processed automatically just like JPEG files:

1. Select a folder containing RAW files
2. Click "Show Files" to scan for media
3. RAW files will appear in the list with extracted metadata
4. Process files normally to rename them

## Example

**Original filename:** `DSC_1234.NEF`

**With metadata and GPS:**
- Date: 2024-01-15 14:30:00
- Location: Athens, Greece
- Generated filename: `2024.01.15-14.30.00.001.Athens.nef`

**Without metadata:**
- Uses file modification date
- Generated filename: `2024.01.15-14.30.00.001.nef`

## Limitations

### Without exifread

When exifread is not installed:

- Some RAW formats may not be readable
- Metadata extraction may fail for certain camera models
- DNG files typically work better than proprietary formats

### With exifread

- Full support for all listed RAW formats
- Reliable metadata extraction
- Accurate GPS coordinate conversion

## Error Handling

The application handles RAW file errors gracefully:

- **Corrupted files**: Logged and skipped, processing continues
- **Missing metadata**: Uses file modification date as fallback
- **Permission errors**: Logged with appropriate error message
- **Unsupported formats**: Detected and reported to user

## Testing

Run the RAW file support tests:

```bash
python test_raw_file_support.py
```

This will verify:
- RAW extensions are recognized
- Metadata extraction works correctly
- GPS coordinate conversion is accurate
- Fallback mechanisms function properly

## Performance

RAW file processing is optimized:

- Metadata extraction only (no image decoding)
- Fast EXIF reading without loading full image
- Caching of GPS city lookups
- Efficient batch processing

## Recommendations

1. **Install exifread** for best results:
   ```bash
   pip install exifread
   ```

2. **Test with your camera's RAW files** before processing large batches

3. **Keep backups** of original files before renaming

4. **Check the preview** in the file list before processing

## Troubleshooting

### RAW files not appearing in file list

- Verify the file extension is in the supported list
- Check file permissions
- Look for error messages in the application log

### No metadata extracted from RAW files

- Install exifread: `pip install exifread`
- Verify the RAW file contains EXIF data
- Check if the camera model is supported

### GPS coordinates not found

- Not all cameras embed GPS data
- Some cameras require GPS accessory
- Check if GPS was enabled when photo was taken

## Future Enhancements

Potential improvements for RAW file support:

- Support for additional RAW formats (e.g., `.3fr`, `.fff`, `.mrw`)
- Thumbnail extraction for preview
- RAW-specific metadata (ISO, aperture, shutter speed)
- Batch conversion options

## Technical Details

### Code Structure

RAW file support is implemented in `media_processor.py`:

- `_extract_image_date()`: Main date extraction with RAW detection
- `_extract_date_with_exifread()`: RAW-specific date extraction
- `_extract_image_gps()`: Main GPS extraction with RAW detection
- `_extract_gps_with_exifread()`: RAW-specific GPS extraction
- `_convert_gps_to_decimal()`: GPS coordinate conversion

### Dependencies

- **PIL/Pillow**: Base image handling
- **exifread** (optional): Enhanced RAW support
- **pillow-heif**: HEIC/HEIF support

### Compatibility

Tested with:
- Windows 10/11
- Python 3.7+
- Various camera RAW formats

## Support

For issues with RAW file support:

1. Check the application log for error messages
2. Verify exifread is installed
3. Test with a known-good RAW file
4. Report issues with camera model and RAW format details
