#!/usr/bin/env python3
"""
Test script for cache management functionality.

This script tests the cache loading and saving functionality
integrated into the GUI application.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from city_cache import CityCache
from gui_components import MediaRenamerGUI


class TestCacheManagement(unittest.TestCase):
    """Test cases for cache management in GUI application."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "test_cache.json")
        
        # Create a test cache with some data
        self.test_cache = CityCache(cache_file=self.cache_file, max_entries=10)
        self.test_cache.set_city(40.7128, -74.0060, "New York")
        self.test_cache.set_city(51.5074, -0.1278, "London")
        self.test_cache.save_cache()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('tkinter.Tk')
    @patch('gui_components.SettingsManager')
    @patch('gui_components.LoggingManager')
    def test_cache_loading_on_startup(self, mock_logging_manager, mock_settings_manager, mock_tk):
        """Test that cache is loaded on application startup."""
        # Mock settings manager to return our test cache file
        mock_settings_instance = MagicMock()
        mock_settings_instance.get.side_effect = lambda key, default=None: {
            "max_city_cache_size": 1000,
            "window_geometry": "1200x600"
        }.get(key, default)
        mock_settings_manager.return_value = mock_settings_instance
        
        # Mock logging manager
        mock_logging_instance = MagicMock()
        mock_logging_instance.setup_application_logger.return_value = MagicMock()
        mock_logging_manager.return_value = mock_logging_instance
        
        # Mock Tk root
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        
        # Patch the cache file path to use our test cache
        with patch.object(CityCache, '__init__', return_value=None) as mock_cache_init:
            with patch.object(CityCache, 'load_cache', return_value=True) as mock_load:
                with patch.object(CityCache, 'get_cache_stats', return_value={'total_entries': 2}):
                    # Create GUI instance (this should trigger cache loading)
                    gui = MediaRenamerGUI()
                    
                    # Verify cache loading was called
                    mock_load.assert_called_once()
    
    @patch('tkinter.Tk')
    @patch('gui_components.SettingsManager')
    @patch('gui_components.LoggingManager')
    def test_cache_saving_on_shutdown(self, mock_logging_manager, mock_settings_manager, mock_tk):
        """Test that cache is saved on application shutdown."""
        # Mock settings manager
        mock_settings_instance = MagicMock()
        mock_settings_instance.get.side_effect = lambda key, default=None: {
            "max_city_cache_size": 1000,
            "window_geometry": "1200x600"
        }.get(key, default)
        mock_settings_instance.save_settings.return_value = True
        mock_settings_manager.return_value = mock_settings_instance
        
        # Mock logging manager
        mock_logging_instance = MagicMock()
        mock_logging_instance.setup_application_logger.return_value = MagicMock()
        mock_logging_manager.return_value = mock_logging_instance
        
        # Mock Tk root
        mock_root = MagicMock()
        mock_root.geometry.return_value = "1200x600"
        mock_tk.return_value = mock_root
        
        # Create GUI instance with mocked cache
        with patch.object(CityCache, '__init__', return_value=None):
            with patch.object(CityCache, 'load_cache', return_value=True):
                with patch.object(CityCache, 'get_cache_stats', return_value={'total_entries': 2}):
                    with patch.object(CityCache, 'save_cache', return_value=True) as mock_save:
                        gui = MediaRenamerGUI()
                        
                        # Trigger shutdown
                        gui.on_closing()
                        
                        # Verify cache saving was called
                        mock_save.assert_called_once()
    
    def test_cache_statistics_display(self):
        """Test cache statistics display functionality."""
        # Create a cache with known data
        cache = CityCache(cache_file=self.cache_file, max_entries=10)
        cache.load_cache()
        
        # Get statistics
        stats = cache.get_cache_stats()
        
        # Verify statistics contain expected information
        self.assertIn('total_entries', stats)
        self.assertIn('max_entries', stats)
        self.assertIn('cache_file', stats)
        self.assertIn('file_exists', stats)
        self.assertIn('coordinate_tolerance', stats)
        
        # Verify values
        self.assertEqual(stats['total_entries'], 2)  # We added 2 cities in setUp
        self.assertEqual(stats['max_entries'], 10)
        self.assertTrue(stats['file_exists'])
    
    def test_cache_status_update_format(self):
        """Test that cache status is formatted correctly."""
        # Create a cache with test data
        cache = CityCache(cache_file=self.cache_file, max_entries=10)
        cache.load_cache()
        
        stats = cache.get_cache_stats()
        expected_status = f"Cache: {stats['total_entries']} entries"
        
        # Verify the status format matches what the GUI expects
        self.assertEqual(expected_status, "Cache: 2 entries")


if __name__ == '__main__':
    unittest.main()