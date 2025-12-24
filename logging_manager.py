"""
Logging Manager for Media File Renamer Application

Provides comprehensive logging capabilities including:
- Application logging with rotation
- Session logging for file operations
- Different severity levels
- Log file management
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import json


class LoggingManager:
    """Manages application and session logging with rotation and file management."""
    
    def __init__(self, logs_dir: str = "logs"):
        """
        Initialize the logging manager.
        
        Args:
            logs_dir: Directory to store log files
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        self.app_logger: Optional[logging.Logger] = None
        self.session_logger: Optional[logging.Logger] = None
        self.session_entries: List[Dict[str, Any]] = []
        self.session_start_time: Optional[datetime] = None
        
    def setup_application_logger(self, log_level: str = "INFO") -> logging.Logger:
        """
        Set up the main application logger with rotation.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            
        Returns:
            Configured logger instance
        """
        try:
            # Create logger
            self.app_logger = logging.getLogger("media_renamer_app")
            self.app_logger.setLevel(getattr(logging, log_level.upper()))
            
            # Clear any existing handlers
            self.app_logger.handlers.clear()
            
            # Create log filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = self.logs_dir / f"app_{timestamp}.log"
            
            # Create rotating file handler (10MB max, keep 5 files)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            
            # Create console handler for immediate feedback
            console_handler = logging.StreamHandler()
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Add handlers to logger
            self.app_logger.addHandler(file_handler)
            self.app_logger.addHandler(console_handler)
            
            # Log successful setup
            self.app_logger.info(f"Application logging initialized - Log file: {log_file}")
            
            return self.app_logger
            
        except Exception as e:
            # Fallback to basic logging if setup fails
            print(f"Warning: Failed to setup application logger: {e}")
            print("Falling back to basic console logging")
            
            basic_logger = logging.getLogger("media_renamer_app_fallback")
            basic_logger.setLevel(logging.INFO)
            
            if not basic_logger.handlers:
                console_handler = logging.StreamHandler()
                formatter = logging.Formatter('%(levelname)s - %(message)s')
                console_handler.setFormatter(formatter)
                basic_logger.addHandler(console_handler)
            
            return basic_logger
    
    def setup_session_logger(self) -> logging.Logger:
        """
        Set up session logger for tracking file operations.
        
        Returns:
            Configured session logger instance
        """
        try:
            self.session_logger = logging.getLogger("media_renamer_session")
            self.session_logger.setLevel(logging.INFO)
            
            # Clear any existing handlers
            self.session_logger.handlers.clear()
            
            # Initialize session tracking
            self.session_start_time = datetime.now()
            self.session_entries.clear()
            
            # Create session log filename
            timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
            session_log_file = self.logs_dir / f"session_{timestamp}.log"
            
            # Create file handler for session
            file_handler = logging.FileHandler(session_log_file, encoding='utf-8')
            
            # Create formatter for session logs
            formatter = logging.Formatter(
                '%(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            self.session_logger.addHandler(file_handler)
            
            # Log session start
            self.session_logger.info("=== File Processing Session Started ===")
            
            if self.app_logger:
                self.app_logger.info(f"Session logging initialized - Session file: {session_log_file}")
            
            return self.session_logger
            
        except Exception as e:
            if self.app_logger:
                self.app_logger.error(f"Failed to setup session logger: {e}")
            else:
                print(f"Error: Failed to setup session logger: {e}")
            
            # Return a dummy logger that doesn't fail
            dummy_logger = logging.getLogger("dummy_session")
            dummy_logger.addHandler(logging.NullHandler())
            return dummy_logger
    
    def log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """
        Log a file operation with details.
        
        Args:
            operation: Type of operation (rename, skip, error, etc.)
            details: Dictionary containing operation details
        """
        try:
            # Create log entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                **details
            }
            
            # Add to session entries
            self.session_entries.append(entry)
            
            # Log to session logger
            if self.session_logger:
                if operation == "rename":
                    self.session_logger.info(
                        f"RENAMED: '{details.get('old_name', 'unknown')}' -> "
                        f"'{details.get('new_name', 'unknown')}'"
                    )
                elif operation == "skip":
                    self.session_logger.info(
                        f"SKIPPED: '{details.get('filename', 'unknown')}' - "
                        f"Reason: {details.get('reason', 'unknown')}"
                    )
                elif operation == "error":
                    self.session_logger.error(
                        f"ERROR: '{details.get('filename', 'unknown')}' - "
                        f"Error: {details.get('error_message', 'unknown')}"
                    )
                else:
                    self.session_logger.info(f"{operation.upper()}: {details}")
            
            # Log to application logger with appropriate level
            if self.app_logger:
                if operation == "error":
                    self.app_logger.error(f"Operation failed: {details}")
                elif operation == "skip":
                    self.app_logger.warning(f"File skipped: {details}")
                else:
                    self.app_logger.info(f"Operation completed: {operation} - {details}")
                    
        except Exception as e:
            # Ensure logging errors don't break the application
            if self.app_logger:
                self.app_logger.error(f"Failed to log operation: {e}")
            else:
                print(f"Error: Failed to log operation: {e}")
    
    def log_error(self, error: Exception, context: str) -> None:
        """
        Log an error with context information.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
        """
        try:
            error_details = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context
            }
            
            if self.app_logger:
                self.app_logger.error(f"Error in {context}: {error}", exc_info=True)
            
            # Also log to session if available
            self.log_operation("error", {
                "context": context,
                "error_message": str(error),
                "error_type": type(error).__name__
            })
            
        except Exception as e:
            # Last resort - print to console
            print(f"Critical: Failed to log error: {e}")
            print(f"Original error in {context}: {error}")
    
    def save_session_log(self) -> Optional[str]:
        """
        Save the session log as a JSON file for detailed analysis.
        
        Returns:
            Path to saved session log file, or None if save failed
        """
        try:
            if not self.session_entries or not self.session_start_time:
                return None
            
            # Create session summary
            session_summary = {
                "session_start": self.session_start_time.isoformat(),
                "session_end": datetime.now().isoformat(),
                "total_operations": len(self.session_entries),
                "operations": self.session_entries
            }
            
            # Create JSON log filename
            timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
            json_log_file = self.logs_dir / f"session_{timestamp}.json"
            
            # Save to JSON file
            with open(json_log_file, 'w', encoding='utf-8') as f:
                json.dump(session_summary, f, indent=2, ensure_ascii=False)
            
            if self.session_logger:
                self.session_logger.info("=== File Processing Session Completed ===")
                self.session_logger.info(f"Total operations: {len(self.session_entries)}")
            
            if self.app_logger:
                self.app_logger.info(f"Session log saved: {json_log_file}")
            
            return str(json_log_file)
            
        except Exception as e:
            if self.app_logger:
                self.app_logger.error(f"Failed to save session log: {e}")
            else:
                print(f"Error: Failed to save session log: {e}")
            return None
    
    def rotate_logs(self, max_files: int = 20) -> None:
        """
        Rotate old log files to prevent excessive disk usage.
        
        Args:
            max_files: Maximum number of log files to keep
        """
        try:
            # Get all log files
            log_files = []
            for pattern in ["app_*.log", "session_*.log", "session_*.json"]:
                log_files.extend(self.logs_dir.glob(pattern))
            
            # Sort by modification time (oldest first)
            log_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Remove oldest files if we exceed the limit
            if len(log_files) > max_files:
                files_to_remove = log_files[:-max_files]
                for file_path in files_to_remove:
                    try:
                        file_path.unlink()
                        if self.app_logger:
                            self.app_logger.info(f"Rotated old log file: {file_path}")
                    except Exception as e:
                        if self.app_logger:
                            self.app_logger.warning(f"Failed to remove old log file {file_path}: {e}")
            
        except Exception as e:
            if self.app_logger:
                self.app_logger.error(f"Failed to rotate logs: {e}")
            else:
                print(f"Error: Failed to rotate logs: {e}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current session.
        
        Returns:
            Dictionary containing session statistics
        """
        if not self.session_entries:
            return {"total_operations": 0}
        
        # Count operations by type
        operation_counts = {}
        for entry in self.session_entries:
            op_type = entry.get("operation", "unknown")
            operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
        
        return {
            "total_operations": len(self.session_entries),
            "operation_counts": operation_counts,
            "session_start": self.session_start_time.isoformat() if self.session_start_time else None
        }
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
        """
        Clean up log files older than specified days.
        
        Args:
            days_to_keep: Number of days to keep log files
        """
        try:
            import time
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            # Get all log files
            log_files = []
            for pattern in ["app_*.log*", "session_*.*"]:
                log_files.extend(self.logs_dir.glob(pattern))
            
            removed_count = 0
            for file_path in log_files:
                try:
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
                except Exception as e:
                    if self.app_logger:
                        self.app_logger.warning(f"Failed to remove old log file {file_path}: {e}")
            
            if self.app_logger and removed_count > 0:
                self.app_logger.info(f"Cleaned up {removed_count} old log files")
                
        except Exception as e:
            if self.app_logger:
                self.app_logger.error(f"Failed to cleanup old logs: {e}")