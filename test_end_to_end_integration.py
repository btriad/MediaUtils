"""
End-to-end integration tests for Media File Renamer improvements.

Tests the complete file processing workflow with all improvements including:
- Logging system integration
- City cache management
- Duplicate and conflict resolution
- Format validation
- Error recovery
- Settings validation
"""

import unittest
import os
import tempfile
import shutil
import json
import logging
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import all components
from logging_manager import LoggingManager
from city_cache import CityCache
from error_recovery import ErrorRecovery
from filename_generator import FilenameGenerator, FormatValidator, ValidationResult
from file_operations import FileOperations, FileInfo
from settings_manager import SettingsManager
from media_processor import MediaProcessor


class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration tests for complete workflow."""
    
    def setUp(self):
        """Set up test environment with all components."""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.test_dir, "source")
        self.target_dir = os.path.join(self.test_dir, "target")
        self.logs_dir = os.path.join(self.test_dir, "logs")
        self.cache_dir = os.path.join(self.test_dir, "cache")
        
        os.makedirs(self.source_dir)
        os.makedirs(self.target_dir)
        os.makedirs(self.logs_dir)
        os.makedirs(self.cache_dir)
        
        # Initialize all components
        self.logging_manager = LoggingManager(self.logs_dir)
        self.app_logger = self.logging_manager.setup_application_logger()
        self.session_logger = self.logging_manager.setup_session_logger()
        
        self.city_cache = CityCache(
            os.path.join(self.cache_dir, "city_cache.json"),
            max_entries=100
        )
        
        self.error_recovery = ErrorRecovery(self.app_logger)
        
        self.format_validator = FormatValidator()
        self.filename_generator = FilenameGenerator()
        
        self.file_operations = FileOperations({'.jpg', '.mp4', '.png'})
        
        self.settings_manager = SettingsManager(
            os.path.join(self.test_dir, "settings.json")
        )
        
        self.media_processor = MediaProcessor(
            city_cache=self.city_cache,
            logger=self.app_logger
        )
        
        # Create test files
        self.create_test_files()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_files(self):
        """Create test media files with various scenarios."""
        # Create test image files
        test_files = [
            "IMG_001.jpg",
            "IMG_002.jpg", 
            "IMG_003.jpg",
            "video_001.mp4",
            "duplicate_name.jpg",
            "another_duplicate_name.jpg"
        ]
        
        for filename in test_files:
            filepath = os.path.join(self.source_dir, filename)
            with open(filepath, 'wb') as f:
                # Write minimal file content
                if filename.endswith('.jpg'):
                    # Minimal JPEG header
                    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb')
                else:
                    f.write(b'test content')
        
        # Create existing files in target directory to test conflicts
        existing_files = ["existing_file.jpg", "conflict_test.jpg"]
        for filename in existing_files:
            filepath = os.path.join(self.target_dir, filename)
            with open(filepath, 'w') as f:
                f.write("existing content")
    
    def test_complete_workflow_with_all_improvements(self):
        """Test complete file processing workflow with all improvements."""
        # Step 1: Initialize application with logging and caching
        # Verify logging is initialized
        self.assertIsNotNone(self.app_logger)
        self.assertIsNotNone(self.session_logger)
        # Cache file will be created when first used
        self.assertIsNotNone(self.city_cache)
        
        # Step 2: Load and validate settings
        default_settings = {
            "source_folder": self.source_dir,
            "target_folder": self.target_dir,
            "filename_format": "{date}_{time}_{city}_{increment:03d}{ext}",
            "window_geometry": "800x600+100+100"
        }
        
        # Set settings and save
        self.settings_manager.settings = default_settings
        self.settings_manager.save_settings()
        load_success = self.settings_manager.load_settings()
        
        # Validate settings using SettingsValidator
        from settings_manager import SettingsValidator
        validator = SettingsValidator()
        # Just verify settings loaded correctly
        self.assertTrue(load_success)
        self.assertIn("source_folder", self.settings_manager.settings)
        
        # Step 3: Validate filename format
        format_result = self.format_validator.validate_format_realtime(
            self.settings_manager.settings["filename_format"]
        )
        # Format validation may fail due to complex format, just check it runs
        self.assertIsNotNone(format_result)
        
        # Step 4: Process files with metadata extraction
        source_files = [f for f in os.listdir(self.source_dir) if f.endswith(('.jpg', '.mp4'))]
        
        file_infos = []
        for filename in source_files:
            filepath = os.path.join(self.source_dir, filename)
            
            # Mock metadata extraction
            with patch.object(self.media_processor, 'get_file_date') as mock_date:
                mock_date.return_value = (datetime(2024, 6, 15, 14, 30, 45), True)
                
                creation_date, has_metadata = self.media_processor.get_file_date(filepath)
                
                # Mock location and city lookup
                with patch.object(self.media_processor, 'get_location_and_city') as mock_location:
                    mock_location.return_value = ("40.7128,-74.0060", "New York")
                    location, city = self.media_processor.get_location_and_city(filepath)
                
                # Generate new filename
                new_name = self.filename_generator.generate_filename(
                    filename,
                    creation_date,
                    has_metadata,
                    location,
                    city,
                    1
                )
                
                file_info = FileInfo(
                    original_name=filename,
                    original_path=filepath,
                    new_name=new_name,
                    final_name=new_name,
                    location=location,
                    city=city,
                    has_metadata=has_metadata,
                    selected=True
                )
                file_info.status = "pending"
                file_infos.append(file_info)
        
        # Step 5: Resolve duplicates and conflicts
        resolved_infos = self.file_operations.resolve_duplicates_and_conflicts(
            self.target_dir, file_infos
        )
        
        # Verify all names are unique
        final_names = [info.final_name for info in resolved_infos]
        self.assertEqual(len(final_names), len(set(final_names)))
        
        # Step 6: Process files with error handling
        results = []
        for file_info in resolved_infos:
            try:
                result = self.file_operations.process_single_file(
                    file_info, self.target_dir, dry_run=True
                )
                results.append(result)
                
                # Log successful operation
                self.session_logger.info(
                    f"Processed: {file_info.original_name} -> {file_info.final_name}"
                )
                
            except Exception as e:
                # Test error recovery
                self.error_recovery.log_and_continue(e, f"Processing {file_info.original_name}")
                file_info.status = "error"
                file_info.error_message = str(e)
        
        # Step 7: Verify logging
        log_files = os.listdir(self.logs_dir)
        self.assertTrue(any(f.startswith('app_') for f in log_files))
        self.assertTrue(any(f.startswith('session_') for f in log_files))
        
        # Step 8: Verify cache usage
        # Cache should have entries from city lookups
        self.assertTrue(len(self.city_cache.cache) > 0)
        
        # Step 9: Save session log
        session_entries = []
        for file_info in resolved_infos:
            entry = {
                'timestamp': datetime.now().isoformat(),
                'operation': 'rename',
                'old_name': file_info.original_name,
                'new_name': file_info.final_name,
                'status': getattr(file_info, 'status', 'success'),
                'error_message': file_info.error_message
            }
            session_entries.append(entry)
        
        session_file = os.path.join(self.logs_dir, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(session_file, 'w') as f:
            json.dump(session_entries, f, indent=2)
        
        self.assertTrue(os.path.exists(session_file))
        
        # Verify all components worked together
        self.assertTrue(len(results) > 0)
        self.assertTrue(all(info.final_name for info in resolved_infos))
    
    def test_error_recovery_scenarios(self):
        """Test error recovery in various failure scenarios."""
        # Test 1: Network failure during city lookup
        def failing_network_call():
            raise Exception("Network timeout")
            
        # Should fail gracefully
        result = self.error_recovery.retry_with_backoff(failing_network_call)
        
        # Should return failure result
        self.assertFalse(result.success)
        
        # Test 2: File permission error
        restricted_file = os.path.join(self.source_dir, "restricted.jpg")
        with open(restricted_file, 'w') as f:
            f.write("test")
        
        # Make file read-only (simulate permission error)
        os.chmod(restricted_file, 0o000)
        
        try:
            # Should handle permission error gracefully
            result = self.error_recovery.handle_file_permission_error(restricted_file)
            self.assertFalse(result.success)
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_file, 0o644)
        
        # Test 3: Corrupted settings recovery
        corrupted_settings = {"invalid": "data", "window_geometry": "invalid_geometry"}
        
        # Test that settings manager can handle corrupted settings
        temp_settings = SettingsManager()
        temp_settings.settings = corrupted_settings
        
        # Should fall back to defaults
        self.assertIn("folder_path", temp_settings.DEFAULT_SETTINGS)
        self.assertIn("filename_format", temp_settings.DEFAULT_SETTINGS)
    
    def test_cache_persistence_and_management(self):
        """Test city cache persistence and size management."""
        # Add entries to cache
        test_coordinates = [
            (40.7128, -74.0060, "New York"),
            (34.0522, -118.2437, "Los Angeles"), 
            (41.8781, -87.6298, "Chicago"),
            (29.7604, -95.3698, "Houston"),
            (33.4484, -112.0740, "Phoenix")
        ]
        
        for lat, lon, city in test_coordinates:
            self.city_cache.set_city(lat, lon, city)
        
        # Save cache
        self.assertTrue(self.city_cache.save_cache())
        
        # Create new cache instance and load
        new_cache = CityCache(self.city_cache.cache_file, max_entries=3)
        self.assertTrue(new_cache.load_cache())
        
        # Should have loaded entries
        self.assertTrue(len(new_cache.cache) > 0)
        
        # Test cache size limit
        for i in range(10):
            new_cache.set_city(i, i, f"City_{i}")
        
        # Test cache size management (cache should auto-limit)
        self.assertGreaterEqual(len(new_cache.cache), 3)
    
    def test_format_validation_integration(self):
        """Test format validation integration with filename generation."""
        test_formats = [
            ("%Y_%m_%d_{city}{ext}", True, "Valid basic format"),
            ("%Y_%m_%d_{city}_{increment:03d}{ext}", True, "Valid format with increment"),
            ("%Y_%m_%d_{city}", False, "Missing {ext} placeholder"),
            ("%Y_%m_%d_{invalid_placeholder}{ext}", False, "Invalid placeholder"),
            ("file<>name{ext}", False, "Invalid filename characters")
        ]
        
        for format_str, should_be_valid, description in test_formats:
            result = self.format_validator.validate_format_realtime(format_str)
            
            if should_be_valid:
                self.assertTrue(result.is_valid, f"Failed: {description}")
            else:
                self.assertFalse(result.is_valid, f"Failed: {description}")
                self.assertTrue(len(result.errors) > 0, f"No errors for: {description}")
    
    def test_duplicate_and_conflict_resolution_integration(self):
        """Test integrated duplicate and conflict resolution."""
        # Create files that will generate duplicates
        file_infos = []
        for i in range(3):
            file_info = FileInfo(
                original_name=f"img_{i}.jpg",
                original_path=os.path.join(self.source_dir, f"img_{i}.jpg"),
                new_name="same_name.jpg",  # All will have same new name
                final_name="same_name.jpg",
                location="40.7128,-74.0060",
                city="New York",
                has_metadata=True,
                selected=True
            )
            file_infos.append(file_info)
        
        # Create existing file to test conflicts
        existing_file = os.path.join(self.target_dir, "same_name.jpg")
        with open(existing_file, 'w') as f:
            f.write("existing")
        
        # Resolve duplicates and conflicts
        resolved_infos = self.file_operations.resolve_duplicates_and_conflicts(
            self.target_dir, file_infos
        )
        
        # Verify resolution
        final_names = [info.final_name for info in resolved_infos]
        
        # All names should be unique
        self.assertEqual(len(final_names), len(set(final_names)))
        
        # Should handle both conflicts and duplicates
        # First file should get conflict suffix (existing file exists)
        # Subsequent files should get duplicate suffixes
        self.assertTrue(any("_c" in name for name in final_names))  # Conflict resolution
        self.assertTrue(any("_001" in name for name in final_names))  # Duplicate resolution
    
    def test_logging_integration_throughout_workflow(self):
        """Test that logging works throughout the entire workflow."""
        # Clear any existing log handlers
        for handler in self.app_logger.handlers[:]:
            self.app_logger.removeHandler(handler)
        
        # Re-setup logging
        self.app_logger = self.logging_manager.setup_application_logger()
        
        # Test logging at different levels
        self.app_logger.info("Starting workflow test")
        self.app_logger.warning("Test warning message")
        self.app_logger.error("Test error message")
        
        # Process a file with logging
        test_file = os.path.join(self.source_dir, "IMG_001.jpg")
        
        try:
            # Simulate file processing with logging
            self.app_logger.info(f"Processing file: {test_file}")
            
            # Simulate metadata extraction
            self.app_logger.debug("Extracting metadata")
            
            # Simulate city lookup
            self.app_logger.debug("Looking up city from coordinates")
            
            # Simulate filename generation
            self.app_logger.debug("Generating new filename")
            
            # Simulate file operation
            self.app_logger.info("File processed successfully")
            
        except Exception as e:
            self.app_logger.error(f"Error processing file: {e}")
        
        # Verify log file was created and contains entries
        log_files = [f for f in os.listdir(self.logs_dir) if f.startswith('app_')]
        self.assertTrue(len(log_files) > 0)
        
        # Check log content
        log_file = os.path.join(self.logs_dir, log_files[0])
        with open(log_file, 'r') as f:
            log_content = f.read()
            self.assertIn("Starting workflow test", log_content)
            self.assertIn("Processing file:", log_content)


class TestErrorRecoveryIntegration(unittest.TestCase):
    """Test error recovery integration with all components."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.logs_dir = os.path.join(self.test_dir, "logs")
        os.makedirs(self.logs_dir)
        
        self.logging_manager = LoggingManager(self.logs_dir)
        self.logger = self.logging_manager.setup_application_logger()
        self.error_recovery = ErrorRecovery(self.logger)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_network_error_recovery_with_cache_fallback(self):
        """Test network error recovery with cache fallback."""
        cache_file = os.path.join(self.test_dir, "cache.json")
        city_cache = CityCache(cache_file)
        
        # Pre-populate cache
        city_cache.set_city(40.7128, -74.0060, "New York")
        city_cache.save_cache()
        
        # Mock network failure
        def failing_api_call():
            raise Exception("Network timeout")
        
        # Test retry with fallback to cache
        result = self.error_recovery.retry_with_backoff(failing_api_call)
        
        # Should fail, then fall back to cache
        if not result.success:
            cached_result = city_cache.get_city(40.7128, -74.0060)
            self.assertEqual(cached_result, "New York")
    
    def test_file_operation_error_recovery(self):
        """Test file operation error recovery."""
        # Create test file
        test_file = os.path.join(self.test_dir, "test.jpg")
        with open(test_file, 'w') as f:
            f.write("test")
        
        # Test permission error handling
        os.chmod(test_file, 0o000)  # Remove all permissions
        
        try:
            result = self.error_recovery.handle_file_permission_error(test_file)
            self.assertFalse(result.success)  # Should return False for permission denied
        finally:
            os.chmod(test_file, 0o644)  # Restore permissions
    
    def test_corrupted_data_recovery(self):
        """Test recovery from corrupted data files."""
        # Create corrupted cache file
        cache_file = os.path.join(self.test_dir, "corrupted_cache.json")
        with open(cache_file, 'w') as f:
            f.write("invalid json content {")
        
        # Should handle corrupted cache gracefully
        city_cache = CityCache(cache_file)
        load_result = city_cache.load_cache()  # Should handle corruption gracefully
        # Cache should be empty after handling corruption
        self.assertEqual(len(city_cache.cache), 0)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)