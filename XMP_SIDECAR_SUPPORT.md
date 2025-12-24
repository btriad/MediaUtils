# XMP Sidecar File Support

## Overview

The Media File Renamer now supports XMP sidecar files, which are commonly created by photo editing software like Adobe Lightroom, Camera Raw, Capture NX-D, and others.

## What are XMP Files?

XMP (Extensible Metadata Platform) files are XML-based sidecar files that store metadata separately from the original image file. They typically have the same name as the image with a `.xmp` extension.

**Example:**
```
photo.nef       ← Original RAW file
photo.xmp       ← XMP sidecar file
```

## Features

### 1. Metadata Extraction from XMP

The application now checks XMP files for metadata when processing images:

- **GPS Coordinates**: If the image file doesn't have GPS data, the application checks the XMP file
- **Date/Time**: If the image file doesn't have date metadata, the application checks the XMP file
- **Automatic Fallback**: XMP data is used as a fallback when image metadata is missing

### 2. Automatic XMP Renaming

When an image file is renamed, its XMP sidecar file is automatically renamed to match:

**Before:**
```
DSC_1234.NEF
DSC_1234.xmp
```

**After:**
```
2024.03.14-11.56.10.001.nef
2024.03.14-11.56.10.001.xmp
```

## Supported XMP Naming Patterns

The application recognizes these XMP naming patterns:

1. `photo.xmp` - Same name, .xmp extension
2. `photo.XMP` - Same name, .XMP extension (uppercase)
3. `photo.nef.xmp` - Original filename with .xmp appended
4. `photo.nef.XMP` - Original filename with .XMP appended

## Use Cases

### Lightroom Users

If you edit RAW files in Lightroom and add GPS data or adjust dates:

1. Export XMP sidecar files from Lightroom
2. Place them in the same folder as your RAW files
3. Run the Media File Renamer
4. GPS and date data from XMP will be used

### Capture NX-D Users

Nikon's Capture NX-D can save metadata to XMP files:

1. Edit your NEF files in Capture NX-D
2. Save metadata to XMP sidecar files
3. Run the Media File Renamer
4. XMP data will be used for renaming

### GPS Tagging Software

If you use software to add GPS data to photos:

1. Use GPS tagging software to add coordinates
2. Save as XMP sidecar files
3. Run the Media File Renamer
4. GPS coordinates from XMP will be used

## How It Works

### Metadata Priority

The application uses this priority order:

1. **Image file metadata** (EXIF from NEF, CR2, etc.)
2. **XMP sidecar file** (if image has no metadata)
3. **File modification date** (if neither has metadata)

### GPS Extraction

```
1. Check image file for GPS
   ↓ (if no GPS found)
2. Look for XMP sidecar file
   ↓ (if XMP found)
3. Extract GPS from XMP
   ↓ (if GPS found)
4. Use XMP GPS coordinates
```

### Date Extraction

```
1. Check image file for date
   ↓ (if no date found)
2. Look for XMP sidecar file
   ↓ (if XMP found)
3. Extract date from XMP
   ↓ (if date found)
4. Use XMP date
```

## Example Scenarios

### Scenario 1: NEF with XMP GPS

**Files:**
- `DSC_1234.NEF` (no GPS in file)
- `DSC_1234.xmp` (contains GPS: 38.015°N, 23.821°E)

**Result:**
- GPS extracted from XMP
- City lookup: Athens
- Renamed to: `2024.03.14-11.56.10.001.Athens.nef`
- XMP renamed to: `2024.03.14-11.56.10.001.Athens.xmp`

### Scenario 2: NEF with Both GPS Sources

**Files:**
- `DSC_5678.NEF` (has GPS: 40.7128°N, 74.0060°W)
- `DSC_5678.xmp` (has GPS: 38.015°N, 23.821°E)

**Result:**
- GPS from NEF file is used (priority)
- City lookup: New York
- Renamed to: `2024.03.14-15.30.45.002.NewYork.nef`
- XMP renamed to: `2024.03.14-15.30.45.002.NewYork.xmp`

### Scenario 3: NEF without XMP

**Files:**
- `IMG_9012.NEF` (has GPS)

**Result:**
- GPS from NEF file is used
- No XMP file to rename
- Renamed to: `2024.03.14-16.20.30.003.Paris.nef`

