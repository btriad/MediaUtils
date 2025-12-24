# Requirements Document

## Introduction

The Media File Renamer is a GUI application designed to rename media files (images and videos) based on their metadata, particularly EXIF data and GPS location information. The application provides a user-friendly interface for batch processing files with customizable filename formats, progress tracking, and settings persistence.

## Requirements

### Requirement 1

**User Story:** As a user, I want to select a folder containing media files, so that I can process multiple files at once for renaming.

#### Acceptance Criteria

1. WHEN the user clicks the "Browse" button THEN the system SHALL open a folder selection dialog
2. WHEN the user selects a valid folder path THEN the system SHALL update the folder path field
3. WHEN the user enters a folder path manually THEN the system SHALL validate the path exists
4. IF the folder path does not exist THEN the system SHALL display an error message

### Requirement 2

**User Story:** As a user, I want to customize the filename format using placeholders, so that I can generate filenames that match my organizational preferences.

#### Acceptance Criteria

1. WHEN the user enters a filename format pattern THEN the system SHALL display a real-time example of the generated filename
2. WHEN the format pattern contains date placeholders THEN the system SHALL format dates according to standard strftime conventions
3. WHEN the format pattern contains {increment:03d} THEN the system SHALL generate sequential 3-digit numbers
4. WHEN the format pattern contains {city} THEN the system SHALL include the city name from GPS data
5. WHEN the format pattern contains {ext} THEN the system SHALL include the original file extension
6. IF the format pattern is invalid THEN the system SHALL display "Invalid format" in the example

### Requirement 3

**User Story:** As a user, I want to extract creation dates from image EXIF data, so that I can organize files chronologically.

#### Acceptance Criteria

1. WHEN processing an image file THEN the system SHALL attempt to read EXIF metadata
2. WHEN EXIF contains DateTimeOriginal THEN the system SHALL use this as the primary date source
3. WHEN DateTimeOriginal is not available THEN the system SHALL try DateTimeDigitized as fallback
4. WHEN DateTimeDigitized is not available THEN the system SHALL try DateTime as final fallback
5. IF no valid date is found in EXIF THEN the system SHALL mark the file as having no metadata

### Requirement 4

**User Story:** As a user, I want to extract creation dates from video metadata, so that I can organize video files chronologically.

#### Acceptance Criteria

1. WHEN processing a video file THEN the system SHALL use ffprobe to extract metadata
2. WHEN ffprobe is available locally THEN the system SHALL use the local executable first
3. WHEN local ffprobe is not available THEN the system SHALL try system PATH ffprobe
4. WHEN video metadata contains creation_time THEN the system SHALL parse the timestamp
5. IF ffprobe is not available THEN the system SHALL mark video files as having no metadata

### Requirement 5

**User Story:** As a user, I want to extract GPS coordinates from media files and convert them to city names, so that I can organize files by location.

#### Acceptance Criteria

1. WHEN processing an image with GPS EXIF data THEN the system SHALL extract latitude and longitude coordinates
2. WHEN processing a video with GPS metadata THEN the system SHALL extract coordinates from format tags
3. WHEN GPS coordinates are available THEN the system SHALL convert them to decimal degrees format
4. WHEN coordinates are available THEN the system SHALL query OpenStreetMap API to get city name
5. WHEN city lookup succeeds THEN the system SHALL clean up municipal prefixes from city names
6. IF GPS data is not available THEN the system SHALL display "No GPS" for location

### Requirement 6

**User Story:** As a user, I want to see a list of discovered files with their current and proposed new names, so that I can review changes before processing.

#### Acceptance Criteria

1. WHEN the user clicks "Show Files" THEN the system SHALL scan the selected folder for supported media files
2. WHEN scanning files THEN the system SHALL display progress updates showing current file being processed
3. WHEN files are discovered THEN the system SHALL display them in a table with columns for selection, current name, new name, location, and city
4. WHEN files have no metadata THEN the system SHALL show "No metadata" in the new name column
5. WHEN processing is complete THEN the system SHALL show statistics including total found files and files missing metadata

### Requirement 7

**User Story:** As a user, I want to select which files to process for renaming, so that I can have control over which files are modified.

#### Acceptance Criteria

1. WHEN the user clicks on a file's checkbox THEN the system SHALL toggle the selection state
2. WHEN the user clicks "Select All" THEN the system SHALL select or deselect all files
3. WHEN files are selected or deselected THEN the system SHALL update the selection count in real-time
4. WHEN no files are selected and user tries to process THEN the system SHALL display a warning message

### Requirement 8

**User Story:** As a user, I want to process selected files for renaming with progress feedback, so that I can track the operation status.

#### Acceptance Criteria

1. WHEN the user clicks "Process Files" THEN the system SHALL show a confirmation dialog with the number of selected files
2. WHEN processing begins THEN the system SHALL disable the process button and show progress updates
3. WHEN processing each file THEN the system SHALL display current file number and total count
4. WHEN a file is successfully renamed THEN the system SHALL increment the processed count
5. WHEN a file cannot be renamed THEN the system SHALL record the error and continue processing
6. WHEN processing completes THEN the system SHALL display results including success count, errors, and skipped files

### Requirement 9

**User Story:** As a user, I want the application to handle files without metadata gracefully, so that I can still identify and manage these files.

#### Acceptance Criteria

1. WHEN a file has no extractable metadata THEN the system SHALL propose adding an underscore prefix to the filename
2. WHEN processing a file with no metadata THEN the system SHALL rename it with underscore prefix if not already present
3. WHEN a file already has underscore prefix THEN the system SHALL skip it and report as already processed
4. WHEN displaying files without metadata THEN the system SHALL show count in the statistics

### Requirement 10

**User Story:** As a user, I want my settings to be saved and restored between sessions, so that I don't have to reconfigure the application each time.

#### Acceptance Criteria

1. WHEN the user changes the folder path THEN the system SHALL save this setting when "Save Settings" is clicked
2. WHEN the user changes the filename format THEN the system SHALL save this setting when "Save Settings" is clicked
3. WHEN the user resizes or moves the window THEN the system SHALL save the window geometry on application close
4. WHEN the application starts THEN the system SHALL restore the last used folder path and filename format
5. WHEN settings are saved successfully THEN the system SHALL display a confirmation message

### Requirement 11

**User Story:** As a user, I want the application to support multiple image and video formats, so that I can process all my media files in one tool.

#### Acceptance Criteria

1. WHEN scanning for files THEN the system SHALL support image formats: JPG, JPEG, PNG, GIF, BMP, TIFF, WebP, HEIC, HEIF
2. WHEN scanning for files THEN the system SHALL support video formats: MP4, AVI, MOV, MKV, WMV, FLV, WebM
3. WHEN processing HEIC/HEIF files THEN the system SHALL use pillow-heif for compatibility
4. WHEN encountering unsupported file types THEN the system SHALL ignore them during scanning

### Requirement 12

**User Story:** As a user, I want error handling and validation throughout the application, so that I can understand and resolve issues when they occur.

#### Acceptance Criteria

1. WHEN a file operation fails THEN the system SHALL capture the specific error and continue processing other files
2. WHEN network requests for city lookup fail THEN the system SHALL handle timeouts gracefully and continue processing
3. WHEN required dependencies are missing THEN the system SHALL display clear error messages with installation instructions
4. WHEN file permissions prevent operations THEN the system SHALL report permission errors specifically
5. WHEN the application encounters unexpected errors THEN the system SHALL provide debug information if debug mode is enabled