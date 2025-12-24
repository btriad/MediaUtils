# Installing exifread for NEF GPS Support

## Why You Need exifread

The `exifread` library is **required** for extracting GPS data from NEF (and other RAW) files. Without it, GPS extraction from RAW files will not work.

## Installation

### Windows

Open Command Prompt or PowerShell and run:

```bash
pip install exifread
```

### Verify Installation

After installing, verify it works:

```bash
python -c "import exifread; print('exifread installed successfully')"
```

## Testing GPS Extraction

After installing exifread, test GPS extraction from your NEF files:

```bash
python diagnose_nef_gps.py "path\to\your\file.NEF"
```

This will show:
- Whether GPS data is present in your NEF file
- The extracted coordinates
- Any errors encountered

## Common Issues

### Issue 1: "exifread not available"

**Solution:** Install exifread as shown above

### Issue 2: "No GPS tags found"

**Possible causes:**
- Camera doesn't have built-in GPS
- GPS was disabled when photo was taken
- External GPS accessory not connected
- GPS data was stripped from the file

**How to check:**
1. Open the NEF file in Nikon ViewNX or Capture NX
2. Check if GPS data is shown
3. Verify GPS was enabled on your camera

### Issue 3: GPS works for JPG but not NEF

**Solution:** This is exactly why exifread is needed. PIL/Pillow has limited RAW support. Install exifread.

## Camera GPS Support

### Nikon Cameras with Built-in GPS

- D5300, D5500, D5600
- D7500
- Nikon 1 AW1
- COOLPIX AW series

### Nikon Cameras Requiring GPS Accessory

Most Nikon DSLRs require an external GPS unit:
- GP-1/GP-1A GPS Unit (older models)
- GP-N100 GPS Unit (newer models)
- Smartphone GPS via SnapBridge (some models)

### Check Your Camera

1. Look in camera menu for GPS settings
2. Check if GPS icon appears in viewfinder
3. Review photo metadata in camera playback

## After Installation

Once exifread is installed:

1. **Restart the application** if it's running
2. **Test with a NEF file** that you know has GPS data
3. **Check the logs** in `logs/` directory for detailed information
4. **Run the diagnostic** tool to verify extraction works

## Verification

Run this to confirm everything works:

```bash
python test_raw_file_support.py
```

All tests should pass if exifread is properly installed.

## Still Having Issues?

If GPS extraction still doesn't work after installing exifread:

1. **Run the diagnostic tool:**
   ```bash
   python diagnose_nef_gps.py "your_file.NEF"
   ```

2. **Check the application logs:**
   - Look in `logs/` directory
   - Find the most recent log file
   - Search for "GPS" or "exifread"

3. **Verify GPS data exists:**
   - Open NEF in Nikon software
   - Check if GPS coordinates are shown
   - Some NEF files simply don't have GPS data

4. **Test with a known-good file:**
   - Find a NEF file that definitely has GPS
   - Test with that file first
   - If it works, other files may not have GPS data

## Alternative: Use DNG Format

If you're having persistent issues with NEF files:

1. Convert NEF to DNG using Adobe DNG Converter
2. DNG is a universal RAW format with better support
3. The application supports DNG files natively

## Summary

**Required for NEF GPS extraction:**
```bash
pip install exifread
```

**Test after installation:**
```bash
python diagnose_nef_gps.py "your_file.NEF"
```

**Verify it works:**
- Check diagnostic output
- Look for "GPS coordinates extracted"
- Verify latitude/longitude values

That's it! With exifread installed, GPS extraction from NEF files should work perfectly.
