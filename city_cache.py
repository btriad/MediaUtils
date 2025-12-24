"""
City Cache Manager for GPS coordinate caching.

This module provides persistent caching of GPS coordinates to city names
to reduce API calls and improve performance.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CacheEntry:
    """Represents a cached GPS coordinate to city mapping."""
    latitude: float
    longitude: float
    city: str
    timestamp: str  # ISO format string
    source: str = "api"  # API source used


class CityCache:
    """
    Manages persistent caching of GPS coordinates to city names.
    
    Features:
    - Persistent JSON storage
    - Size limit management (default 1000 entries)
    - Coordinate proximity matching for cache hits
    - Graceful error handling for corrupted cache files
    """
    
    def __init__(self, cache_file: str = "city_cache.json", max_entries: int = 1000):
        """
        Initialize the city cache.
        
        Args:
            cache_file: Path to the cache file
            max_entries: Maximum number of entries to keep in cache
        """
        self.cache_file = Path(cache_file)
        self.max_entries = max_entries
        self.cache: Dict[str, CacheEntry] = {}
        self._coordinate_tolerance = 0.001  # Degrees for proximity matching
        
    def _coordinate_key(self, lat: float, lon: float) -> str:
        """Generate a string key for coordinate pair."""
        return f"{lat:.6f},{lon:.6f}"
    
    def _is_coordinate_close(self, lat1: float, lon1: float, lat2: float, lon2: float) -> bool:
        """
        Check if two coordinates are within tolerance distance.
        
        Args:
            lat1, lon1: First coordinate pair
            lat2, lon2: Second coordinate pair
            
        Returns:
            True if coordinates are within tolerance
        """
        # Use a slightly larger tolerance to account for floating point precision
        tolerance = self._coordinate_tolerance + 1e-10
        return (abs(lat1 - lat2) <= tolerance and 
                abs(lon1 - lon2) <= tolerance)
    
    def get_city(self, lat: float, lon: float) -> Optional[str]:
        """
        Get cached city name for GPS coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Cached city name if found, None otherwise
        """
        # First try exact match
        key = self._coordinate_key(lat, lon)
        if key in self.cache:
            return self.cache[key].city
        
        # Try proximity matching
        for entry in self.cache.values():
            if self._is_coordinate_close(lat, lon, entry.latitude, entry.longitude):
                return entry.city
                
        return None
    
    def set_city(self, lat: float, lon: float, city: str, source: str = "api") -> None:
        """
        Cache a city name for GPS coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            city: City name to cache
            source: Source of the city information
        """
        key = self._coordinate_key(lat, lon)
        entry = CacheEntry(
            latitude=lat,
            longitude=lon,
            city=city,
            timestamp=datetime.now().isoformat(),
            source=source
        )
        
        self.cache[key] = entry
        
        # Cleanup if cache is too large
        if len(self.cache) > self.max_entries:
            self._cleanup_cache()
    
    def _cleanup_cache(self) -> None:
        """Remove oldest entries to maintain size limit."""
        if len(self.cache) <= self.max_entries:
            return
            
        # Sort by timestamp and keep only the most recent entries
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].timestamp,
            reverse=True
        )
        
        # Keep only max_entries
        self.cache = dict(sorted_entries[:self.max_entries])
    
    def load_cache(self) -> bool:
        """
        Load cache from file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not self.cache_file.exists():
                return True  # Empty cache is valid
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert dict entries back to CacheEntry objects
            self.cache = {}
            for key, entry_data in data.items():
                try:
                    entry = CacheEntry(**entry_data)
                    self.cache[key] = entry
                except (TypeError, ValueError):
                    # Skip invalid entries
                    continue
            
            return True
            
        except (json.JSONDecodeError, IOError, OSError) as e:
            # Handle corrupted cache file
            self._backup_corrupted_cache()
            self.cache = {}
            return False
    
    def save_cache(self) -> bool:
        """
        Save cache to file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert CacheEntry objects to dict for JSON serialization
            data = {}
            for key, entry in self.cache.items():
                data[key] = asdict(entry)
            
            # Write to temporary file first, then rename for atomic operation
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(self.cache_file)
            return True
            
        except (IOError, OSError):
            return False
    
    def _backup_corrupted_cache(self) -> None:
        """Backup corrupted cache file for debugging."""
        try:
            if self.cache_file.exists():
                backup_name = f"{self.cache_file.stem}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                backup_path = self.cache_file.parent / backup_name
                shutil.copy2(self.cache_file, backup_path)
        except (IOError, OSError):
            # If backup fails, just continue
            pass
    
    def is_coordinate_cached(self, lat: float, lon: float, tolerance: float = None) -> bool:
        """
        Check if coordinates are cached within tolerance.
        
        Args:
            lat: Latitude
            lon: Longitude
            tolerance: Custom tolerance (uses default if None)
            
        Returns:
            True if coordinates are cached within tolerance
        """
        if tolerance is not None:
            old_tolerance = self._coordinate_tolerance
            self._coordinate_tolerance = tolerance
            result = self.get_city(lat, lon) is not None
            self._coordinate_tolerance = old_tolerance
            return result
        
        return self.get_city(lat, lon) is not None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "total_entries": len(self.cache),
            "max_entries": self.max_entries,
            "cache_file": str(self.cache_file),
            "file_exists": self.cache_file.exists(),
            "coordinate_tolerance": self._coordinate_tolerance
        }
    
    def clear_cache(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()