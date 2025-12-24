"""
Unit tests for settings validation functionality.

Tests validation of different setting types, corrupted settings recovery,
and comprehensive settings validation according to requirements 7.1, 7.2, 7.3.
"""

import unittest
import json
import os
import tempfile
import shutil
from unittest.mock import patch, mock_open
from settings_manager import SettingsManager


class TestSettingsValidation(unittest.TestCase):
    """Test cases for settings validation and recovery."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_settings_file = os.path.join(self.test_dir, "test_settings.json")
        self.settings_manager = SettingsManager(self.test_settings_file)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_validate_string_settings(self):
        """Test validation of string-type settings."""
        # Valid string settings
        self.assertTrue(self.settings_manager.validate_setting("folder_path", "C:\\Users"))
        self.assertTrue(self.settings_manager.validate_setting("filename_format", "%Y-%m-%d.{ext}"))
        self.assertTrue(self.settings_manager.validate_setting("window_geometry", "800x600"))
        
        # Invalid string settings (wrong type)
        self.assertFalse(self.settings_manager.validate_setting("folder_path", 123))
        self.assertFalse(self.settings_manager.validate_setting("filename_format", None))
        self.assertFalse(self.settings_manager.validate_setting("window_geometry", []))
    
    def test_validate_boolean_settings(self):
        """Test validation of boolean-type settings."""
        # Valid boolean settings
        self.assertTrue(self.settings_manager.validate_setting("auto_select_all", True))
        self.assertTrue(self.settings_manager.validate_setting("auto_select_all", False))
        self.assertTrue(self.settings_manager.validate_setting("show_missing_metadata_warning", True))
        
        # Invalid boolean settings (wrong type)
        self.assertFalse(self.settings_manager.validate_setting("auto_select_all", "true"))
        self.assertFalse(self.settings_manager.validate_setting("auto_select_all", 1))
        self.assertFalse(self.settings_manager.validate_setting("show_missing_metadata_warning", None))
    
    def test_validate_integer_settings(self):
        """Test validation of integer-type settings."""
        # Valid integer settings
        self.assertTrue(self.settings_manager.validate_setting("api_timeout", 5))
        self.assertTrue(self.settings_manager.validate_setting("max_city_cache_size", 1000))
        self.assertTrue(self.settings_manager.validate_setting("api_timeout", 1))
        
        # Invalid integer settings (wrong type)
        self.assertFalse(self.settings_manager.validate_setting("api_timeout", "5"))
        self.assertFalse(self.settings_manager.validate_setting("api_timeout", 5.5))
        self.assertFalse(self.settings_manager.validate_setting("max_city_cache_size", None))
        
        # Invalid integer settings (out of range)
        self.assertFalse(self.settings_manager.validate_setting("api_timeout", 0))
        self.assertFalse(self.settings_manager.validate_setting("api_timeout", -1))
        self.assertFalse(self.settings_manager.validate_setting("max_city_cache_size", -100))
    
    def test_validate_list_settings(self):
        """Test validation of list-type settings."""
        # Valid list settings
        valid_formats = ["%Y-%m-%d.{ext}", "%Y%m%d_{city}.{ext}"]
        self.assertTrue(self.settings_manager.validate_setting("last_used_formats", valid_formats))
        self.assertTrue(self.settings_manager.validate_setting("last_used_formats", []))
        
        # Invalid list settings (wrong type)
        self.assertFalse(self.settings_manager.validate_setting("last_used_formats", "not a list"))
        self.assertFalse(self.settings_manager.validate_setting("last_used_formats", None))
        
        # Invalid list settings (wrong element types)
        invalid_formats = ["%Y-%m-%d.{ext}", 123, None]
        self.assertFalse(self.settings_manager.validate_setting("last_used_formats", invalid_formats))
    
    def test_validate_folder_paths(self):
        """Test validation of folder path settings."""
        # Create a test directory
        test_folder = os.path.join(self.test_dir, "test_folder")
        os.makedirs(test_folder)
        
        # Valid folder paths
        self.assertTrue(self.settings_manager.validate_folder_path(test_folder))
        self.assertTrue(self.settings_manager.validate_folder_path(self.test_dir))
        
        # Invalid folder paths
        self.assertFalse(self.settings_manager.validate_folder_path("/nonexistent/path"))
        self.assertFalse(self.settings_manager.validate_folder_path(""))
        self.assertFalse(self.settings_manager.validate_folder_path(None))
        
        # Path that exists but is a file, not directory
        test_file = os.path.join(self.test_dir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        self.assertFalse(self.settings_manager.validate_folder_path(test_file))
    
    def test_validate_filename_formats(self):
        """Test validation of filename format patterns."""
        # Valid formats
        valid_formats = [
            "%Y-%m-%d.{ext}",
            "%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}",
            "{city}_%Y%m%d.{ext}",
            "IMG_%Y%m%d_{increment:03d}.{ext}"
        ]
        
        for fmt in valid_formats:
            self.assertTrue(self.settings_manager.validate_filename_format(fmt))
        
        # Invalid formats (missing required placeholders)
        invalid_formats = [
            "%Y-%m-%d",  # Missing {ext}
            "{ext}",     # Missing date components
            "",          # Empty format
            None         # None format
        ]
        
        for fmt in invalid_formats:
            self.assertFalse(self.settings_manager.validate_filename_format(fmt))
        
        # Invalid formats (invalid characters for filenames)
        invalid_char_formats = [
            "%Y-%m-%d<test>.{ext}",  # Contains <
            "%Y-%m-%d|test.{ext}",   # Contains |
            "%Y-%m-%d\"test\".{ext}", # Contains "
        ]
        
        for fmt in invalid_char_formats:
            self.assertFalse(self.settings_manager.validate_filename_format(fmt))
    
    def test_validate_window_geometry(self):
        """Test validation of window geometry settings."""
        # Valid geometries
        valid_geometries = [
            "800x600",
            "1200x800",
            "1920x1080",
            "800x600+100+50"  # With position
        ]
        
        for geom in valid_geometries:
            self.assertTrue(self.settings_manager.validate_window_geometry(geom))
        
        # Invalid geometries
        invalid_geometries = [
            "800",           # Missing height
            "800x",          # Missing height
            "x600",          # Missing width
            "800x600x100",   # Too many dimensions
            "abcxdef",       # Non-numeric
            "",              # Empty
            None,            # None
            "0x0",           # Zero dimensions
            "800x0",         # Zero height
            "0x600"          # Zero width
        ]
        
        for geom in invalid_geometries:
            self.assertFalse(self.settings_manager.validate_window_geometry(geom))
    
    def test_corrupted_settings_recovery(self):
        """Test recovery from corrupted settings files."""
        # Create corrupted JSON file
        with open(self.test_settings_file, 'w') as f:
            f.write('{"invalid": json, "missing": quote}')
        
        # Should recover with defaults
        manager = SettingsManager(self.test_settings_file)
        self.assertEqual(manager.settings, SettingsManager.DEFAULT_SETTINGS)
        
        # Verify backup was created
        backup_file = self.test_settings_file + ".corrupted.backup"
        self.assertTrue(os.path.exists(backup_file))
    
    def test_partial_settings_recovery(self):
        """Test recovery when some settings are valid and others are corrupted."""
        # Create partially corrupted settings
        partial_settings = {
            "folder_path": "C:\\Valid\\Path",
            "filename_format": 123,  # Invalid type
            "auto_select_all": "not_boolean",  # Invalid type
            "api_timeout": 5,  # Valid
            "invalid_setting": "should_be_ignored"
        }
        
        with open(self.test_settings_file, 'w') as f:
            json.dump(partial_settings, f)
        
        manager = SettingsManager(self.test_settings_file)
        
        # Valid settings should be preserved
        self.assertEqual(manager.get("folder_path"), "C:\\Valid\\Path")
        self.assertEqual(manager.get("api_timeout"), 5)
        
        # Invalid settings should revert to defaults
        self.assertEqual(manager.get("filename_format"), SettingsManager.DEFAULT_SETTINGS["filename_format"])
        self.assertEqual(manager.get("auto_select_all"), SettingsManager.DEFAULT_SETTINGS["auto_select_all"])
    
    def test_missing_settings_file_recovery(self):
        """Test behavior when settings file doesn't exist."""
        # Remove settings file if it exists
        if os.path.exists(self.test_settings_file):
            os.remove(self.test_settings_file)
        
        manager = SettingsManager(self.test_settings_file)
        
        # Should use defaults
        self.assertEqual(manager.settings, SettingsManager.DEFAULT_SETTINGS)
        
        # Should create new settings file
        self.assertTrue(os.path.exists(self.test_settings_file))
    
    def test_comprehensive_settings_validation(self):
        """Test comprehensive validation of all settings at once."""
        # Valid settings
        valid_settings = {
            "folder_path": self.test_dir,
            "filename_format": "%Y-%m-%d.{ext}",
            "window_geometry": "800x600",
            "last_used_formats": ["%Y-%m-%d.{ext}"],
            "auto_select_all": True,
            "show_missing_metadata_warning": False,
            "api_timeout": 10,
            "max_city_cache_size": 500
        }
        
        validation_result = self.settings_manager.validate_all_settings(valid_settings)
        self.assertTrue(validation_result.is_valid)
        self.assertEqual(len(validation_result.errors), 0)
        
        # Invalid settings
        invalid_settings = {
            "folder_path": "/nonexistent/path",
            "filename_format": "invalid_format",  # Missing {ext}
            "window_geometry": "invalid_geometry",
            "last_used_formats": "not_a_list",
            "auto_select_all": "not_boolean",
            "api_timeout": -1,
            "max_city_cache_size": "not_integer"
        }
        
        validation_result = self.settings_manager.validate_all_settings(invalid_settings)
        self.assertFalse(validation_result.is_valid)
        self.assertGreater(len(validation_result.errors), 0)
    
    def test_settings_repair(self):
        """Test automatic repair of corrupted settings."""
        corrupted_settings = {
            "folder_path": "/nonexistent/path",
            "filename_format": "invalid",
            "window_geometry": "invalid",
            "auto_select_all": "not_boolean",
            "api_timeout": -1
        }
        
        repaired_settings = self.settings_manager.repair_corrupted_settings(corrupted_settings)
        
        # Should have valid defaults for corrupted values
        self.assertEqual(repaired_settings["folder_path"], SettingsManager.DEFAULT_SETTINGS["folder_path"])
        self.assertEqual(repaired_settings["filename_format"], SettingsManager.DEFAULT_SETTINGS["filename_format"])
        self.assertEqual(repaired_settings["window_geometry"], SettingsManager.DEFAULT_SETTINGS["window_geometry"])
        self.assertEqual(repaired_settings["auto_select_all"], SettingsManager.DEFAULT_SETTINGS["auto_select_all"])
        self.assertEqual(repaired_settings["api_timeout"], SettingsManager.DEFAULT_SETTINGS["api_timeout"])


if __name__ == '__main__':
    unittest.main()