#!/usr/bin/env python3
"""
Test to verify GUI cache management methods exist and are callable.
"""

import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def test_gui_cache_methods():
    """Test that GUI cache management methods exist."""
    print("Testing GUI cache management methods...")
    
    # Import the GUI class
    from gui_components import MediaRenamerGUI
    
    # Check that the required methods exist
    required_methods = [
        'load_city_cache',
        'save_city_cache', 
        'update_cache_status',
        'get_cache_statistics'
    ]
    
    for method_name in required_methods:
        if hasattr(MediaRenamerGUI, method_name):
            print(f"✅ Method '{method_name}' exists")
        else:
            print(f"❌ Method '{method_name}' missing")
            return False
    
    # Check that CityCache is imported
    try:
        from gui_components import CityCache
        print("✅ CityCache import successful")
    except ImportError:
        print("❌ CityCache import failed")
        return False
    
    print("\n✅ All GUI cache management methods are available!")
    return True


if __name__ == '__main__':
    success = test_gui_cache_methods()
    sys.exit(0 if success else 1)