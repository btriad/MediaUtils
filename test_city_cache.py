"""
Unit tests for city cache management system.

Tests cache hit/miss scenarios, size limits, cleanup, and coordinate proximity matching.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from city_cache import CityCache, CacheEntry


class TestCityCache(unittest.TestCase):
    """Test cases for CityCache functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create temporary file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "test_cache.json")
        self.cache = CityCache(cache_file=self.cache_file, max_entries=5)
    
    def tearDown(self):
        """Clean up after each test method."""
        # Remove temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cache_hit_scenarios(self):
        """Test cache hit scenarios - Requirement 2.1."""
        # Test exact coordinate match
        lat, lon = 40.7128, -74.0060  # New York coordinates
        city = "New York"
        
        # Initially should be cache miss
        self.assertIsNone(self.cache.get_city(lat, lon))
        
        # Add to cache
        self.cache.set_city(lat, lon, city)
        
        # Should now be cache hit
        self.assertEqual(self.cache.get_city(lat, lon), city)
    
    def test_cache_miss_scenarios(self):
        """Test cache miss scenarios - Requirement 2.1."""
        # Test with empty cache
        self.assertIsNone(self.cache.get_city(40.7128, -74.0060))
        
        # Add one entry
        self.cache.set_city(40.7128, -74.0060, "New York")
        
        # Test miss with different coordinates
        self.assertIsNone(self.cache.get_city(34.0522, -118.2437))  # Los Angeles
    
    def test_coordinate_proximity_matching(self):
        """Test coordinate proximity matching - Requirement 9.4."""
        # Add entry to cache
        base_lat, base_lon = 40.7128, -74.0060
        self.cache.set_city(base_lat, base_lon, "New York")
        
        # Test coordinates within tolerance (0.001 degrees)
        close_lat = base_lat + 0.0005  # Within tolerance
        close_lon = base_lon + 0.0005
        self.assertEqual(self.cache.get_city(close_lat, close_lon), "New York")
        
        # Test coordinates at exact tolerance boundary
        boundary_lat = base_lat + 0.001
        boundary_lon = base_lon + 0.001
        self.assertEqual(self.cache.get_city(boundary_lat, boundary_lon), "New York")
        
        # Test coordinates outside tolerance
        far_lat = base_lat + 0.002  # Outside tolerance
        far_lon = base_lon + 0.002
        self.assertIsNone(self.cache.get_city(far_lat, far_lon))
    
    def test_cache_size_limits(self):
        """Test cache size limits - Requirement 9.1."""
        import time
        
        # Fill cache to max capacity (5 entries)
        cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
        coordinates = [
            (40.7128, -74.0060),
            (34.0522, -118.2437),
            (41.8781, -87.6298),
            (29.7604, -95.3698),
            (33.4484, -112.0740)
        ]
        
        for i, (lat, lon) in enumerate(coordinates):
            self.cache.set_city(lat, lon, cities[i])
            time.sleep(0.01)  # Ensure different timestamps
        
        # Verify all entries are present
        self.assertEqual(len(self.cache.cache), 5)
        
        # Add one more entry to trigger cleanup
        time.sleep(0.01)  # Ensure Miami has newest timestamp
        self.cache.set_city(25.7617, -80.1918, "Miami")  # 6th entry
        
        # Should still have max_entries (5)
        self.assertEqual(len(self.cache.cache), 5)
        
        # Miami should be present (newest)
        self.assertEqual(self.cache.get_city(25.7617, -80.1918), "Miami")
    
    def test_cache_cleanup_removes_oldest(self):
        """Test that cache cleanup removes oldest entries - Requirement 9.1."""
        # Add entries with different timestamps
        import time
        
        # Add first entry
        self.cache.set_city(40.7128, -74.0060, "New York")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Add more entries to fill cache
        coordinates = [
            (34.0522, -118.2437, "Los Angeles"),
            (41.8781, -87.6298, "Chicago"),
            (29.7604, -95.3698, "Houston"),
            (33.4484, -112.0740, "Phoenix")
        ]
        
        for lat, lon, city in coordinates:
            self.cache.set_city(lat, lon, city)
            time.sleep(0.01)
        
        # Cache should be at capacity (5 entries)
        self.assertEqual(len(self.cache.cache), 5)
        
        # Add one more to trigger cleanup
        self.cache.set_city(25.7617, -80.1918, "Miami")
        
        # New York (oldest) should be removed
        self.assertIsNone(self.cache.get_city(40.7128, -74.0060))
        
        # Miami (newest) should be present
        self.assertEqual(self.cache.get_city(25.7617, -80.1918), "Miami")
    
    def test_cache_persistence_save_load(self):
        """Test cache persistence through save and load operations."""
        # Add entries to cache
        self.cache.set_city(40.7128, -74.0060, "New York")
        self.cache.set_city(34.0522, -118.2437, "Los Angeles")
        
        # Save cache
        self.assertTrue(self.cache.save_cache())
        self.assertTrue(os.path.exists(self.cache_file))
        
        # Create new cache instance and load
        new_cache = CityCache(cache_file=self.cache_file, max_entries=5)
        self.assertTrue(new_cache.load_cache())
        
        # Verify data was loaded correctly
        self.assertEqual(new_cache.get_city(40.7128, -74.0060), "New York")
        self.assertEqual(new_cache.get_city(34.0522, -118.2437), "Los Angeles")
    
    def test_corrupted_cache_handling(self):
        """Test handling of corrupted cache files."""
        # Create corrupted JSON file
        with open(self.cache_file, 'w') as f:
            f.write("invalid json content {")
        
        # Loading should handle corruption gracefully
        self.assertFalse(self.cache.load_cache())
        
        # Cache should be empty after failed load
        self.assertEqual(len(self.cache.cache), 0)
        
        # Should still be able to add new entries
        self.cache.set_city(40.7128, -74.0060, "New York")
        self.assertEqual(self.cache.get_city(40.7128, -74.0060), "New York")
    
    def test_missing_cache_file_handling(self):
        """Test handling when cache file doesn't exist."""
        # Remove cache file if it exists
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        
        # Loading non-existent file should succeed (empty cache)
        self.assertTrue(self.cache.load_cache())
        self.assertEqual(len(self.cache.cache), 0)
    
    def test_is_coordinate_cached_method(self):
        """Test the is_coordinate_cached method."""
        lat, lon = 40.7128, -74.0060
        
        # Initially not cached
        self.assertFalse(self.cache.is_coordinate_cached(lat, lon))
        
        # Add to cache
        self.cache.set_city(lat, lon, "New York")
        
        # Should now be cached
        self.assertTrue(self.cache.is_coordinate_cached(lat, lon))
        
        # Test with custom tolerance
        close_lat, close_lon = lat + 0.0005, lon + 0.0005
        self.assertTrue(self.cache.is_coordinate_cached(close_lat, close_lon, tolerance=0.001))
        self.assertFalse(self.cache.is_coordinate_cached(close_lat, close_lon, tolerance=0.0001))
    
    def test_cache_stats(self):
        """Test cache statistics functionality."""
        # Get initial stats
        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["total_entries"], 0)
        self.assertEqual(stats["max_entries"], 5)
        self.assertFalse(stats["file_exists"])
        
        # Add entries and check stats
        self.cache.set_city(40.7128, -74.0060, "New York")
        self.cache.set_city(34.0522, -118.2437, "Los Angeles")
        
        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["total_entries"], 2)
        
        # Save and check file existence
        self.cache.save_cache()
        stats = self.cache.get_cache_stats()
        self.assertTrue(stats["file_exists"])
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add entries
        self.cache.set_city(40.7128, -74.0060, "New York")
        self.cache.set_city(34.0522, -118.2437, "Los Angeles")
        self.assertEqual(len(self.cache.cache), 2)
        
        # Clear cache
        self.cache.clear_cache()
        self.assertEqual(len(self.cache.cache), 0)
        
        # Verify entries are gone
        self.assertIsNone(self.cache.get_city(40.7128, -74.0060))
        self.assertIsNone(self.cache.get_city(34.0522, -118.2437))
    
    def test_cache_entry_with_source(self):
        """Test cache entries include source information."""
        lat, lon = 40.7128, -74.0060
        city = "New York"
        source = "test_api"
        
        # Add entry with custom source
        self.cache.set_city(lat, lon, city, source)
        
        # Verify entry has correct source
        key = self.cache._coordinate_key(lat, lon)
        entry = self.cache.cache[key]
        self.assertEqual(entry.source, source)
        self.assertEqual(entry.city, city)
        self.assertEqual(entry.latitude, lat)
        self.assertEqual(entry.longitude, lon)


if __name__ == '__main__':
    unittest.main()