## XMP File Format

XMP files are XML-based and contain metadata in this format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description
        xmlns:exif="http://ns.adobe.com/exif/1.0/">
      <exif:GPSLatitude>38.015</exif:GPSLatitude>
      <exif:GPSLongitude>23.8206</exif:GPSLongitude>
      <exif:DateTimeOriginal>2024-03-14T11:56:10</exif:DateTimeOriginal>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
```

## Supported XMP Fields

### GPS Fields
- `exif:GPSLatitude`
- `exif:GPSLongitude`
- `exifEX:GPSLatitude` (alternative namespace)
- `exifEX:GPSLongitude` (alternative namespace)

### Date Fields (in priority order)
1. `exif:DateTimeOriginal`
2. `exif:DateTimeDigitized`
3. `xmp:CreateDate`
4. `xmp:ModifyDate`
5. `photoshop:DateCreated`

## Creating XMP Files

### From Lightroom

1. Select photos in Lightroom
2. Metadata → Save Metadata to File
3. XMP files created in same folder

### From Capture NX-D

1. Edit NEF file
2. File → Save XMP/IPTC
3. XMP file created in same folder

### From ExifTool

```bash
exiftool -tagsFromFile source.jpg -all:all target.nef.xmp
```

## Testing XMP Support

Run the test suite:

```bash
python test_xmp_support.py
```

Expected output:
```
✓ XMP file detection
✓ GPS extraction from XMP
✓ Date extraction from XMP
✓ XMP renaming alongside images
✓ MediaProcessor integration
```

## Troubleshooting

### XMP File Not Found

**Problem:** Application doesn't find XMP file

**Solutions:**
1. Check XMP filename matches image filename
2. Verify XMP is in same folder as image
3. Check file extension (.xmp or .XMP)

### GPS Not Extracted from XMP

**Problem:** GPS in XMP but not used

**Solutions:**
1. Check if image file already has GPS (takes priority)
2. Verify XMP file is valid XML
3. Check GPS fields are in correct format
4. Review application logs for errors

### XMP Not Renamed

**Problem:** Image renamed but XMP stays with old name

**Solutions:**
1. Check XMP file permissions
2. Verify XMP file exists before renaming
3. Review application logs for errors
4. Ensure XMP filename matches image

## Logging

XMP operations are logged:

```
INFO: Checking XMP sidecar for GPS: photo.xmp
INFO: Using GPS from XMP sidecar: 38.015000, 23.820600
INFO: Renamed XMP: photo.xmp -> 2024.03.14-11.56.10.001.xmp
```

Check logs in `logs/` directory for detailed information.

## Benefits

### For Lightroom Users
- GPS data added in Lightroom is used for renaming
- Date adjustments in Lightroom are respected
- XMP files stay synchronized with images

### For RAW Shooters
- Add GPS data post-capture
- Correct dates without modifying RAW files
- Keep metadata separate from originals

### For Workflow Integration
- Works with existing XMP-based workflows
- Compatible with Adobe products
- Supports industry-standard metadata format

## Limitations

### XMP Format Support
- Only XML-based XMP files supported
- Binary XMP not supported
- Embedded XMP (inside image) not checked separately

### Metadata Fields
- Only GPS and date fields extracted
- Other metadata (keywords, ratings) not used for renaming
- Custom XMP fields not supported

### File Operations
- XMP rename failures don't stop image rename
- XMP files not created if missing
- XMP content not modified

## Future Enhancements

Potential improvements:

- Extract additional metadata (keywords, ratings)
- Create XMP files if missing
- Update XMP content after renaming
- Support for custom XMP namespaces
- Batch XMP operations

## Summary

**XMP sidecar file support provides:**

✅ Automatic XMP file detection  
✅ GPS extraction from XMP  
✅ Date extraction from XMP  
✅ Automatic XMP renaming  
✅ Seamless integration with existing workflow  
✅ Fallback when image metadata is missing  

**Perfect for:**
- Lightroom users
- Capture NX-D users
- GPS tagging workflows
- Post-processing metadata additions
- RAW file workflows

The application now provides comprehensive support for XMP sidecar files, making it easier to work with RAW files and post-processing workflows!
