"""
File Operations Module

Handles file system operations including:
- File discovery and filtering
- Batch file renaming
- Conflict resolution
- Progress tracking
"""

import os
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Callable, Optional, Set
from dataclasses import dataclass
from error_recovery import ErrorRecovery
from xmp_handler import XMPHandler


@dataclass
class FileInfo:
    """Data class to hold file information."""
    original_name: str
    original_path: str
    new_name: str
    final_name: str  # After duplicate/conflict resolution
    location: str
    city: str
    has_metadata: bool
    selected: bool = False


@dataclass
class OperationLog:
    """Data class to hold detailed operation log entry."""
    original_name: str
    final_name: str
    status: str  # 'success', 'error', 'skipped'
    error_message: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class ProcessResult:
    """Data class to hold processing results with detailed operation logs."""
    processed_count: int
    error_count: int
    errors: List[str]
    skipped_count: int
    operation_logs: List[OperationLog]


class FileOperations:
    """Handles file system operations for media renaming."""
    
    def __init__(self, supported_extensions: set, logger: Optional[logging.Logger] = None, logging_manager=None, error_recovery: Optional[ErrorRecovery] = None):
        """
        Initialize file operations handler.
        
        Args:
            supported_extensions: Set of supported file extensions
            logger: Optional logger instance for error tracking
            logging_manager: Optional logging manager for session logging
            error_recovery: Optional error recovery system instance
        """
        self.supported_extensions = supported_extensions
        self.duplicate_resolver = DuplicateResolver()
        self.conflict_resolver = ConflictResolver()
        self.logger = logger or logging.getLogger(__name__)
        self.logging_manager = logging_manager
        self.error_recovery = error_recovery or ErrorRecovery(logger=self.logger)
        self.xmp_handler = XMPHandler(logger=self.logger)
        
        # Log initialization
        self.logger.info(f"FileOperations initialized with {len(supported_extensions)} supported extensions")
    
    def discover_files(self, 
                      folder_path: str, 
                      progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[str]:
        """
        Discover all supported media files in a folder.
        
        Args:
            folder_path: Path to search for files
            progress_callback: Optional callback for progress updates (current, total, filename)
            
        Returns:
            List of file paths
        """
        self.logger.info(f"Starting file discovery in folder: {folder_path}")
        
        if not os.path.exists(folder_path):
            self.logger.error(f"Folder does not exist: {folder_path}")
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")
        
        try:
            # Get all files in directory
            all_files = [f for f in os.listdir(folder_path) 
                        if os.path.isfile(os.path.join(folder_path, f))]
            
            self.logger.info(f"Found {len(all_files)} total files in {folder_path}")
            
            # Filter supported media files
            media_files = []
            for i, filename in enumerate(all_files, 1):
                if progress_callback:
                    progress_callback(i, len(all_files), filename)
                
                ext = os.path.splitext(filename.lower())[1]
                if ext in self.supported_extensions:
                    media_files.append(os.path.join(folder_path, filename))
            
            self.logger.info(f"Discovered {len(media_files)} supported media files")
            return media_files
            
        except PermissionError as e:
            self.logger.error(f"Permission denied accessing folder: {folder_path}")
            # Use error recovery for permission errors
            recovery_result = self.error_recovery.handle_file_permission_error(folder_path, "read")
            raise PermissionError(f"Permission denied accessing folder: {folder_path}")
        except Exception as e:
            self.logger.error(f"Error discovering files in {folder_path}: {e}")
            # Use error recovery for other errors
            recovery_result = self.error_recovery.log_and_continue(e, "file discovery", folder_path)
            raise Exception(f"Error discovering files: {str(e)}")
    
    def check_filename_conflicts(self, 
                               folder_path: str, 
                               file_mappings: List[Tuple[str, str]]) -> Dict[str, List[str]]:
        """
        Check for filename conflicts in rename operations.
        
        Args:
            folder_path: Target folder path
            file_mappings: List of (current_name, new_name) tuples
            
        Returns:
            Dictionary of conflicts: {new_name: [list_of_current_names]}
        """
        conflicts = {}
        new_name_counts = {}
        
        # Check for duplicate new names
        for current_name, new_name in file_mappings:
            if new_name in ["No metadata", "Error"] or new_name.startswith("Error:"):
                continue
                
            if new_name in new_name_counts:
                new_name_counts[new_name].append(current_name)
            else:
                new_name_counts[new_name] = [current_name]
        
        # Identify conflicts
        for new_name, current_names in new_name_counts.items():
            if len(current_names) > 1:
                conflicts[new_name] = current_names
        
        # Check for existing files
        existing_conflicts = {}
        for current_name, new_name in file_mappings:
            if new_name in ["No metadata", "Error"] or new_name.startswith("Error:"):
                continue
                
            new_path = os.path.join(folder_path, new_name)
            if os.path.exists(new_path):
                if new_name not in existing_conflicts:
                    existing_conflicts[new_name] = []
                existing_conflicts[new_name].append(current_name)
        
        # Merge conflicts
        all_conflicts = {**conflicts, **existing_conflicts}
        return all_conflicts
    
    def resolve_duplicates_and_conflicts(self, 
                                       folder_path: str, 
                                       file_infos: List[FileInfo]) -> List[FileInfo]:
        """
        Resolve duplicate filenames and file conflicts for a list of FileInfo objects.
        
        Args:
            folder_path: Target folder path
            file_infos: List of FileInfo objects to process
            
        Returns:
            Updated list of FileInfo objects with resolved final_name field
        """
        # Create mappings for duplicate resolution
        file_mappings = [(info.original_name, info.new_name) for info in file_infos]
        
        # Resolve duplicates first
        resolved_mappings = self.duplicate_resolver.resolve_duplicates(file_mappings)
        
        # Create a mapping from original name to resolved name
        resolved_dict = dict(resolved_mappings)
        
        # Update FileInfo objects with resolved names and check for conflicts
        updated_file_infos = []
        for info in file_infos:
            # Create a copy of the FileInfo with resolved name
            updated_info = FileInfo(
                original_name=info.original_name,
                original_path=info.original_path,
                new_name=info.new_name,
                final_name=resolved_dict[info.original_name],
                location=info.location,
                city=info.city,
                has_metadata=info.has_metadata,
                selected=info.selected
            )
            
            # Check for conflicts with existing files (only for valid names)
            if (updated_info.final_name not in ["No metadata"] and 
                not updated_info.final_name.startswith("Error")):
                updated_info.final_name = self.conflict_resolver.resolve_file_conflicts(
                    folder_path, updated_info.final_name
                )
            
            updated_file_infos.append(updated_info)
        
        return updated_file_infos
    
    def process_files(self, 
                     folder_path: str, 
                     file_infos: List[FileInfo],
                     progress_callback: Optional[Callable[[int, int, str], None]] = None) -> ProcessResult:
        """
        Process selected files for renaming.
        
        Args:
            folder_path: Base folder path
            file_infos: List of FileInfo objects
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessResult with operation statistics and detailed logs
        """
        # Filter selected files
        selected_files = [f for f in file_infos if f.selected]
        
        self.logger.info(f"Starting file processing: {len(selected_files)} files selected for renaming")
        
        if not selected_files:
            self.logger.warning("No files selected for processing")
            return ProcessResult(0, 0, ["No files selected"], 0, [])
        
        # Log session start if logging manager is available
        if self.logging_manager:
            self.logging_manager.log_operation("session_start", {
                "total_files": len(selected_files),
                "folder_path": folder_path
            })
        
        processed_count = 0
        error_count = 0
        skipped_count = 0
        errors = []
        operation_logs = []
        
        for i, file_info in enumerate(selected_files, 1):
            if progress_callback:
                progress_callback(i, len(selected_files), file_info.original_name)
            
            self.logger.debug(f"Processing file {i}/{len(selected_files)}: {file_info.original_name}")
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                result = self._rename_single_file(folder_path, file_info)
                
                if result["success"]:
                    processed_count += 1
                    final_name = result.get('final_name', file_info.final_name)
                    self.logger.info(f"Successfully renamed: {file_info.original_name} -> {final_name}")
                    
                    # Log to session logger
                    if self.logging_manager:
                        self.logging_manager.log_operation("rename", {
                            "old_name": file_info.original_name,
                            "new_name": final_name,
                            "folder_path": folder_path
                        })
                    
                    # Create operation log entry for successful rename
                    operation_logs.append(OperationLog(
                        original_name=file_info.original_name,
                        final_name=final_name,
                        status='success',
                        error_message=None,
                        timestamp=timestamp
                    ))
                    
                elif result["skipped"]:
                    skipped_count += 1
                    self.logger.warning(f"Skipped file: {file_info.original_name} - {result['error']}")
                    if result["error"]:
                        errors.append(f"{file_info.original_name}: {result['error']}")
                    
                    # Log to session logger
                    if self.logging_manager:
                        self.logging_manager.log_operation("skip", {
                            "filename": file_info.original_name,
                            "reason": result['error'],
                            "folder_path": folder_path
                        })
                    
                    # Create operation log entry for skipped file
                    operation_logs.append(OperationLog(
                        original_name=file_info.original_name,
                        final_name=file_info.original_name,  # No change for skipped files
                        status='skipped',
                        error_message=result['error'],
                        timestamp=timestamp
                    ))
                    
                else:
                    error_count += 1
                    self.logger.error(f"Failed to rename: {file_info.original_name} - {result['error']}")
                    errors.append(f"{file_info.original_name}: {result['error']}")
                    
                    # Log to session logger
                    if self.logging_manager:
                        self.logging_manager.log_operation("error", {
                            "filename": file_info.original_name,
                            "error_message": result['error'],
                            "folder_path": folder_path
                        })
                    
                    # Create operation log entry for failed rename
                    operation_logs.append(OperationLog(
                        original_name=file_info.original_name,
                        final_name=file_info.original_name,  # No change for failed files
                        status='error',
                        error_message=result['error'],
                        timestamp=timestamp
                    ))
                    
            except Exception as e:
                error_count += 1
                error_msg = f"Unexpected error - {str(e)}"
                self.logger.error(f"Unexpected error processing {file_info.original_name}: {e}")
                errors.append(f"{file_info.original_name}: {error_msg}")
                
                # Log to session logger
                if self.logging_manager:
                    self.logging_manager.log_operation("error", {
                        "filename": file_info.original_name,
                        "error_message": error_msg,
                        "folder_path": folder_path
                    })
                
                # Create operation log entry for unexpected error
                operation_logs.append(OperationLog(
                    original_name=file_info.original_name,
                    final_name=file_info.original_name,  # No change for failed files
                    status='error',
                    error_message=error_msg,
                    timestamp=timestamp
                ))
        
        # Log session completion
        if self.logging_manager:
            self.logging_manager.log_operation("session_complete", {
                "processed_count": processed_count,
                "error_count": error_count,
                "skipped_count": skipped_count,
                "total_files": len(selected_files)
            })
        
        self.logger.info(f"File processing completed: {processed_count} processed, {error_count} errors, {skipped_count} skipped")
        return ProcessResult(processed_count, error_count, errors, skipped_count, operation_logs)
    
    def _rename_single_file(self, folder_path: str, file_info: FileInfo) -> Dict[str, any]:
        """
        Rename a single file with error handling and conflict re-checking.
        
        Args:
            folder_path: Base folder path
            file_info: FileInfo object with rename details
            
        Returns:
            Dictionary with operation result
        """
        current_path = os.path.join(folder_path, file_info.original_name)
        self.logger.debug(f"Attempting to rename: {current_path}")
        
        try:
            # Use final_name if available, otherwise fall back to new_name
            target_name = getattr(file_info, 'final_name', file_info.new_name)
            
            # Handle files with no metadata - add underscore prefix
            if target_name == "No metadata":
                if file_info.original_name.startswith('_'):
                    self.logger.debug(f"File already has underscore prefix: {file_info.original_name}")
                    return {
                        "success": False,
                        "skipped": True,
                        "error": "Already has underscore prefix"
                    }
                final_target_name = f"_{file_info.original_name}"
                new_path = os.path.join(folder_path, final_target_name)
                self.logger.debug(f"Adding underscore prefix: {new_path}")
            
            # Handle error cases
            elif target_name.startswith("Error:"):
                self.logger.debug(f"Skipping file with error: {target_name}")
                return {
                    "success": False,
                    "skipped": True,
                    "error": target_name
                }
            
            # Normal rename with conflict re-checking
            else:
                # Re-check for conflicts immediately before renaming (Requirement 3.5)
                # This handles cases where files may have been created between initial resolution and actual rename
                final_target_name = self.conflict_resolver.resolve_file_conflicts(folder_path, target_name)
                new_path = os.path.join(folder_path, final_target_name)
                self.logger.debug(f"Target path after conflict resolution: {new_path}")
            
            # Check if source file exists
            if not os.path.exists(current_path):
                self.logger.error(f"Source file not found: {current_path}")
                return {
                    "success": False,
                    "skipped": False,
                    "error": "Source file not found"
                }
            
            # Final safety check - this should not happen with proper conflict resolution
            if os.path.exists(new_path):
                self.logger.error(f"Target file already exists after conflict resolution: {new_path}")
                return {
                    "success": False,
                    "skipped": True,
                    "error": "Target file already exists after conflict resolution"
                }
            
            # Perform the rename
            self.logger.debug(f"Executing rename: {current_path} -> {new_path}")
            os.rename(current_path, new_path)
            self.logger.info(f"File renamed successfully: {file_info.original_name} -> {os.path.basename(new_path)}")
            
            # Rename XMP sidecar file if it exists
            try:
                xmp_renamed = self.xmp_handler.rename_xmp_with_image(current_path, new_path)
                if xmp_renamed:
                    self.logger.info(f"XMP sidecar renamed alongside image")
            except Exception as e:
                self.logger.warning(f"Failed to rename XMP sidecar: {e}")
                # Don't fail the whole operation if XMP rename fails
            
            return {
                "success": True,
                "skipped": False,
                "error": None,
                "final_name": final_target_name if 'final_target_name' in locals() else target_name
            }
            
        except PermissionError as e:
            self.logger.error(f"Permission denied renaming {current_path}: {e}")
            # Use error recovery for permission errors
            recovery_result = self.error_recovery.handle_file_permission_error(current_path, "rename")
            return {
                "success": False,
                "skipped": False,
                "error": "Permission denied"
            }
        except OSError as e:
            self.logger.error(f"File system error renaming {current_path}: {e}")
            # Use error recovery for file system errors
            recovery_result = self.error_recovery.log_and_continue(e, "file rename", current_path)
            return {
                "success": False,
                "skipped": False,
                "error": f"File system error: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Unexpected error renaming {current_path}: {e}")
            # Use error recovery for unexpected errors
            recovery_result = self.error_recovery.log_and_continue(e, "file rename", current_path)
            return {
                "success": False,
                "skipped": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def create_backup_list(self, 
                          folder_path: str, 
                          file_mappings: List[Tuple[str, str]]) -> bool:
        """
        Create a backup list of rename operations for undo functionality.
        
        Args:
            folder_path: Base folder path
            file_mappings: List of (old_name, new_name) tuples
            
        Returns:
            True if backup list created successfully
        """
        try:
            backup_file = os.path.join(folder_path, ".media_renamer_backup.txt")
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write("# Media Renamer Backup - Rename Operations\n")
                f.write("# Format: old_name -> new_name\n")
                f.write(f"# Created: {os.path.getctime}\n\n")
                
                for old_name, new_name in file_mappings:
                    f.write(f"{old_name} -> {new_name}\n")
            
            return True
            
        except Exception as e:
            print(f"Error creating backup list: {e}")
            return False
    
    def get_folder_stats(self, folder_path: str) -> Dict[str, int]:
        """
        Get statistics about files in a folder.
        
        Args:
            folder_path: Path to analyze
            
        Returns:
            Dictionary with file statistics
        """
        try:
            if not os.path.exists(folder_path):
                return {"total_files": 0, "media_files": 0, "other_files": 0}
            
            all_files = [f for f in os.listdir(folder_path) 
                        if os.path.isfile(os.path.join(folder_path, f))]
            
            media_files = 0
            for filename in all_files:
                ext = os.path.splitext(filename.lower())[1]
                if ext in self.supported_extensions:
                    media_files += 1
            
            return {
                "total_files": len(all_files),
                "media_files": media_files,
                "other_files": len(all_files) - media_files
            }
            
        except Exception as e:
            print(f"Error getting folder stats: {e}")
            return {"total_files": 0, "media_files": 0, "other_files": 0}


class DuplicateResolver:
    """Handles resolution of duplicate filenames with sequential numbering."""
    
    def resolve_duplicates(self, file_mappings: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Resolve duplicate filenames by adding sequential numbers.
        
        Args:
            file_mappings: List of (original_name, new_name) tuples
            
        Returns:
            List of (original_name, resolved_name) tuples with unique names
        """
        if not file_mappings:
            return []
        
        # Track name usage and resolve conflicts
        name_counts = {}
        resolved_mappings = []
        
        for original_name, new_name in file_mappings:
            # Skip files with no metadata or errors
            if new_name in ["No metadata"] or new_name.startswith("Error"):
                resolved_mappings.append((original_name, new_name))
                continue
            
            # Check if this name has been used before
            if new_name in name_counts:
                # Generate unique name with suffix
                name_counts[new_name] += 1
                unique_name = self._add_duplicate_suffix(new_name, name_counts[new_name])
            else:
                # First occurrence of this name
                name_counts[new_name] = 0
                unique_name = new_name
            
            resolved_mappings.append((original_name, unique_name))
        
        return resolved_mappings
    
    def generate_unique_name(self, base_name: str, existing_names: Set[str]) -> str:
        """
        Generate a unique name by adding suffix if needed.
        
        Args:
            base_name: Base filename to make unique
            existing_names: Set of names that already exist
            
        Returns:
            Unique filename
        """
        if base_name not in existing_names:
            return base_name
        
        # Find the next available number
        counter = 1
        while True:
            unique_name = self._add_duplicate_suffix(base_name, counter)
            if unique_name not in existing_names:
                return unique_name
            counter += 1
    
    def _add_duplicate_suffix(self, filename: str, number: int) -> str:
        """
        Add duplicate suffix to filename (e.g., _001, _002).
        
        Args:
            filename: Original filename
            number: Number to append
            
        Returns:
            Filename with suffix
        """
        name, ext = os.path.splitext(filename)
        return f"{name}_{number:03d}{ext}"


class ConflictResolver:
    """Handles resolution of file conflicts with existing files."""
    
    def resolve_file_conflicts(self, folder_path: str, target_name: str) -> str:
        """
        Resolve conflicts with existing files by adding conflict suffix.
        
        Args:
            folder_path: Target directory path
            target_name: Desired filename
            
        Returns:
            Available filename (may have conflict suffix)
        """
        target_path = os.path.join(folder_path, target_name)
        
        # If no conflict, return original name
        if not os.path.exists(target_path):
            return target_name
        
        # Find available name with conflict suffix
        return self.find_available_name(folder_path, target_name)
    
    def find_available_name(self, folder_path: str, base_name: str) -> str:
        """
        Find an available filename by adding conflict suffixes (_c1, _c2, etc.).
        
        Args:
            folder_path: Target directory path
            base_name: Base filename
            
        Returns:
            Available filename
        """
        name, ext = os.path.splitext(base_name)
        counter = 1
        
        while True:
            conflict_name = f"{name}_c{counter}{ext}"
            conflict_path = os.path.join(folder_path, conflict_name)
            
            if not os.path.exists(conflict_path):
                return conflict_name
            
            counter += 1