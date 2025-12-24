#!/usr/bin/env python3
"""
Media File Renamer - Main Entry Point

A GUI application for renaming media files based on EXIF metadata and GPS location data.

Features:
- Extracts creation date/time from images and videos
- Converts GPS coordinates to city names
- Customizable filename formats with placeholders
- Batch processing with progress tracking
- Settings persistence and validation
- Comprehensive logging and error recovery
- Persistent city caching for improved performance
- Enhanced duplicate and conflict resolution

Author: Media Renamer Team
Version: 2.0.0
"""

import sys
import os
import atexit
import logging
from pathlib import Path

# Add current directory to Python path for module imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from gui_components import MediaRenamerGUI
    from logging_manager import LoggingManager
    from city_cache import CityCache
    from error_recovery import ErrorRecovery
    from settings_manager import SettingsManager
except ImportError as e:
    print(f"Error importing required components: {e}")
    print("Please ensure all required modules are in the same directory.")
    sys.exit(1)


def check_dependencies():
    """
    Check if all required dependencies are available.
    
    Returns:
        tuple: (success: bool, missing_deps: list)
    """
    required_modules = [
        ('PIL', 'Pillow'),
        ('pillow_heif', 'pillow-heif'),
    ]
    
    missing_deps = []
    
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_deps.append(package_name)
    
    return len(missing_deps) == 0, missing_deps


