#!/usr/bin/env python3
"""
Integration Verification Script

This script verifies that all components of the Media File Renamer
are properly integrated and working together.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from logging_manager import LoggingManager
from city_cache import CityCache
from error_recovery import ErrorRecovery
from settings_manager import SettingsManager
from media_processor import MediaProcessor
from file_operations import FileOperations
from filename_generator import FilenameGenerator, FormatValidator


def test_system_integration():
    """Test integration of all major systems."""
    print("=" * 60)
    print("Media File Renamer - Integration Verification")
    print("=" * 60)
    
    # Create temporary test environment
    test_dir = tempfile.mkdtemp()
    logs_dir = os.path.join(test_dir, "logs")
    cache_dir = os.path.join(test_dir, "cache")
    
    try:
        os.makedirs(logs_dir)
        os.makedirs(cache_dir)
        
        print(f"✓ Test environment created: {test_dir}")
        
        # Test 1: Initialize Logging System
        print("\n1. Testing Logging System Integration...")
        logging_manager = LoggingManager(logs_dir)
        app_logger = logging_manager.setup_application_logger()
        session_logger = logging_manager.setup_session_logger()
        
        app_logger.info("Integration test started")
        print("   ✓ Application logger initialized")
        print("   ✓ Session logger initialized")
        
        # Test 2: Initialize City Cache
        print("\n2. Testing City Cache Integration...")
        cache_file = os.path.join(cache_dir, "test_cache.json")
        city_cache = CityCache(cache_file, max_entries=100)
        
        # Add test entries
        city_cache.set_city(40.7128, -74.0060, "New York")
        city_cache.set_city(34.0522, -118.2437, "Los Angeles")
        
        # Test cache operations
        cached_city = city_cache.get_city(40.7128, -74.0060)
        assert cached_city == "New York", f"Expected 'New York', got '{cached_city}'"
        
        # Test cache persistence
        city_cache.save_cache()
        
        new_cache = CityCache(cache_file)
        new_cache.load_cache()
        cached_city2 = new_cache.get_city(40.7128, -74.0060)
        assert cached_city2 == "New York", "Cache persistence failed"
        
        print("   ✓ City cache operations working")
        print("   ✓ Cache persistence working")
        
        # Test 3: Initialize Error Recovery
        print("\n3. Testing Error Recovery Integration...")
        error_recovery = ErrorRecovery(app_logger)
        
        # Test retry mechanism
        def failing_function():
            raise Exception("Test failure")
        
        result = error_recovery.retry_with_backoff(failing_function)
        assert not result.success, "Error recovery should return failure"
        print("   ✓ Error recovery retry mechanism working")
        
        # Test 4: Initialize Settings Manager
        print("\n4. Testing Settings Manager Integration...")
        settings_file = os.path.join(test_dir, "test_settings.json")
        settings_manager = SettingsManager(settings_file)
        
        # Test settings operations
        settings_manager.set("test_key", "test_value")
        settings_manager.save_settings()
        
        new_settings = SettingsManager(settings_file)
        new_settings.load_settings()
        assert new_settings.get("test_key") == "test_value", "Settings persistence failed"
        
        print("   ✓ Settings persistence working")
        
        # Test 5: Initialize Media Processor with integrated systems
        print("\n5. Testing Media Processor Integration...")
        media_processor = MediaProcessor(
            city_cache=city_cache,
            logger=app_logger,
            error_recovery=error_recovery
        )
        
        # Verify integrated systems are used
        assert media_processor.city_cache is city_cache, "City cache not integrated"
        assert media_processor.logger is app_logger, "Logger not integrated"
        assert media_processor.error_recovery is error_recovery, "Error recovery not integrated"
        
        print("   ✓ Media processor integrated with all systems")
        
        # Test 6: Initialize File Operations with integrated systems
        print("\n6. Testing File Operations Integration...")
        supported_extensions = {'.jpg', '.mp4', '.png'}
        file_operations = FileOperations(
            supported_extensions,
            logger=app_logger,
            logging_manager=logging_manager,
            error_recovery=error_recovery
        )
        
        # Verify integrated systems are used
        assert file_operations.logger is app_logger, "Logger not integrated in FileOperations"
        assert file_operations.logging_manager is logging_manager, "LoggingManager not integrated"
        assert file_operations.error_recovery is error_recovery, "Error recovery not integrated"
        
        print("   ✓ File operations integrated with all systems")
        
        # Test 7: Test Format Validation
        print("\n7. Testing Format Validation Integration...")
        format_validator = FormatValidator()
        
        # Test valid format
        result = format_validator.validate_format_realtime("%Y_%m_%d_{city}{ext}")
        assert result.is_valid, f"Valid format failed validation: {result.errors}"
        
        # Test invalid format
        result = format_validator.validate_format_realtime("%Y_%m_%d_{city}")  # Missing {ext}
        assert not result.is_valid, "Invalid format passed validation"
        assert len(result.errors) > 0, "No errors reported for invalid format"
        
        print("   ✓ Format validation working correctly")
        
        # Test 8: Test End-to-End Workflow Simulation
        print("\n8. Testing End-to-End Workflow Simulation...")
        
        # Create test file
        test_source = os.path.join(test_dir, "source")
        os.makedirs(test_source)
        test_file = os.path.join(test_source, "test_image.jpg")
        
        # Create minimal JPEG file
        with open(test_file, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb')
        
        # Test file discovery
        discovered_files = file_operations.discover_files(test_source)
        assert len(discovered_files) == 1, f"Expected 1 file, found {len(discovered_files)}"
        
        print("   ✓ File discovery working")
        
        # Test logging throughout workflow
        app_logger.info("Workflow simulation completed successfully")
        
        # Test session log saving
        logging_manager.log_operation("test_operation", {
            "file": "test_image.jpg",
            "status": "success"
        })
        
        session_log_path = logging_manager.save_session_log()
        assert session_log_path is not None, "Session log save failed"
        assert os.path.exists(session_log_path), "Session log file not created"
        
        print("   ✓ Session logging working")
        print("   ✓ End-to-end workflow simulation successful")
        
        # Test 9: Verify Log Files Created
        print("\n9. Verifying Log Files...")
        log_files = os.listdir(logs_dir)
        app_logs = [f for f in log_files if f.startswith('app_')]
        session_logs = [f for f in log_files if f.startswith('session_')]
        
        assert len(app_logs) > 0, "No application log files created"
        assert len(session_logs) > 0, "No session log files created"
        
        print(f"   ✓ Application logs: {len(app_logs)} files")
        print(f"   ✓ Session logs: {len(session_logs)} files")
        
        print("\n" + "=" * 60)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("✅ All systems are properly integrated and working together")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            shutil.rmtree(test_dir, ignore_errors=True)
            print(f"\n🧹 Test environment cleaned up")
        except Exception as e:
            print(f"Warning: Could not clean up test directory: {e}")


if __name__ == "__main__":
    success = test_system_integration()
    sys.exit(0 if success else 1)