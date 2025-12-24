#!/usr/bin/env python3
"""
Manual test for GUI cache management functionality.

This script creates a simple test to verify cache management
works in the actual GUI application.
"""

import os
import tempfile
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from city_cache import CityCache


def test_cache_functionality():
    """Test cache functionality that will be used by the GUI."""
    print("Testing cache management functionality...")
    
    # Create temporary cache file
    temp_dir = tempfile.mkdtemp()
    cache_file = os.path.join(temp_dir, "test_cache.json")
    
    print(f"Using cache file: {cache_file}")
    
    # Test 1: Create cache and add some data (simulating startup)
    print("\n1. Testing cache creation and data addition...")
    cache = CityCache(cache_file=cache_file, max_entries=1000)
    
    # Add some test data
    cache.set_city(40.7128, -74.0060, "New York")
    cache.set_city(51.5074, -0.1278, "London")
    cache.set_city(48.8566, 2.3522, "Paris")
    
    # Get statistics
    stats = cache.get_cache_stats()
    print(f"Cache statistics: {stats}")
    
    # Test 2: Save cache (simulating shutdown)
    print("\n2. Testing cache save...")
    save_success = cache.save_cache()
    print(f"Cache save successful: {save_success}")
    
    # Test 3: Load cache in new instance (simulating startup)
    print("\n3. Testing cache load...")
    new_cache = CityCache(cache_file=cache_file, max_entries=1000)
    load_success = new_cache.load_cache()
    print(f"Cache load successful: {load_success}")
    
    # Verify data
    print("\n4. Verifying loaded data...")
    cities = [
        (40.7128, -74.0060, "New York"),
        (51.5074, -0.1278, "London"),
        (48.8566, 2.3522, "Paris")
    ]
    
    for lat, lon, expected_city in cities:
        actual_city = new_cache.get_city(lat, lon)
        print(f"  {lat}, {lon} -> {actual_city} (expected: {expected_city})")
        assert actual_city == expected_city, f"Expected {expected_city}, got {actual_city}"
    
    # Test 5: Cache statistics format
    print("\n5. Testing cache statistics format...")
    stats = new_cache.get_cache_stats()
    status_text = f"Cache: {stats['total_entries']} entries"
    print(f"Status text format: '{status_text}'")
    
    # Test 6: Test proximity matching
    print("\n6. Testing proximity matching...")
    # Test coordinates very close to New York
    close_city = new_cache.get_city(40.7129, -74.0061)  # Very close to NYC
    print(f"Proximity match result: {close_city}")
    assert close_city == "New York", f"Expected proximity match to return New York, got {close_city}"
    
    print("\n✅ All cache functionality tests passed!")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("Cleanup completed.")


if __name__ == '__main__':
    test_cache_functionality()