#!/usr/bin/env python3
"""
Integration test for cache management functionality.

This script tests the cache loading and saving functionality
without the full GUI initialization.
"""

import os
import tempfile
import unittest
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from city_cache import CityCache
from media_processor import MediaProcessor


class TestCacheIntegration(unittest.TestCase):
    """Test cases for cache integration with MediaProcessor."""
    
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
    
    def test_cache_loading_and_saving(self):
        """Test that cache can be loaded and saved properly."""
        # Create a new cache instance and load from file
        cache = CityCache(cache_file=self.cache_file, max_entries=10)
        
        # Load cache
        load_success = cache.load_cache()
        self.assertTrue(load_success, "Cache should load successfully")
        
        # Verify loaded data
        self.assertEqual(cache.get_city(40.7128, -74.0060), "New York")
        self.assertEqual(cache.get_city(51.5074, -0.1278), "London")
        
        # Add new data
        cache.set_city(48.8566, 2.3522, "Paris")
        
        # Save cache
        save_success = cache.save_cache()
        self.assertTrue(save_success, "Cache should save successfully")
        
        # Create another instance and verify the new data was saved
        cache2 = CityCache(cache_file=self.cache_file, max_entries=10)
        cache2.load_cache()
        self.assertEqual(cache2.get_city(48.8566, 2.3522), "Paris")
    
    def test_media_processor_cache_integration(self):
        """Test that MediaProcessor properly uses the cache."""
        # Create cache with test data
        cache = CityCache(cache_file=self.cache_file, max_entries=10)
        cache.load_cache()
        
        # Create MediaProcessor with the cache
        processor = MediaProcessor(city_cache=cache)
        
        # Verify cache statistics
        stats = processor.get_cache_stats()
        self.assertIn('total_entries', stats)
        self.assertEqual(stats['total_entries'], 2)  # New York and London
        
        # Test cache save through MediaProcessor
        save_success = processor.save_cache()
        self.assertTrue(save_success, "MediaProcessor should save cache successfully")
        
        # Test cache load through MediaProcessor
        load_success = processor.load_cache()
        self.assertTrue(load_success, "MediaProcessor should load cache successfully")
    
    def test_cache_statistics_format(self):
        """Test that cache statistics are properly formatted."""
        cache = CityCache(cache_file=self.cache_file, max_entries=10)
        cache.load_cache()
        
        stats = cache.get_cache_stats()
        
        # Verify all required statistics are present
        required_keys = ['total_entries', 'max_entries', 'cache_file', 'file_exists', 'coordinate_tolerance']
        for key in required_keys:
            self.assertIn(key, stats, f"Statistics should include {key}")
        
        # Verify values
        self.assertEqual(stats['total_entries'], 2)
        self.assertEqual(stats['max_entries'], 10)
        self.assertTrue(stats['file_exists'])
        self.assertEqual(stats['coordinate_tolerance'], 0.001)
    
    def test_cache_startup_shutdown_simulation(self):
        """Test simulated application startup and shutdown cache operations."""
        # Simulate application startup
        startup_cache = CityCache(cache_file=self.cache_file, max_entries=1000)
        startup_success = startup_cache.load_cache()
        self.assertTrue(startup_success, "Startup cache load should succeed")
        
        # Verify initial data is loaded
        self.assertEqual(startup_cache.get_city(40.7128, -74.0060), "New York")
        
        # Simulate some operations during application runtime
        startup_cache.set_city(35.6762, 139.6503, "Tokyo")
        startup_cache.set_city(-33.8688, 151.2093, "Sydney")
        
        # Simulate application shutdown
        shutdown_success = startup_cache.save_cache()
        self.assertTrue(shutdown_success, "Shutdown cache save should succeed")
        
        # Verify data persists after shutdown by loading in new instance
        verification_cache = CityCache(cache_file=self.cache_file, max_entries=1000)
        verification_cache.load_cache()
        
        # Check all data is present
        self.assertEqual(verification_cache.get_city(40.7128, -74.0060), "New York")
        self.assertEqual(verification_cache.get_city(51.5074, -0.1278), "London")
        self.assertEqual(verification_cache.get_city(35.6762, 139.6503), "Tokyo")
        self.assertEqual(verification_cache.get_city(-33.8688, 151.2093), "Sydney")
        
        # Verify statistics
        stats = verification_cache.get_cache_stats()
        self.assertEqual(stats['total_entries'], 4)


if __name__ == '__main__':
    unittest.main()