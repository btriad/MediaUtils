"""
Settings Management Module

Handles loading, saving, and validation of application settings.
Provides default configurations and settings persistence.
"""

import json
import os
import re
import shutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of settings validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class SettingsValidator:
    """Handles validation of individual settings and comprehensive validation."""
    
    # Invalid filename characters for Windows/cross-platform compatibility
    INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]'
    
    # Required placeholders for filename formats
    REQUIRED_PLACEHOLDERS = ['{ext}']
    
    # At least one date component should be present
    DATE_PATTERNS = [r'%Y', r'%y', r'%m', r'%d', r'%H', r'%M', r'%S']
    
    @staticmethod
    def validate_string_type(value: Any, allow_empty: bool = True) -> bool:
        """Validate that value is a string."""
        if not isinstance(value, str):
            return False
        return allow_empty or len(value.strip()) > 0
    
    @staticmethod
    def validate_boolean_type(value: Any) -> bool:
        """Validate that value is a boolean."""
        return isinstance(value, bool)
    
    @staticmethod
    def validate_integer_type(value: Any, min_val: int = None, max_val: int = None) -> bool:
        """Validate that value is an integer within optional range."""
        if not isinstance(value, int):
            return False
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True
    
    @staticmethod
    def validate_list_type(value: Any, element_type: type = None) -> bool:
        """Validate that value is a list with optional element type checking."""
        if not isinstance(value, list):
            return False
        if element_type is not None:
            return all(isinstance(item, element_type) for item in value)
        return True
    
    @staticmethod
    def validate_folder_path(path: Any) -> bool:
        """Validate that path exists and is a directory."""
        if not isinstance(path, str):
            return False
        if not path.strip():
            return False
        try:
            return os.path.exists(path) and os.path.isdir(path)
        except (OSError, TypeError):
            return False
    
    @staticmethod
    def validate_filename_format(format_str: Any) -> bool:
        """Validate filename format pattern."""
        if not isinstance(format_str, str):
            return False
        if not format_str.strip():
            return False
        
        # Check for required placeholders
        for placeholder in SettingsValidator.REQUIRED_PLACEHOLDERS:
            if placeholder not in format_str:
                return False
        
        # Check for at least one date component
        has_date_component = any(pattern in format_str for pattern in SettingsValidator.DATE_PATTERNS)
        if not has_date_component:
            return False
        
        # Check for invalid filename characters
        # Remove strftime patterns and placeholders first
        temp_str = re.sub(r'%[a-zA-Z]', '', format_str)  # Remove %Y, %m, etc.
        temp_str = re.sub(r'\{[^}]+\}', '', temp_str)    # Remove {ext}, {increment:03d}, etc.
        
        if re.search(SettingsValidator.INVALID_FILENAME_CHARS, temp_str):
            return False
        
        return True
    
    @staticmethod
    def validate_window_geometry(geometry: Any) -> bool:
        """Validate window geometry string (e.g., '800x600' or '800x600+100+50')."""
        if not isinstance(geometry, str):
            return False
        if not geometry.strip():
            return False
        
        # Pattern for geometry: WIDTHxHEIGHT[+X+Y]
        pattern = r'^(\d+)x(\d+)(\+\d+\+\d+)?$'
        match = re.match(pattern, geometry)
        
        if not match:
            return False
        
        width, height = int(match.group(1)), int(match.group(2))
        return width > 0 and height > 0


