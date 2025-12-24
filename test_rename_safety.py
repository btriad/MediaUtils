#!/usr/bin/env python3
"""
Test to verify that rename operations ONLY rename files and do nothing else.

This test confirms:
- Files stay in the same directory
- File contents are not modified
- No files are deleted
- No files are moved to different directories
"""

import os
import tempfile
import shutil
from pathlib import Path
from file_operations import FileOperations, FileInfo


def test_rename_safety():
    """Test that rename operations are safe and only rename files."""
    print("=" * 60)
    print("RENAME OPERATION SAFETY TEST")
    print("=" * 60)
    
    # Create temporary test directory
    test_dir = tempfile.mkdtemp(prefix="rename_safety_test_")
    print(f"\nTest directory: {test_dir}")
    
    try:
        # Create test files with known content
        test_files = {
            "test1.jpg": b"JPEG file content - test 1",
            "test2.jpg": b"JPEG file content - test 2",
            "test3.nef": b"NEF RAW file content - test 3"
        }
        
        print("\n1. Creating test files...")
        for filename, content in test_files.items():
            filepath = os.path.join(test_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(content)
            print(f"   Created: {filename} ({len(content)} bytes)")
        
        # Record original state
        print("\n2. Recording original state...")
        original_files = set(os.listdir(test_dir))
        original_contents = {}
        original_sizes = {}
        
        for filename in original_files:
            filepath = os.path.join(test_dir, filename)
            with open(filepath, 'rb') as f:
                original_contents[filename] = f.read()
            original_sizes[filename] = os.path.getsize(filepath)
            print(f"   {filename}: {original_sizes[filename]} bytes")
        
        # Prepare rename operations
        print("\n3. Preparing rename operations...")
        file_ops = FileOperations({'.jpg', '.nef'})
        
        file_infos = [
            FileInfo(
                original_name="test1.jpg",
                original_path=os.path.join(test_dir, "test1.jpg"),
                new_name="renamed1.jpg",
                final_name="renamed1.jpg",
                location="Test Location",
                city="Test City",
                has_metadata=False,
                selected=True
            ),
            FileInfo(
                original_name="test2.jpg",
                original_path=os.path.join(test_dir, "test2.jpg"),
                new_name="renamed2.jpg",
                final_name="renamed2.jpg",
                location="Test Location",
                city="Test City",
                has_metadata=False,
                selected=True
            ),
            FileInfo(
                original_name="test3.nef",
                original_path=os.path.join(test_dir, "test3.nef"),
                new_name="renamed3.nef",
                final_name="renamed3.nef",
                location="Test Location",
                city="Test City",
                has_metadata=False,
                selected=True
            )
        ]
        
        # Execute rename operations
        print("\n4. Executing rename operations...")
        result = file_ops.process_files(test_dir, file_infos)
        print(f"   Processed: {result.processed_count}")
        print(f"   Errors: {result.error_count}")
        print(f"   Skipped: {result.skipped_count}")
        
        # Verify results
        print("\n5. Verifying safety constraints...")
        
        # Check 1: Same number of files (no deletion, no creation except backup)
        current_files = set(os.listdir(test_dir))
        media_files = {f for f in current_files if not f.startswith('.media_renamer')}
        
        if len(media_files) == len(original_files):
            print("   ✓ PASS: Same number of files (no deletion)")
        else:
            print(f"   ✗ FAIL: File count changed ({len(original_files)} -> {len(media_files)})")
            return False
        
        # Check 2: All files still in same directory
        for filename in media_files:
            filepath = os.path.join(test_dir, filename)
            if os.path.dirname(filepath) == test_dir:
                continue
            else:
                print(f"   ✗ FAIL: File moved to different directory: {filename}")
                return False
        print("   ✓ PASS: All files remain in same directory")
        
        # Check 3: File contents unchanged
        contents_match = True
        for new_filename in media_files:
            new_filepath = os.path.join(test_dir, new_filename)
            with open(new_filepath, 'rb') as f:
                new_content = f.read()
            
            # Find matching original content
            found_match = False
            for orig_content in original_contents.values():
                if new_content == orig_content:
                    found_match = True
                    break
            
            if not found_match:
                print(f"   ✗ FAIL: Content modified for {new_filename}")
                contents_match = False
        
        if contents_match:
            print("   ✓ PASS: All file contents unchanged")
        else:
            return False
        
        # Check 4: File sizes unchanged
        sizes_match = True
        for new_filename in media_files:
            new_filepath = os.path.join(test_dir, new_filename)
            new_size = os.path.getsize(new_filepath)
            
            # Find matching original size
            found_match = False
            for orig_size in original_sizes.values():
                if new_size == orig_size:
                    found_match = True
                    break
            
            if not found_match:
                print(f"   ✗ FAIL: Size changed for {new_filename}")
                sizes_match = False
        
        if sizes_match:
            print("   ✓ PASS: All file sizes unchanged")
        else:
            return False
        
        # Check 5: Only filenames changed
        expected_new_names = {"renamed1.jpg", "renamed2.jpg", "renamed3.nef"}
        if media_files == expected_new_names:
            print("   ✓ PASS: Only filenames changed (as expected)")
        else:
            print(f"   ✗ FAIL: Unexpected filenames: {media_files}")
            return False
        
        # Check 6: Backup log created (optional safety feature)
        backup_files = [f for f in current_files if f.startswith('.media_renamer')]
        if backup_files:
            print(f"   ✓ PASS: Backup log created: {backup_files[0]}")
        else:
            print("   ⚠ INFO: No backup log created (optional feature)")
        
        # Check 7: Verify content mapping
        print("\n6. Verifying content integrity...")
        content_map = {
            "renamed1.jpg": test_files["test1.jpg"],
            "renamed2.jpg": test_files["test2.jpg"],
            "renamed3.nef": test_files["test3.nef"]
        }
        
        all_match = True
        for new_name, expected_content in content_map.items():
            filepath = os.path.join(test_dir, new_name)
            with open(filepath, 'rb') as f:
                actual_content = f.read()
            
            if actual_content == expected_content:
                print(f"   ✓ {new_name}: Content matches original")
            else:
                print(f"   ✗ {new_name}: Content DOES NOT match!")
                all_match = False
        
        if not all_match:
            return False
        
        print("\n" + "=" * 60)
        print("SAFETY TEST RESULT: ✓ PASSED")
        print("=" * 60)
        print("\nConfirmed:")
        print("✓ Files only renamed (not deleted, moved, or modified)")
        print("✓ All files remain in same directory")
        print("✓ File contents completely unchanged")
        print("✓ File sizes unchanged")
        print("✓ Only filenames changed")
        print("\n✓ RENAME OPERATION IS SAFE")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        print(f"\nCleaning up test directory: {test_dir}")
        try:
            shutil.rmtree(test_dir)
            print("✓ Cleanup complete")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")


if __name__ == "__main__":
    success = test_rename_safety()
    exit(0 if success else 1)
