# Installing FFmpeg for MOV File Support

## Why FFmpeg is Needed

The Media File Renamer application **fully supports MOV files**, but requires **FFmpeg** (specifically the `ffprobe` tool) to extract metadata from video files, including:

- **Creation date/time** - When the video was recorded
- **GPS coordinates** - Where the video was recorded (if available)
- **Other metadata** - Camera model, resolution, duration, etc.

Without FFmpeg, the application can:
- ✅ Detect MOV files
- ✅ List MOV files in the interface
- ❌ Extract metadata from MOV files (will show "No metadata")

## Installation Methods

### Method 1: Using winget (Recommended for Windows 10/11)

Open PowerShell or Command Prompt and run:

```powershell
winget install Gyan.FFmpeg
```

After installation, **restart your terminal** or **restart the Media File Renamer application**.

### Method 2: Using Chocolatey

If you have Chocolatey installed:

```powershell
choco install ffmpeg
```

### Method 3: Manual Installation

1. **Download FFmpeg:**
   - Visit: https://ffmpeg.org/download.html
   - For Windows: https://www.gyan.dev/ffmpeg/builds/
   - Download the "ffmpeg-release-essentials.zip"

2. **Extract the archive:**
   - Extract to a folder like `C:\ffmpeg`

3. **Add to PATH:**
   - Open System Properties → Environment Variables
   - Edit the "Path" variable
   - Add: `C:\ffmpeg\bin`
   - Click OK

4. **Verify installation:**
   - Open a new Command Prompt
   - Run: `ffprobe -version`
   - You should see version information

### Method 4: Portable Installation (No PATH modification)

1. Download `ffprobe.exe` from FFmpeg builds
2. Place `ffprobe.exe` in the same folder as `main.py`
3. The application will automatically detect and use it

## Verifying Installation

After installing FFmpeg, verify it's working:

### Option 1: Command Line Test

```powershell
ffprobe -version
```

You should see output like:
```
ffprobe version N-123074-g4e32fb4c2a
...
```

### Option 2: Test with the Application

Run the test script:

```powershell
python test_iphone_mov.py
```

You should see:
```
✓ ffprobe found: ffprobe
```

## Testing MOV File Metadata

Once FFmpeg is installed, test your iPhone MOV file:

```powershell
python test_iphone_mov.py
```

Expected output:
```
✓ Date extracted: 2024-08-09 19:34:35
✓ Location: 41.0368, 28.9852
✓ City: Athens
```

## Troubleshooting

### "ffprobe not found" Error

**Solution 1:** Restart your terminal/application after installing FFmpeg

**Solution 2:** Verify FFmpeg is in PATH:
```powershell
where.exe ffprobe
```

**Solution 3:** Use portable installation (place ffprobe.exe in application folder)

### "No metadata found" for MOV files

**Possible causes:**
1. FFmpeg not installed correctly
2. MOV file doesn't contain metadata
3. MOV file is corrupted

**Test with ffprobe directly:**
```powershell
ffprobe -v quiet -print_format json -show_format -show_streams test.MOV
```

### Permission Errors

Run PowerShell as Administrator when installing via winget or chocolatey.

## Supported Video Formats (with FFmpeg)

Once FFmpeg is installed, these video formats are fully supported:

- ✅ **MOV** - QuickTime Movie (iPhone, Mac)
- ✅ **MP4** - MPEG-4 Video
- ✅ **AVI** - Audio Video Interleave
- ✅ **MKV** - Matroska Video
- ✅ **WMV** - Windows Media Video
- ✅ **FLV** - Flash Video
- ✅ **WebM** - WebM Video

## iPhone-Specific Notes

iPhone MOV files typically contain:
- ✅ Creation date/time
- ✅ GPS coordinates (if Location Services enabled)
- ✅ Camera model (iPhone model)
- ✅ Video resolution and codec info

Make sure Location Services were enabled when recording the video for GPS data to be available.

## Quick Start After Installation

1. **Install FFmpeg** (using one of the methods above)
2. **Restart the application**: `python main.py`
3. **Select folder** with MOV files
4. **Click "Show Files"** - MOV files should now show metadata
5. **Process files** - MOV files will be renamed with date/location

## Need Help?

If you continue to have issues:
1. Check the application logs in the `logs/` folder
2. Run the diagnostic script: `python test_iphone_mov.py`
3. Verify FFmpeg installation: `ffprobe -version`

---

*Note: FFmpeg is free, open-source software licensed under LGPL/GPL*