class SettingsManager:
    """Manages application settings with persistence and validation."""
    
    # Default application settings
    DEFAULT_SETTINGS = {
        "folder_path": "c:\\",
        "filename_format": "%Y.%m.%d-%H.%M.%S.{increment:03d}.{city}.{ext}",
        "window_geometry": "1200x600",
        "last_used_formats": [
            "%Y.%m.%d-%H.%M.%S.{increment:03d}.{city}.{ext}",
            "%Y-%m-%d_%H-%M-%S.{increment:03d}.{ext}",
            "{city}_%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}"
        ],
        "auto_select_all": False,
        "show_missing_metadata_warning": True,
        "api_timeout": 5,
        "max_city_cache_size": 1000
    }
    
    def __init__(self, settings_file: str = "settings.json"):
        """
        Initialize settings manager.
        
        Args:
            settings_file: Path to settings file
        """
        self.settings_file = settings_file
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load_settings()
    
    def load_settings(self) -> bool:
        """
        Load settings from file with validation and recovery.
        
        Returns:
            True if settings loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # Use lenient repair for loading (preserves non-existent paths)
                repaired_settings = self._repair_settings_for_loading(loaded_settings)
                self.settings.update(repaired_settings)
                
                # Save repaired settings if any repairs were made
                if repaired_settings != loaded_settings:
                    self.save_settings()
                
                return True
            else:
                # Create default settings file
                self.save_settings()
                return True
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading settings: {e}")
            # Backup corrupted file and use defaults
            self._backup_corrupted_settings()
            self.settings = self.DEFAULT_SETTINGS.copy()
            self.save_settings()
            return False
    
    def save_settings(self) -> bool:
        """
        Save current settings to file.
        
        Returns:
            True if settings saved successfully, False otherwise
        """
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value by key.
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set setting value by key.
        
        Args:
            key: Setting key
            value: Setting value
        """
        self.settings[key] = value
    
    def update(self, new_settings: Dict[str, Any]) -> None:
        """
        Update multiple settings at once.
        
        Args:
            new_settings: Dictionary of settings to update
        """
        self.settings.update(new_settings)
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self.settings = self.DEFAULT_SETTINGS.copy()
    
    def _merge_settings(self, loaded_settings: Dict[str, Any]) -> None:
        """
        Merge loaded settings with defaults, validating types.
        
        Args:
            loaded_settings: Settings loaded from file
        """
        for key, value in loaded_settings.items():
            if key in self.DEFAULT_SETTINGS:
                # Type validation - ensure loaded value matches default type
                default_type = type(self.DEFAULT_SETTINGS[key])
                if isinstance(value, default_type):
                    self.settings[key] = value
                else:
                    print(f"Warning: Invalid type for setting '{key}', using default")
            else:
                # Allow new settings not in defaults
                self.settings[key] = value
    
    def validate_folder_path(self, path: str) -> bool:
        """
        Validate if folder path exists and is accessible.
        
        Args:
            path: Folder path to validate
            
        Returns:
            True if path is valid, False otherwise
        """
        try:
            return os.path.exists(path) and os.path.isdir(path)
        except Exception:
            return False
    
    def add_recent_format(self, format_pattern: str) -> None:
        """
        Add format pattern to recent formats list.
        
        Args:
            format_pattern: Format pattern to add
        """
        recent_formats = self.settings.get("last_used_formats", [])
        
        # Remove if already exists
        if format_pattern in recent_formats:
            recent_formats.remove(format_pattern)
        
        # Add to beginning
        recent_formats.insert(0, format_pattern)
        
        # Keep only last 10 formats
        self.settings["last_used_formats"] = recent_formats[:10]
    
    def get_recent_formats(self) -> list:
        """
        Get list of recently used format patterns.
        
        Returns:
            List of recent format patterns
        """
        return self.settings.get("last_used_formats", [])
    
    def export_settings(self, export_path: str) -> bool:
        """
        Export settings to a different file.
        
        Args:
            export_path: Path to export settings to
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, import_path: str) -> bool:
        """
        Import settings from a file.
        
        Args:
            import_path: Path to import settings from
            
        Returns:
            True if import successful, False otherwise
        """
        try:
            if not os.path.exists(import_path):
                return False
                
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # Validate and repair imported settings
            repaired_settings = self.repair_corrupted_settings(imported_settings)
            self.settings.update(repaired_settings)
            return True
            
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
    
    def validate_setting(self, key: str, value: Any) -> bool:
        """
        Validate a single setting value.
        
        Args:
            key: Setting key
            value: Setting value to validate
            
        Returns:
            True if setting is valid, False otherwise
        """
        if key not in self.DEFAULT_SETTINGS:
            return True  # Allow unknown settings
        
        default_value = self.DEFAULT_SETTINGS[key]
        
        # Type-specific validation
        if key == "folder_path":
            # For folder_path, we validate type but not existence during setting validation
            # Existence validation is separate
            return SettingsValidator.validate_string_type(value, allow_empty=False)
        elif key == "filename_format":
            return SettingsValidator.validate_filename_format(value)
        elif key == "window_geometry":
            return SettingsValidator.validate_window_geometry(value)
        elif key == "last_used_formats":
            return SettingsValidator.validate_list_type(value, str) and \
                   all(SettingsValidator.validate_filename_format(fmt) for fmt in value)
        elif key in ["auto_select_all", "show_missing_metadata_warning"]:
            return SettingsValidator.validate_boolean_type(value)
        elif key in ["api_timeout", "max_city_cache_size"]:
            return SettingsValidator.validate_integer_type(value, min_val=1)
        elif isinstance(default_value, str):
            return SettingsValidator.validate_string_type(value, allow_empty=False)
        elif isinstance(default_value, bool):
            return SettingsValidator.validate_boolean_type(value)
        elif isinstance(default_value, int):
            return SettingsValidator.validate_integer_type(value)
        elif isinstance(default_value, list):
            return SettingsValidator.validate_list_type(value)
        
        return True
    
    def validate_folder_path(self, path: str) -> bool:
        """
        Validate if folder path exists and is accessible.
        
        Args:
            path: Folder path to validate
            
        Returns:
            True if path is valid, False otherwise
        """
        return SettingsValidator.validate_folder_path(path)
    
    def validate_filename_format(self, format_str: str) -> bool:
        """
        Validate filename format pattern.
        
        Args:
            format_str: Format string to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        return SettingsValidator.validate_filename_format(format_str)
    
    def validate_window_geometry(self, geometry: str) -> bool:
        """
        Validate window geometry string.
        
        Args:
            geometry: Geometry string to validate
            
        Returns:
            True if geometry is valid, False otherwise
        """
        return SettingsValidator.validate_window_geometry(geometry)
    
    def validate_all_settings(self, settings: Dict[str, Any]) -> ValidationResult:
        """
        Validate all settings comprehensively.
        
        Args:
            settings: Dictionary of settings to validate
            
        Returns:
            ValidationResult with validation status and error details
        """
        errors = []
        warnings = []
        
        for key, value in settings.items():
            if not self.validate_setting(key, value):
                if key in self.DEFAULT_SETTINGS:
                    errors.append(f"Invalid value for '{key}': {value}")
                else:
                    warnings.append(f"Unknown setting '{key}' will be ignored")
        
        # Check for missing required settings
        for key in self.DEFAULT_SETTINGS:
            if key not in settings:
                warnings.append(f"Missing setting '{key}', will use default")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def repair_corrupted_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Repair corrupted settings by replacing invalid values with defaults.
        
        Args:
            settings: Settings dictionary to repair
            
        Returns:
            Repaired settings dictionary
        """
        repaired = self.DEFAULT_SETTINGS.copy()
        
        for key, value in settings.items():
            # Special handling for folder_path - check existence during repair
            if key == "folder_path":
                if SettingsValidator.validate_string_type(value, allow_empty=False) and \
                   SettingsValidator.validate_folder_path(value):
                    repaired[key] = value
                elif key in self.DEFAULT_SETTINGS:
                    print(f"Warning: Invalid value for setting '{key}', using default")
                    # Keep default value
                else:
                    repaired[key] = value
            elif self.validate_setting(key, value):
                repaired[key] = value
            elif key in self.DEFAULT_SETTINGS:
                print(f"Warning: Invalid value for setting '{key}', using default")
                # Keep default value
            else:
                # Unknown setting, keep it but warn
                print(f"Warning: Unknown setting '{key}', keeping as-is")
                repaired[key] = value
        
        return repaired
    
    def _repair_settings_for_loading(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Repair settings for loading - more lenient, preserves non-existent paths.
        
        Args:
            settings: Settings dictionary to repair
            
        Returns:
            Repaired settings dictionary
        """
        repaired = self.DEFAULT_SETTINGS.copy()
        
        for key, value in settings.items():
            if self.validate_setting(key, value):
                repaired[key] = value
            elif key in self.DEFAULT_SETTINGS:
                print(f"Warning: Invalid value for setting '{key}', using default")
                # Keep default value
            else:
                # Unknown setting, keep it but warn
                print(f"Warning: Unknown setting '{key}', keeping as-is")
                repaired[key] = value
        
        return repaired
    
    def _backup_corrupted_settings(self) -> None:
        """Create a backup of corrupted settings file."""
        try:
            if os.path.exists(self.settings_file):
                backup_path = self.settings_file + ".corrupted.backup"
                shutil.copy2(self.settings_file, backup_path)
                print(f"Corrupted settings backed up to: {backup_path}")
        except Exception as e:
            print(f"Failed to backup corrupted settings: {e}")