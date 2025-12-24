#!/usr/bin/env python3
"""
Demo script to showcase session logging functionality.

This script demonstrates the session logging features implemented for the
Media File Renamer application.
"""

import os
import tempfile
import shutil
from datetime import datetime
from logging_manager import LoggingManager
from file_operations import FileOperations, FileInfo


def demo_session_logging():
    """Demonstrate session logging functionality."""
    print("=== Media File Renamer - Session Logging Demo ===\n")
    
    # Create temporary directory for demo
    demo_dir = tempfile.mkdtemp(prefix="session_logging_demo_")
    logs_dir = os.path.join(demo_dir, "logs")
    test_files_dir = os.path.join(demo_dir, "test_files")
    os.makedirs(test_files_dir)
    
    print(f"Demo directory: {demo_dir}")
    print(f"Logs directory: {logs_dir}")
    print(f"Test files directory: {test_files_dir}\n")
    
    try:
        # Initialize logging manager
        print("1. Initializing logging manager...")
        logging_manager = LoggingManager(logs_dir=logs_dir)
        app_logger = logging_manager.setup_application_logger("INFO")
        print("   ✓ Application logger initialized")
        
        # Setup session logger
        print("\n2. Setting up session logger...")
        session_logger = logging_manager.setup_session_logger()
        print("   ✓ Session logger initialized")
        print(f"   ✓ Session start time: {logging_manager.session_start_time}")
        
        # Create test files
        print("\n3. Creating test files...")
        test_files = ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]
        for filename in test_files:
            filepath = os.path.join(test_files_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"Test content for {filename}")
            print(f"   ✓ Created: {filename}")
        
        # Initialize file operations with session logging
        print("\n4. Initializing file operations with session logging...")
        supported_extensions = {'.jpg', '.jpeg', '.png', '.mp4', '.mov'}
        file_ops = FileOperations(
            supported_extensions, 
            logger=app_logger, 
            logging_manager=logging_manager
        )
        print("   ✓ File operations initialized with session logging")
        
        # Create file infos for processing
        print("\n5. Creating file processing data...")
        file_infos = [
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(test_files_dir, "IMG_001.jpg"),
                new_name="2023-01-15_12-30-45_NewYork.jpg",
                final_name="2023-01-15_12-30-45_NewYork.jpg",
                location="40.7128,-74.0060",
                city="New York",
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="IMG_002.jpg",
                original_path=os.path.join(test_files_dir, "IMG_002.jpg"),
                new_name="2023-01-16_14-15-30_Boston.jpg",
                final_name="2023-01-16_14-15-30_Boston.jpg",
                location="42.3601,-71.0589",
                city="Boston",
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="IMG_003.jpg",
                original_path=os.path.join(test_files_dir, "IMG_003.jpg"),
                new_name="No metadata",
                final_name="No metadata",
                location="",
                city="",
                has_metadata=False,
                selected=True
            )
        ]
        print(f"   ✓ Created {len(file_infos)} file info objects")
        
        # Process files with session logging
        print("\n6. Processing files with session logging...")
        
        def progress_callback(current, total, filename):
            print(f"   Processing {current}/{total}: {filename}")
        
        result = file_ops.process_files(test_files_dir, file_infos, progress_callback)
        
        print(f"\n   Processing Results:")
        print(f"   ✓ Processed: {result.processed_count} files")
        print(f"   ✓ Skipped: {result.skipped_count} files")
        print(f"   ✓ Errors: {result.error_count} files")
        
        # Show session summary
        print("\n7. Session logging summary...")
        session_summary = logging_manager.get_session_summary()
        print(f"   ✓ Total operations logged: {session_summary['total_operations']}")
        
        if "operation_counts" in session_summary:
            print("   ✓ Operation breakdown:")
            for op_type, count in session_summary["operation_counts"].items():
                print(f"     - {op_type}: {count}")
        
        # Save session log
        print("\n8. Saving session log...")
        session_log_path = logging_manager.save_session_log()
        if session_log_path:
            print(f"   ✓ Session log saved: {os.path.basename(session_log_path)}")
            print(f"   ✓ Full path: {session_log_path}")
            
            # Show session log content
            print("\n9. Session log content preview:")
            import json
            with open(session_log_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            print(f"   Session Start: {session_data['session_start']}")
            print(f"   Session End: {session_data['session_end']}")
            print(f"   Total Operations: {session_data['total_operations']}")
            print("   Operations:")
            for i, op in enumerate(session_data['operations'][:5], 1):  # Show first 5
                print(f"     {i}. {op['operation']}: {op.get('old_name', op.get('filename', 'N/A'))}")
            if len(session_data['operations']) > 5:
                print(f"     ... and {len(session_data['operations']) - 5} more operations")
        else:
            print("   ✗ Failed to save session log")
        
        # Show log files created
        print("\n10. Log files created:")
        if os.path.exists(logs_dir):
            log_files = os.listdir(logs_dir)
            for log_file in sorted(log_files):
                file_path = os.path.join(logs_dir, log_file)
                file_size = os.path.getsize(file_path)
                print(f"    ✓ {log_file} ({file_size} bytes)")
        
        print("\n=== Session Logging Demo Complete ===")
        print(f"Demo files are in: {demo_dir}")
        print("You can examine the log files to see the detailed session information.")
        
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup (optional - comment out to keep files for inspection)
        try:
            # shutil.rmtree(demo_dir, ignore_errors=True)
            # print(f"\nCleaned up demo directory: {demo_dir}")
            pass
        except Exception as e:
            print(f"Warning: Could not clean up demo directory: {e}")


if __name__ == "__main__":
    demo_session_logging()