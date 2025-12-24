# Requirements Document - Media File Renamer Improvements

## Introduction

This document outlines enhancements to the existing Media File Renamer application to improve reliability, user experience, and data management. The improvements focus on better duplicate handling, persistent city caching, file conflict resolution, enhanced format validation, proper logging, error recovery, and settings validation.

## Requirements

### Requirement 1

**User Story:** As a user, I want duplicate filenames to be automatically resolved with sequential numbering, so that no files are skipped due to naming conflicts.

#### Acceptance Criteria

1. WHEN multiple files generate the same new filename THEN the system SHALL append sequential numbers to make them unique
2. WHEN the first duplicate is detected THEN the system SHALL add "_001" before the file extension
3. WHEN subsequent duplicates are found THEN the system SHALL increment the number (_002, _003, etc.)
4. WHEN checking for duplicates THEN the system SHALL consider both generated names and existing files in the target folder
5. WHEN displaying the file list THEN the system SHALL show the final unique names that will be used

### Requirement 2

**User Story:** As a user, I want city lookups to be cached persistently, so that repeated GPS coordinates don't require new API calls and the app works faster.

#### Acceptance Criteria

1. WHEN a GPS coordinate is looked up successfully THEN the system SHALL save the result to a local cache file
2. WHEN the same GPS coordinates are encountered again THEN the system SHALL use the cached city name instead of making an API call
3. WHEN the application starts THEN the system SHALL load the existing cache from file
4. WHEN the cache file becomes large THEN the system SHALL limit it to the most recent 1000 entries
5. WHEN the cache file is corrupted THEN the system SHALL create a new empty cache and continue operation
6. WHEN saving cache fails THEN the system SHALL log the error but continue normal operation

### Requirement 3

**User Story:** As a user, I want file conflicts to be resolved automatically, so that existing files are never accidentally overwritten.

#### Acceptance Criteria

1. WHEN a target filename already exists THEN the system SHALL append "_c1" before the file extension
2. WHEN "_c1" filename also exists THEN the system SHALL try "_c2", "_c3", etc. until finding an available name
3. WHEN checking for conflicts THEN the system SHALL verify the target file doesn't exist before renaming
4. WHEN displaying the file list THEN the system SHALL show the final conflict-resolved names
5. WHEN processing files THEN the system SHALL re-check for conflicts immediately before each rename operation

### Requirement 4

**User Story:** As a user, I want detailed format validation with helpful error messages, so that I can create valid filename patterns easily.

#### Acceptance Criteria

1. WHEN the user types in the format field THEN the system SHALL validate the pattern in real-time
2. WHEN the format is missing required placeholders THEN the system SHALL show specific error messages like "Missing {ext} placeholder"
3. WHEN the format contains invalid filename characters THEN the system SHALL highlight the problematic characters
4. WHEN the format has malformed placeholders THEN the system SHALL suggest corrections like "Did you mean {increment:03d}?"
5. WHEN the format is valid THEN the system SHALL show a green checkmark or "Valid format" message
6. WHEN the format has warnings but is usable THEN the system SHALL show the example with warning indicators

### Requirement 5

**User Story:** As a user, I want comprehensive logging throughout the application, so that I can troubleshoot issues and track operations.

#### Acceptance Criteria

1. WHEN the application starts THEN the system SHALL create a log file with timestamp in the filename
2. WHEN processing files THEN the system SHALL log each successful rename operation with old and new names
3. WHEN errors occur THEN the system SHALL log detailed error information including file paths and error messages
4. WHEN API calls are made THEN the system SHALL log the requests and responses for debugging
5. WHEN the application encounters warnings THEN the system SHALL log them with appropriate severity levels
6. WHEN log files become large THEN the system SHALL rotate them to prevent excessive disk usage
7. WHEN logging fails THEN the system SHALL continue operation and maintain existing print statements as fallback

### Requirement 6

**User Story:** As a user, I want the application to recover gracefully from common errors, so that temporary issues don't stop the entire process.

#### Acceptance Criteria

1. WHEN ffprobe is not available THEN the system SHALL log the issue and continue processing other files
2. WHEN network requests for city lookup fail THEN the system SHALL retry up to 3 times with exponential backoff
3. WHEN network requests timeout THEN the system SHALL use cached data if available or continue without city information
4. WHEN file permissions prevent reading metadata THEN the system SHALL log the error and mark the file as no metadata
5. WHEN image files are corrupted THEN the system SHALL log the error and continue processing other files
6. WHEN the GPS API returns invalid data THEN the system SHALL log the response and continue without city information

### Requirement 7

**User Story:** As a user, I want my settings to be validated when loaded, so that corrupted or invalid settings don't crash the application.

#### Acceptance Criteria

1. WHEN loading settings from file THEN the system SHALL validate each setting against expected types and ranges
2. WHEN a setting has an invalid type THEN the system SHALL use the default value and log a warning
3. WHEN the settings file is corrupted THEN the system SHALL create new default settings and log the issue
4. WHEN folder paths in settings don't exist THEN the system SHALL reset to default path and notify the user
5. WHEN filename formats in settings are invalid THEN the system SHALL reset to default format and log the issue
6. WHEN window geometry settings are invalid THEN the system SHALL use default window size and position

### Requirement 8

**User Story:** As a user, I want operation logs to be saved for each processing session, so that I can review what changes were made.

#### Acceptance Criteria

1. WHEN starting a file processing operation THEN the system SHALL create a session log with timestamp
2. WHEN files are successfully renamed THEN the system SHALL record the old name, new name, and timestamp in the session log
3. WHEN files are skipped or encounter errors THEN the system SHALL record the reason in the session log
4. WHEN processing completes THEN the system SHALL save the session log to a dated file in a logs directory
5. WHEN the logs directory doesn't exist THEN the system SHALL create it automatically
6. WHEN saving session logs fails THEN the system SHALL display a warning but continue operation

### Requirement 9

**User Story:** As a user, I want the city cache to be managed efficiently, so that it doesn't consume excessive disk space or memory.

#### Acceptance Criteria

1. WHEN the cache reaches 1000 entries THEN the system SHALL remove the oldest entries to maintain the limit
2. WHEN saving the cache THEN the system SHALL use JSON format for human readability and debugging
3. WHEN loading the cache THEN the system SHALL handle missing or corrupted cache files gracefully
4. WHEN GPS coordinates are very close (within 0.001 degrees) THEN the system SHALL use the existing cached city
5. WHEN the cache file becomes corrupted THEN the system SHALL backup the corrupted file and create a new cache

### Requirement 10

**User Story:** As a user, I want format validation to provide helpful suggestions, so that I can quickly fix common mistakes in filename patterns.

#### Acceptance Criteria

1. WHEN the user types an invalid date format THEN the system SHALL suggest valid alternatives like "%Y for 4-digit year"
2. WHEN the user forgets the {ext} placeholder THEN the system SHALL show "Add {ext} to include file extension"
3. WHEN the user uses invalid characters THEN the system SHALL list the problematic characters and suggest replacements
4. WHEN the user has unmatched braces THEN the system SHALL highlight the location of the syntax error
5. WHEN the user creates a valid format THEN the system SHALL show available additional placeholders they might want to use