def check_ffmpeg():
    """
    Check if ffmpeg/ffprobe is available for video processing.
    
    Returns:
        bool: True if ffmpeg is available
    """
    import subprocess
    
    # Check for local ffprobe.exe
    local_ffprobe = Path(__file__).parent / 'ffprobe.exe'
    if local_ffprobe.exists():
        return True
    
    # Check system PATH
    try:
        subprocess.run(['ffprobe', '-version'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def print_system_info():
    """Print system and dependency information."""
    print("Media File Renamer v2.0.0 - Enhanced Edition")
    print("=" * 50)
    print(f"Python version: {sys.version}")
    print(f"Operating system: {os.name}")
    print(f"Current directory: {os.getcwd()}")
    
    # Check dependencies
    deps_ok, missing_deps = check_dependencies()
    if deps_ok:
        print("✓ All Python dependencies available")
    else:
        print(f"✗ Missing dependencies: {', '.join(missing_deps)}")
    
    # Check ffmpeg
    if check_ffmpeg():
        print("✓ FFmpeg/ffprobe available for video processing")
    else:
        print("⚠ FFmpeg/ffprobe not found - video processing will be limited")
    
    # Check system directories
    logs_dir = current_dir / "logs"
    cache_dir = current_dir / "cache"
    print(f"✓ Logs directory: {logs_dir}")
    print(f"✓ Cache directory: {cache_dir}")
    
    print("=" * 50)


def initialize_application_systems():
    """
    Initialize all application systems including logging, caching, and error recovery.
    
    Returns:
        tuple: (logging_manager, city_cache, error_recovery, settings_manager, logger)
    """
    try:
        # Create logs directory
        logs_dir = current_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Initialize logging system
        logging_manager = LoggingManager(str(logs_dir))
        app_logger = logging_manager.setup_application_logger()
        session_logger = logging_manager.setup_session_logger()
        
        app_logger.info("Application starting - Media File Renamer v2.0.0")
        
        # Initialize settings manager with validation
        settings_file = current_dir / "settings.json"
        settings_manager = SettingsManager(str(settings_file))
        
        # Load and validate settings
        if not settings_manager.load_settings():
            app_logger.warning("Settings file not found or corrupted, using defaults")
        
        # Initialize city cache
        cache_dir = current_dir / "cache"
        cache_dir.mkdir(exist_ok=True)
        cache_file = cache_dir / "city_cache.json"
        
        city_cache = CityCache(str(cache_file), max_entries=1000)
        if city_cache.load_cache():
            app_logger.info(f"City cache loaded with {len(city_cache.cache)} entries")
        else:
            app_logger.info("Starting with empty city cache")
        
        # Initialize error recovery system
        error_recovery = ErrorRecovery(app_logger)
        
        app_logger.info("All application systems initialized successfully")
        
        return logging_manager, city_cache, error_recovery, settings_manager, app_logger
        
    except Exception as e:
        print(f"Failed to initialize application systems: {e}")
        if '--debug' in sys.argv:
            import traceback
            traceback.print_exc()
        raise


def setup_shutdown_handlers(city_cache, logging_manager, logger):
    """
    Set up handlers for graceful application shutdown.
    
    Args:
        city_cache: City cache instance to save on shutdown
        logging_manager: Logging manager for cleanup
        logger: Application logger
    """
    def shutdown_handler():
        """Handle graceful shutdown of application systems."""
        try:
            logger.info("Application shutting down...")
            
            # Save city cache
            if city_cache.save_cache():
                logger.info("City cache saved successfully")
            else:
                logger.warning("Failed to save city cache")
            
            # Save any pending session logs
            logging_manager.save_session_log()
            
            logger.info("Application shutdown complete")
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
    
    # Register shutdown handler
    atexit.register(shutdown_handler)


def main():
    """Main application entry point with comprehensive system initialization."""
    # Print system information in debug mode
    if '--debug' in sys.argv or '-d' in sys.argv:
        print_system_info()
    
    # Check critical dependencies
    deps_ok, missing_deps = check_dependencies()
    if not deps_ok:
        print("Error: Missing required dependencies!")
        print(f"Please install: {', '.join(missing_deps)}")
        print("\nInstall with:")
        for dep in missing_deps:
            print(f"  pip install {dep}")
        return 1
    
    # Handle help before initializing systems
    if '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        return 0
    
    try:
        # Initialize all application systems
        logging_manager, city_cache, error_recovery, settings_manager, logger = initialize_application_systems()
        
        # Set up graceful shutdown handlers
        setup_shutdown_handlers(city_cache, logging_manager, logger)
        
        # Create and configure the GUI application with all systems
        app = MediaRenamerGUI(
            logging_manager=logging_manager,
            city_cache=city_cache,
            error_recovery=error_recovery,
            settings_manager=settings_manager
        )
        
        # Start the application
        logger.info("Starting GUI application...")
        print("Starting Media File Renamer with enhanced features...")
        
        app.run()
        
        logger.info("Application completed successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
        if 'logger' in locals():
            logger.info("Application interrupted by user")
        return 1
    except Exception as e:
        error_msg = f"Fatal error: {e}"
        print(error_msg)
        
        if 'logger' in locals():
            logger.error(error_msg)
        
        if '--debug' in sys.argv:
            import traceback
            traceback.print_exc()
        return 1


def print_help():
    """Print command line help information."""
    help_text = """
Media File Renamer v2.0.0 - Enhanced Edition

USAGE:
    python main.py [OPTIONS]

OPTIONS:
    -h, --help      Show this help message
    -d, --debug     Show debug information and system details

DESCRIPTION:
    A comprehensive GUI application for renaming media files based on their metadata
    with advanced features for reliability and user experience.
    
    Supported file types:
    - Images: JPG, JPEG, PNG, GIF, BMP, TIFF, WebP, HEIC, HEIF
    - Videos: MP4, AVI, MOV, MKV, WMV, FLV, WebM
    
    Core Features:
    - Extract creation date/time from EXIF data
    - Convert GPS coordinates to city names with persistent caching
    - Customizable filename formats with real-time validation
    - Batch processing with progress tracking
    - Automatic duplicate and conflict resolution
    - Comprehensive logging and error recovery
    - Settings validation and corruption recovery
    
    Enhanced Features (v2.0):
    - Persistent city cache for improved performance
    - Intelligent duplicate filename resolution with sequential numbering
    - File conflict resolution to prevent overwrites
    - Real-time format validation with helpful suggestions
    - Comprehensive application and session logging
    - Robust error recovery with retry mechanisms
    - Settings validation and automatic corruption recovery
    - Enhanced user feedback and progress indicators

REQUIREMENTS:
    - Python 3.7+
    - Pillow (for image processing)
    - pillow-heif (for HEIC/HEIF support)
    - FFmpeg (optional, for video metadata)

EXAMPLES:
    python main.py              # Start the GUI application
    python main.py --debug      # Start with debug information and system details
    python main.py --help       # Show this help message

DIRECTORIES:
    logs/                       # Application and session logs
    cache/                      # Persistent city cache storage
    settings.json              # Application settings

For more information, visit: https://github.com/your-repo/media-renamer
"""
    print(help_text)


if __name__ == "__main__":
    sys.exit(main())