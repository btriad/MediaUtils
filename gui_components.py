"""
GUI Components Module

Contains the main GUI interface for the Media File Renamer application.
Handles user interactions, file display, and progress updates.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from typing import List, Optional, Callable
from file_operations import FileInfo, ProcessResult
from settings_manager import SettingsManager
from filename_generator import FilenameGenerator, ValidationResult, ValidationSeverity
from media_processor import MediaProcessor
from file_operations import FileOperations
from logging_manager import LoggingManager
from city_cache import CityCache


class MediaRenamerGUI:
    """Main GUI class for the Media File Renamer application."""
    
    def __init__(self, logging_manager=None, city_cache=None, error_recovery=None, settings_manager=None):
        """
        Initialize the GUI application with integrated systems.
        
        Args:
            logging_manager: Pre-initialized logging manager
            city_cache: Pre-initialized city cache
            error_recovery: Pre-initialized error recovery system
            settings_manager: Pre-initialized settings manager
        """
        # Use provided systems or create defaults for backward compatibility
        self.settings_manager = settings_manager or SettingsManager()
        self.filename_generator = FilenameGenerator()
        self.logging_manager = logging_manager or LoggingManager()
        self.error_recovery = error_recovery
        
        # Setup application logger
        try:
            if logging_manager:
                self.app_logger = logging_manager.app_logger
            else:
                self.app_logger = self.logging_manager.setup_application_logger()
            
            if self.app_logger:
                self.app_logger.info("GUI application starting up with integrated systems")
        except Exception as e:
            # Requirement 5.7: Continue operation and maintain existing print statements as fallback when logging fails
            print(f"Warning: Failed to setup GUI logger: {e}")
            print("Continuing with fallback logging to console")
            self.app_logger = None
        
        # Use provided city cache or create default
        if city_cache:
            self.city_cache = city_cache
        else:
            cache_file = "city_cache.json"
            max_cache_size = self.settings_manager.get("max_city_cache_size", 1000)
            self.city_cache = CityCache(cache_file=cache_file, max_entries=max_cache_size)
            self.load_city_cache()
        
        # Initialize media processor with integrated systems
        self.media_processor = MediaProcessor(
            city_cache=self.city_cache, 
            logger=self.app_logger,
            error_recovery=self.error_recovery
        )
        
        # Combine supported extensions from media processor
        supported_extensions = (self.media_processor.image_extensions | 
                              self.media_processor.video_extensions)
        self.file_operations = FileOperations(
            supported_extensions, 
            logger=self.app_logger, 
            logging_manager=self.logging_manager,
            error_recovery=self.error_recovery
        )
        
        # Initialize GUI
        self.root = tk.Tk()
        self.root.title("Media File Renamer")
        self.root.geometry(self.settings_manager.get("window_geometry", "1200x600"))
        
        if self.app_logger:
            self.app_logger.info(f"GUI window initialized with geometry: {self.root.geometry()}")
        
        # Setup custom styles
        self.setup_custom_styles()
        
        # File data storage
        self.file_infos: List[FileInfo] = []
        
        # Validation state
        self.last_validation_result: Optional[ValidationResult] = None
        self.validation_after_id: Optional[str] = None
        
        # Create GUI components
        self.create_widgets()
        self.load_initial_settings()
        
        # Bind window close event to save settings and cache
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        if self.app_logger:
            self.app_logger.info("GUI application initialization completed")
    
    def setup_custom_styles(self):
        """Setup custom TTK styles for validation feedback."""
        try:
            style = ttk.Style()
            
            # Create error style for entry widgets
            style.configure("Error.TEntry", 
                          fieldbackground="#ffe6e6",  # Light red background
                          bordercolor="#ff6666")      # Red border
            
            # Create warning style for entry widgets  
            style.configure("Warning.TEntry",
                          fieldbackground="#fff3cd",  # Light yellow background
                          bordercolor="#ffc107")      # Yellow border
                          
        except Exception as e:
            # If custom styles fail, continue without them
            print(f"Warning: Could not setup custom styles: {e}")
    
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        # Configure main grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)
        
        # Create main sections
        self._create_folder_section()
        self._create_format_section()
        self._create_button_section()
        self._create_file_list_section()
    
    def _create_folder_section(self):
        """Create folder selection section."""
        folder_frame = ttk.Frame(self.root, padding="10")
        folder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        folder_frame.columnconfigure(0, weight=1)
        
        ttk.Label(folder_frame, text="Folder Path:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.folder_var = tk.StringVar(value=self.settings_manager.get("folder_path"))
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=50)
        folder_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).grid(row=1, column=1)
    
    def _create_format_section(self):
        """Create filename format section with validation feedback."""
        format_frame = ttk.Frame(self.root, padding="10")
        format_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        format_frame.columnconfigure(0, weight=1)
        
        # Format label with validation status
        format_header_frame = ttk.Frame(format_frame)
        format_header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        format_header_frame.columnconfigure(0, weight=1)
        
        ttk.Label(format_header_frame, text="Filename Format:").grid(row=0, column=0, sticky=tk.W)
        
        # Validation status indicator
        self.validation_status_label = ttk.Label(format_header_frame, text="", foreground="green")
        self.validation_status_label.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))
        
        # Format entry with validation styling
        self.format_var = tk.StringVar(value=self.settings_manager.get("filename_format"))
        self.format_entry = ttk.Entry(format_frame, textvariable=self.format_var, width=60)
        self.format_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Example label
        self.example_label = ttk.Label(format_frame, foreground="gray")
        self.example_label.grid(row=2, column=0, sticky=tk.W)
        
        # Validation messages frame
        self.validation_frame = ttk.Frame(format_frame)
        self.validation_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        self.validation_frame.columnconfigure(0, weight=1)
        
        # Validation messages text widget (initially hidden)
        self.validation_text = tk.Text(self.validation_frame, height=4, wrap=tk.WORD, 
                                     font=("Arial", 8), state=tk.DISABLED)
        self.validation_scrollbar = ttk.Scrollbar(self.validation_frame, orient=tk.VERTICAL, 
                                                command=self.validation_text.yview)
        self.validation_text.configure(yscrollcommand=self.validation_scrollbar.set)
        
        # Configure text tags for different message types
        self.validation_text.tag_configure("error", foreground="red")
        self.validation_text.tag_configure("warning", foreground="orange")
        self.validation_text.tag_configure("info", foreground="blue")
        self.validation_text.tag_configure("suggestion", foreground="green", font=("Arial", 8, "italic"))
        
        # Suggestions button (initially hidden)
        self.suggestions_button = ttk.Button(self.validation_frame, text="Show Format Suggestions", 
                                           command=self.show_format_suggestions)
        
        # Bind format change to update validation with debouncing
        self.format_var.trace('w', self.schedule_validation_update)
        self.update_format_validation()
    
    def _create_button_section(self):
        """Create action buttons section."""
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=2, column=0)
        
        ttk.Button(button_frame, text="Save Settings", 
                  command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Show Files", 
                  command=self.show_files).pack(side=tk.LEFT, padx=5)
        self.process_button = ttk.Button(button_frame, text="Process Files", 
                                       command=self.process_files)
        self.process_button.pack(side=tk.LEFT, padx=5)
    
    def _create_file_list_section(self):
        """Create file list and statistics section."""
        files_frame = ttk.Frame(self.root, padding="10")
        files_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(1, weight=1)
        
        # Stats and select all frame
        stats_frame = ttk.Frame(files_frame)
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.stats_label = ttk.Label(stats_frame, text="Total found: 0  Total Selected: 0")
        self.stats_label.pack(side=tk.LEFT)
        
        self.select_all_var = tk.BooleanVar()
        select_all_cb = ttk.Checkbutton(stats_frame, text="Select All", 
                                       variable=self.select_all_var, 
                                       command=self.toggle_all)
        select_all_cb.pack(side=tk.LEFT, padx=(20, 0))
        
        # Treeview for file list
        self._create_file_treeview(files_frame)
        
        # Progress and status frame
        progress_frame = ttk.Frame(files_frame)
        progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(1, weight=1)
        
        # Status label for progress updates
        self.status_label = ttk.Label(progress_frame, text="", foreground="blue")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Progress bar (initially hidden)
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        self.progress_bar.grid_remove()  # Hide initially
        
        # Logging status indicator (clickable for detailed stats)
        self.logging_status_label = ttk.Label(progress_frame, text="", foreground="gray", font=("Arial", 8), cursor="hand2")
        self.logging_status_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
        self.logging_status_label.bind("<Button-1>", self.show_detailed_status)
        
        # Initialize cache status display if cache status was set during startup
        if hasattr(self, '_cache_status'):
            self.update_cache_status(self._cache_status)
    
    def _create_file_treeview(self, parent_frame):
        """Create the file list treeview widget."""
        columns = ('Select', 'Current Name', 'New Name', 'Location', 'City')
        self.tree = ttk.Treeview(parent_frame, columns=columns, show='headings', height=15)
        
        # Configure column headings
        self.tree.heading('Select', text='Select')
        self.tree.heading('Current Name', text='Current Name')
        self.tree.heading('New Name', text='New Name')
        self.tree.heading('Location', text='Location')
        self.tree.heading('City', text='City')
        
        # Configure column widths
        self.tree.column('Select', width=60)
        self.tree.column('Current Name', width=200)
        self.tree.column('New Name', width=200)
        self.tree.column('Location', width=150)
        self.tree.column('City', width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout
        self.tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Bind click events
        self.tree.bind('<Button-1>', self.on_tree_click)
    
    def load_initial_settings(self):
        """Load initial settings into GUI components."""
        # Update filename generator with current format
        format_pattern = self.format_var.get()
        self.filename_generator.set_format(format_pattern)
    
    def browse_folder(self):
        """Open folder browser dialog."""
        initial_dir = self.folder_var.get()
        if self.app_logger:
            self.app_logger.info(f"User opened folder browser dialog, initial dir: {initial_dir}")
        
        folder = filedialog.askdirectory(initialdir=initial_dir)
        if folder:
            self.folder_var.set(folder)
            if self.app_logger:
                self.app_logger.info(f"User selected folder: {folder}")
        else:
            if self.app_logger:
                self.app_logger.debug("User cancelled folder selection")
    
    def save_settings(self):
        """Save current settings to file."""
        if self.app_logger:
            self.app_logger.info("User initiated settings save")
        
        try:
            # Update settings with current values
            folder_path = self.folder_var.get()
            filename_format = self.format_var.get()
            window_geometry = self.root.geometry()
            
            self.settings_manager.set("folder_path", folder_path)
            self.settings_manager.set("filename_format", filename_format)
            self.settings_manager.set("window_geometry", window_geometry)
            
            # Add current format to recent formats
            self.settings_manager.add_recent_format(filename_format)
            
            if self.app_logger:
                self.app_logger.debug(f"Settings to save - Folder: {folder_path}, Format: {filename_format}")
            
            # Save to file
            if self.settings_manager.save_settings():
                if self.app_logger:
                    self.app_logger.info("Settings saved successfully")
                messagebox.showinfo("Settings", "Settings saved successfully!")
            else:
                if self.app_logger:
                    self.app_logger.error("Failed to save settings")
                messagebox.showerror("Error", "Could not save settings.")
                
        except Exception as e:
            if self.app_logger:
                self.app_logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Could not save settings: {e}")
    
    def schedule_validation_update(self, *args):
        """Schedule validation update with debouncing to avoid excessive validation calls."""
        # Cancel previous scheduled update
        if self.validation_after_id:
            self.root.after_cancel(self.validation_after_id)
        
        # Schedule new update after 300ms delay
        self.validation_after_id = self.root.after(300, self.update_format_validation)
    
    def update_format_validation(self):
        """Update format validation with comprehensive feedback."""
        try:
            format_pattern = self.format_var.get()
            
            # Perform detailed validation
            validation_result = self.filename_generator.validate_format_detailed(format_pattern)
            self.last_validation_result = validation_result
            
            # Update validation status indicator (Requirements 4.5, 4.6)
            if validation_result.is_valid:
                # Check if there are any warnings or info messages
                has_warnings = any(msg.severity == ValidationSeverity.WARNING for msg in validation_result.messages)
                has_suggestions = any(msg.severity == ValidationSeverity.INFO for msg in validation_result.messages)
                
                if has_warnings:
                    # Requirement 4.6: Show example with warning indicators when format has warnings but is usable
                    self.validation_status_label.config(text="✓ Valid (with warnings)", foreground="orange")
                    try:
                        self.format_entry.config(style="Warning.TEntry")
                    except:
                        pass
                elif has_suggestions:
                    self.validation_status_label.config(text="✓ Valid (suggestions available)", foreground="green")
                    try:
                        self.format_entry.config(style="TEntry")
                    except:
                        pass
                else:
                    # Requirement 4.5: Show a green checkmark or "Valid format" message when format is valid
                    self.validation_status_label.config(text="✓ Valid format", foreground="green")
                    try:
                        self.format_entry.config(style="TEntry")
                    except:
                        pass
            else:
                self.validation_status_label.config(text="✗ Invalid", foreground="red")
                # Update entry styling for invalid format (if custom style is available)
                try:
                    self.format_entry.config(style="Error.TEntry")
                except:
                    pass  # Fallback if custom style not available
            
            # Update example
            if validation_result.example:
                self.example_label.config(text=f"Example: {validation_result.example}", foreground="gray")
            else:
                self.example_label.config(text="Example: Invalid format", foreground="red")
            
            # Update validation messages
            self.update_validation_messages(validation_result)
            
        except Exception as e:
            self.validation_status_label.config(text="✗ Error", foreground="red")
            self.example_label.config(text=f"Error: {str(e)}", foreground="red")
            self.hide_validation_messages()
    
    def update_validation_messages(self, validation_result: ValidationResult):
        """Update the validation messages display."""
        if not validation_result.messages:
            self.hide_validation_messages()
            return
        
        # Show validation messages
        self.validation_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.validation_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Clear existing content
        self.validation_text.config(state=tk.NORMAL)
        self.validation_text.delete(1.0, tk.END)
        
        # Add messages grouped by severity
        errors = validation_result.errors
        warnings = validation_result.warnings
        infos = [msg for msg in validation_result.messages if msg.severity == ValidationSeverity.INFO]
        
        if errors:
            self.validation_text.insert(tk.END, "Errors:\n", "error")
            for msg in errors:
                self.validation_text.insert(tk.END, f"• {msg.message}\n", "error")
                if msg.suggestion:
                    self.validation_text.insert(tk.END, f"  → {msg.suggestion}\n", "suggestion")
            self.validation_text.insert(tk.END, "\n")
        
        if warnings:
            self.validation_text.insert(tk.END, "Warnings:\n", "warning")
            for msg in warnings:
                self.validation_text.insert(tk.END, f"• {msg.message}\n", "warning")
                if msg.suggestion:
                    self.validation_text.insert(tk.END, f"  → {msg.suggestion}\n", "suggestion")
            self.validation_text.insert(tk.END, "\n")
        
        if infos:
            self.validation_text.insert(tk.END, "Suggestions:\n", "info")
            for msg in infos:
                self.validation_text.insert(tk.END, f"• {msg.message}\n", "info")
                if msg.suggestion:
                    self.validation_text.insert(tk.END, f"  → {msg.suggestion}\n", "suggestion")
        
        # Requirement 10.5: Show available additional placeholders when user creates a valid format
        if validation_result.is_valid and not errors and not warnings:
            format_str = self.format_var.get()
            available_placeholders = self._get_unused_placeholders(format_str)
            
            if available_placeholders:
                if infos:
                    self.validation_text.insert(tk.END, "\n")
                self.validation_text.insert(tk.END, "Available additional placeholders:\n", "info")
                for placeholder, description in available_placeholders.items():
                    self.validation_text.insert(tk.END, f"• {placeholder}: {description}\n", "suggestion")
        
        self.validation_text.config(state=tk.DISABLED)
        
        # Show suggestions button if format is valid but has suggestions
        if validation_result.is_valid and (warnings or infos):
            self.suggestions_button.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        else:
            self.suggestions_button.grid_remove()
    
    def _get_unused_placeholders(self, format_str: str) -> dict:
        """
        Get placeholders that are not currently used in the format string.
        
        Args:
            format_str: Current format string
            
        Returns:
            Dictionary of unused placeholders and their descriptions
        """
        all_placeholders = self.filename_generator.get_available_placeholders()
        unused = {}
        
        # Check which placeholders are not in the current format
        for placeholder, description in all_placeholders.items():
            # For strftime codes, check if the code is in the format
            if placeholder.startswith('%'):
                if placeholder not in format_str:
                    unused[placeholder] = description
            # For custom placeholders, check if the placeholder is in the format
            elif placeholder.startswith('{'):
                if placeholder not in format_str:
                    unused[placeholder] = description
        
        # Limit to most useful suggestions (max 5)
        priority_placeholders = ['{increment:03d}', '{city}', '%Y', '%m', '%d', '%H', '%M', '%S']
        prioritized = {}
        
        for priority in priority_placeholders:
            if priority in unused:
                prioritized[priority] = unused[priority]
                if len(prioritized) >= 5:
                    break
        
        # Add remaining if we have space
        for placeholder, description in unused.items():
            if placeholder not in prioritized and len(prioritized) < 5:
                prioritized[placeholder] = description
        
        return prioritized
    
    def hide_validation_messages(self):
        """Hide the validation messages display."""
        self.validation_text.grid_remove()
        self.validation_scrollbar.grid_remove()
        self.suggestions_button.grid_remove()
    
    def show_format_suggestions(self):
        """Show a dialog with format pattern suggestions."""
        suggestions = self.filename_generator.get_format_suggestions()
        
        # Create suggestions dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Format Pattern Suggestions")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        center_window(dialog, 600, 400)
        
        # Create main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        ttk.Label(main_frame, text="Click on a suggestion to use it:", 
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Suggestions listbox with scrollbar
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        suggestions_listbox = tk.Listbox(list_frame, font=("Courier", 9))
        suggestions_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                            command=suggestions_listbox.yview)
        suggestions_listbox.configure(yscrollcommand=suggestions_scrollbar.set)
        
        suggestions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        suggestions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add suggestions to listbox
        for suggestion in suggestions:
            suggestions_listbox.insert(tk.END, suggestion)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def use_suggestion():
            selection = suggestions_listbox.curselection()
            if selection:
                selected_format = suggestions_listbox.get(selection[0])
                self.format_var.set(selected_format)
                dialog.destroy()
        
        def preview_suggestion(event):
            selection = suggestions_listbox.curselection()
            if selection:
                selected_format = suggestions_listbox.get(selection[0])
                try:
                    example = self.filename_generator.generate_example()
                    # Update a preview label if we had one
                except:
                    pass
        
        ttk.Button(button_frame, text="Use Selected", command=use_suggestion).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=(10, 0))
        
        # Bind double-click to use suggestion
        suggestions_listbox.bind('<Double-Button-1>', lambda e: use_suggestion())
        suggestions_listbox.bind('<<ListboxSelect>>', preview_suggestion)
    
    def update_example(self, *args):
        """Update the filename format example (legacy method for backward compatibility)."""
        self.update_format_validation()
    
    def show_files(self):
        """Discover and display files in the selected folder."""
        folder_path = self.folder_var.get()
        
        if self.app_logger:
            self.app_logger.info(f"User initiated file discovery for folder: {folder_path}")
        
        # Validate folder path
        if not self.settings_manager.validate_folder_path(folder_path):
            if self.app_logger:
                self.app_logger.error(f"Invalid folder path: {folder_path}")
            messagebox.showerror("Error", "Selected folder does not exist or is not accessible.")
            return
        
        # Initialize logging for this operation
        self.update_logging_status("Initializing logging...")
        
        try:
            # Setup application logger if not already done
            if not self.logging_manager.app_logger:
                self.logging_manager.setup_application_logger()
            
            self.update_logging_status("Logging ready")
            
            # Show loading message and progress bar
            self.show_progress_bar()
            self.update_progress(0, "Discovering files...")
            
            # Clear existing data
            self.clear_file_list()
            
            if self.app_logger:
                self.app_logger.info("Starting file discovery and metadata extraction")
            
            # Discover files with progress callback
            def progress_callback(current, total, filename):
                progress_percent = (current / total) * 50 if total > 0 else 0  # First 50% for discovery
                self.update_progress(progress_percent, f"Scanning {current}/{total} files...")
            
            file_paths = self.file_operations.discover_files(folder_path, progress_callback)
            
            if self.logging_manager.app_logger:
                self.logging_manager.app_logger.info(f"Discovered {len(file_paths)} files in {folder_path}")
            
            # Process each file to extract metadata
            self.file_infos = []
            missing_metadata_count = 0
            
            for i, filepath in enumerate(file_paths, 1):
                # Update progress (50-100% for processing)
                progress_percent = 50 + ((i / len(file_paths)) * 50) if file_paths else 100
                self.update_progress(progress_percent, f"Processing {i}/{len(file_paths)} files...")
                
                # Extract metadata
                file_date, has_metadata = self.media_processor.get_file_date(filepath)
                location, city = self.media_processor.get_location_and_city(filepath)
                
                # Generate new filename
                filename = os.path.basename(filepath)
                new_name, _ = self.filename_generator.generate_filename(
                    filepath, file_date, has_metadata, location, city, i
                )
                
                # Create FileInfo object
                file_info = FileInfo(
                    original_name=filename,
                    original_path=filepath,
                    new_name=new_name,
                    final_name=new_name,  # Initially same as new_name, will be updated by duplicate resolution
                    location=location,
                    city=city,
                    has_metadata=has_metadata,
                    selected=False
                )
                
                self.file_infos.append(file_info)
                
                if not has_metadata:
                    missing_metadata_count += 1
                
                # Add to treeview
                self.tree.insert('', 'end', values=(
                    '☐', filename, new_name, location, city
                ))
            
            # Complete progress
            self.update_progress(100, "Complete")
            
            # Update statistics
            self.update_stats(missing_metadata_count)
            
            # Log completion
            if self.logging_manager.app_logger:
                self.logging_manager.app_logger.info(f"File discovery completed: {len(self.file_infos)} files processed, {missing_metadata_count} without metadata")
            
            # Update cache statistics after processing
            self.update_cache_status()  # Use enhanced method to show detailed stats
            
            # Hide progress bar after a short delay
            self.root.after(1000, self.hide_progress_bar)
            
        except Exception as e:
            self.hide_progress_bar()
            self.update_logging_status("Error occurred")
            if self.logging_manager.app_logger:
                self.logging_manager.log_error(e, "show_files")
            messagebox.showerror("Error", f"Could not process folder: {e}")
    
    def clear_file_list(self):
        """Clear the file list and reset selection state."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.file_infos.clear()
        self.select_all_var.set(False)
    
    def on_tree_click(self, event):
        """Handle clicks on the file list treeview."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            
            if column == '#1':  # Select column
                self.toggle_file_selection(item)
    
    def toggle_file_selection(self, item):
        """Toggle selection state of a file item."""
        try:
            # Get item index
            item_index = self.tree.index(item)
            
            # Toggle selection in data
            old_state = self.file_infos[item_index].selected
            self.file_infos[item_index].selected = not old_state
            
            if self.app_logger:
                filename = self.file_infos[item_index].original_name
                new_state = "selected" if self.file_infos[item_index].selected else "deselected"
                self.app_logger.debug(f"User {new_state} file: {filename}")
            
            # Update treeview display
            values = list(self.tree.item(item, 'values'))
            values[0] = '☑' if self.file_infos[item_index].selected else '☐'
            self.tree.item(item, values=values)
            
            # Update statistics
            self.update_stats()
            
        except (IndexError, tk.TclError) as e:
            if self.app_logger:
                self.app_logger.warning(f"Error toggling file selection: {e}")
            pass  # Handle invalid item gracefully
    
    def toggle_all(self):
        """Toggle selection state of all files."""
        select_state = self.select_all_var.get()
        
        if self.app_logger:
            action = "selected" if select_state else "deselected"
            self.app_logger.info(f"User {action} all files ({len(self.file_infos)} files)")
        
        # Update all file infos
        for file_info in self.file_infos:
            file_info.selected = select_state
        
        # Update treeview display
        checkbox_state = '☑' if select_state else '☐'
        for item in self.tree.get_children():
            values = list(self.tree.item(item, 'values'))
            values[0] = checkbox_state
            self.tree.item(item, values=values)
        
        # Update statistics
        self.update_stats()
    
    def update_stats(self, missing_metadata_count: int = 0):
        """Update file statistics display."""
        total = len(self.file_infos)
        selected = sum(1 for f in self.file_infos if f.selected)
        
        stats_text = f"Total found: {total}  Total Selected: {selected}"
        if missing_metadata_count > 0:
            stats_text += f"  Missing metadata: {missing_metadata_count}"
        
        self.stats_label.config(text=stats_text)
        
        # Update select all checkbox state
        if selected == 0:
            self.select_all_var.set(False)
        elif selected == total and total > 0:
            self.select_all_var.set(True)
    
    def _update_display_with_resolved_names(self):
        """Update the treeview display with resolved final names."""
        # Clear and repopulate the treeview with resolved names
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for file_info in self.file_infos:
            checkbox = '☑' if file_info.selected else '☐'
            self.tree.insert('', 'end', values=(
                checkbox, 
                file_info.original_name, 
                file_info.final_name,  # Use final_name instead of new_name
                file_info.location, 
                file_info.city
            ))
    
    def process_files(self):
        """Process selected files for renaming."""
        if self.app_logger:
            self.app_logger.info("User initiated file processing")
        
        # Check if any files are selected
        selected_files = [f for f in self.file_infos if f.selected]
        if not selected_files:
            if self.app_logger:
                self.app_logger.warning("File processing cancelled: no files selected")
            messagebox.showwarning("Warning", "No files selected for processing.")
            return
        
        if self.app_logger:
            self.app_logger.info(f"Processing {len(selected_files)} selected files")
        
        # Validate format before processing
        if self.last_validation_result and not self.last_validation_result.is_valid:
            if self.app_logger:
                self.app_logger.error("File processing cancelled: invalid filename format")
            messagebox.showerror("Invalid Format", 
                               "Please fix the filename format errors before processing files.")
            return
        
        # Setup session logging
        self.update_logging_status("Starting session logging...")
        try:
            if not self.logging_manager.session_logger:
                self.logging_manager.setup_session_logger()
            self.update_logging_status("Session logging active")
        except Exception as e:
            self.update_logging_status("Session logging failed")
            if self.logging_manager.app_logger:
                self.logging_manager.log_error(e, "session_logging_setup")
        
        # Apply duplicate resolution and conflict resolution
        folder_path = self.folder_var.get()
        self.file_infos = self.file_operations.resolve_duplicates_and_conflicts(
            folder_path, self.file_infos
        )
        
        # Update the display with resolved names
        self._update_display_with_resolved_names()
        
        # Show confirmation dialog
        if self.app_logger:
            self.app_logger.debug("Showing user confirmation dialog for file processing")
        
        if not messagebox.askyesno("Confirm", 
                                  f"Rename {len(selected_files)} selected files?"):
            if self.app_logger:
                self.app_logger.info("User cancelled file processing at confirmation dialog")
            return
        
        if self.app_logger:
            self.app_logger.info("User confirmed file processing, starting operation")
        
        # Disable process button and show progress
        self.process_button.config(state='disabled')
        self.show_progress_bar()
        
        try:
            # Progress callback with logging
            def progress_callback(current, total, filename):
                progress_percent = (current / total) * 100 if total > 0 else 0
                self.update_progress(progress_percent, f"Processing {current}/{total} files...")
                
                # Log progress to session
                if self.logging_manager.session_logger:
                    self.logging_manager.log_operation("progress", {
                        "current": current,
                        "total": total,
                        "filename": filename
                    })
            
            # Log processing start
            if self.logging_manager.app_logger:
                self.logging_manager.app_logger.info(f"Starting file processing: {len(selected_files)} files selected")
            
            # Process files
            result = self.file_operations.process_files(
                folder_path, self.file_infos, progress_callback
            )
            
            # Complete progress
            self.update_progress(100, "Processing complete")
            
            # Save session log
            self.update_logging_status("Saving session log...")
            try:
                session_log_path = self.logging_manager.save_session_log()
                if session_log_path:
                    self.update_logging_status(f"Session saved: {os.path.basename(session_log_path)}")
                else:
                    # Requirement 8.6: Display a warning but continue operation when saving session logs fails
                    self.update_logging_status("Session log save failed")
                    messagebox.showwarning("Session Log Warning", 
                                         "Failed to save session log file. Processing completed successfully but session details were not saved.")
            except Exception as e:
                # Requirement 8.6: Display a warning but continue operation when saving session logs fails
                self.update_logging_status("Session log save error")
                if self.logging_manager.app_logger:
                    self.logging_manager.log_error(e, "session_log_save")
                messagebox.showwarning("Session Log Error", 
                                     f"Error saving session log: {str(e)}\nProcessing completed successfully but session details were not saved.")
            
            # Log processing completion
            if self.logging_manager.app_logger:
                self.logging_manager.app_logger.info(
                    f"File processing completed: {result.processed_count} processed, "
                    f"{result.skipped_count} skipped, {len(result.errors)} errors"
                )
            
            # Show results
            self.show_process_results(result)
            
            # Update cache statistics after processing
            self.update_cache_status()  # Use enhanced method to show detailed stats
            
            # Refresh file list if any files were processed
            if result.processed_count > 0:
                self.show_files()
                
        except Exception as e:
            self.update_logging_status("Processing error occurred")
            if self.logging_manager.app_logger:
                self.logging_manager.log_error(e, "process_files")
            messagebox.showerror("Error", f"An error occurred during processing: {e}")
        
        finally:
            # Re-enable process button and hide progress
            self.process_button.config(state='normal')
            self.root.after(2000, self.hide_progress_bar)  # Hide after 2 seconds
    
    def show_process_results(self, result: ProcessResult):
        """Display processing results to user with session log information."""
        # Build result message
        result_msg = f"Successfully processed {result.processed_count} files."
        
        if result.skipped_count > 0:
            result_msg += f"\nSkipped {result.skipped_count} files."
        
        if result.errors:
            result_msg += f"\n\nErrors ({len(result.errors)}):"
            # Enhanced error reporting with detailed messages and suggestions
            error_categories = self._categorize_errors(result.errors)
            
            for category, errors in error_categories.items():
                if errors:
                    result_msg += f"\n\n{category}:"
                    for error in errors[:3]:  # Show first 3 per category
                        result_msg += f"\n• {error}"
                    if len(errors) > 3:
                        result_msg += f"\n... and {len(errors) - 3} more {category.lower()}"
            
            # Add suggestions for common error types
            suggestions = self._get_error_suggestions(error_categories)
            if suggestions:
                result_msg += f"\n\nSuggestions:"
                for suggestion in suggestions:
                    result_msg += f"\n• {suggestion}"
        
        # Add session log information
        session_summary = self.logging_manager.get_session_summary()
        if session_summary.get("total_operations", 0) > 0:
            result_msg += f"\n\nSession Log Summary:"
            result_msg += f"\nTotal operations logged: {session_summary['total_operations']}"
            
            # Show operation counts if available
            if "operation_counts" in session_summary:
                for op_type, count in session_summary["operation_counts"].items():
                    result_msg += f"\n• {op_type}: {count}"
        
        # Show detailed operation log if available
        if hasattr(result, 'operation_logs') and result.operation_logs:
            self._show_detailed_results_window(result)
        else:
            # Choose appropriate message box type
            if result.processed_count > 0:
                messagebox.showinfo("Process Complete", result_msg)
            else:
                messagebox.showwarning("Process Complete", result_msg)
    
    def _categorize_errors(self, errors: list) -> dict:
        """
        Categorize errors by type for better user understanding.
        
        Args:
            errors: List of error messages
            
        Returns:
            Dictionary of categorized errors
        """
        categories = {
            "Permission Errors": [],
            "File Not Found": [],
            "Network Errors": [],
            "Format Errors": [],
            "Other Errors": []
        }
        
        for error in errors:
            error_lower = error.lower()
            if "permission" in error_lower or "access" in error_lower:
                categories["Permission Errors"].append(error)
            elif "not found" in error_lower or "does not exist" in error_lower:
                categories["File Not Found"].append(error)
            elif "network" in error_lower or "timeout" in error_lower or "connection" in error_lower:
                categories["Network Errors"].append(error)
            elif "format" in error_lower or "invalid" in error_lower:
                categories["Format Errors"].append(error)
            else:
                categories["Other Errors"].append(error)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _get_error_suggestions(self, error_categories: dict) -> list:
        """
        Get suggestions based on error categories.
        
        Args:
            error_categories: Dictionary of categorized errors
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        if "Permission Errors" in error_categories:
            suggestions.append("Try running the application as administrator or check file permissions")
        
        if "File Not Found" in error_categories:
            suggestions.append("Verify that all files still exist in the selected folder")
        
        if "Network Errors" in error_categories:
            suggestions.append("Check your internet connection for GPS city lookup functionality")
        
        if "Format Errors" in error_categories:
            suggestions.append("Review your filename format pattern for invalid characters or syntax")
        
        if len(error_categories) > 2:
            suggestions.append("Consider processing files in smaller batches to isolate issues")
        
        return suggestions
    
    def show_progress_bar(self):
        """Show the progress bar for long-running operations."""
        self.progress_bar.grid()
        self.progress_bar['value'] = 0
    
    def hide_progress_bar(self):
        """Hide the progress bar."""
        self.progress_bar.grid_remove()
        self.status_label.config(text="")
    
    def update_progress(self, percent: float, message: str = ""):
        """
        Update progress bar and status message.
        
        Args:
            percent: Progress percentage (0-100)
            message: Status message to display
        """
        self.progress_bar['value'] = percent
        if message:
            self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def update_logging_status(self, status: str):
        """
        Update the logging status indicator while preserving cache status.
        
        Args:
            status: Status message to display
        """
        current_text = self.logging_status_label.cget("text")
        
        # Extract cache status if present
        cache_status = ""
        if " | Cache:" in current_text:
            parts = current_text.split(" | ")
            cache_parts = [part for part in parts if part.startswith("Cache:")]
            if cache_parts:
                cache_status = f" | {cache_parts[0]}"
        
        # Update with new logging status and preserve cache status
        new_text = f"Logging: {status}{cache_status}"
        self.logging_status_label.config(text=new_text)
        self.root.update_idletasks()
    
    def _show_detailed_results_window(self, result: ProcessResult):
        """
        Show detailed results window with session log information.
        
        Args:
            result: ProcessResult containing operation logs
        """
        # Create results window
        results_window = tk.Toplevel(self.root)
        results_window.title("Processing Results - Session Log")
        results_window.geometry("800x600")
        results_window.transient(self.root)
        results_window.grab_set()
        
        # Create main frame
        main_frame = ttk.Frame(results_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Summary section
        summary_frame = ttk.LabelFrame(main_frame, text="Summary", padding="10")
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        summary_text = (f"Successfully processed: {result.processed_count} files\n"
                       f"Skipped: {result.skipped_count} files\n"
                       f"Errors: {result.error_count} files")
        
        ttk.Label(summary_frame, text=summary_text).pack(anchor=tk.W)
        
        # Session log section
        log_frame = ttk.LabelFrame(main_frame, text="Session Log Details", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create treeview for operation logs
        columns = ('Time', 'Original Name', 'Final Name', 'Status', 'Message')
        log_tree = ttk.Treeview(log_frame, columns=columns, show='headings', height=15)
        
        # Configure column headings and widths
        log_tree.heading('Time', text='Time')
        log_tree.heading('Original Name', text='Original Name')
        log_tree.heading('Final Name', text='Final Name')
        log_tree.heading('Status', text='Status')
        log_tree.heading('Message', text='Message')
        
        log_tree.column('Time', width=120)
        log_tree.column('Original Name', width=200)
        log_tree.column('Final Name', width=200)
        log_tree.column('Status', width=80)
        log_tree.column('Message', width=200)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_tree.yview)
        h_scrollbar = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=log_tree.xview)
        log_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout for treeview and scrollbars
        log_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Populate the treeview with operation logs
        for log_entry in result.operation_logs:
            # Format timestamp for display
            time_display = log_entry.timestamp.split()[1] if log_entry.timestamp else ""
            
            # Determine status color tags
            status_tag = ""
            if log_entry.status == "success":
                status_tag = "success"
            elif log_entry.status == "error":
                status_tag = "error"
            elif log_entry.status == "skipped":
                status_tag = "warning"
            
            log_tree.insert('', 'end', values=(
                time_display,
                log_entry.original_name,
                log_entry.final_name,
                log_entry.status.upper(),
                log_entry.error_message or ""
            ), tags=(status_tag,))
        
        # Configure tags for status colors
        log_tree.tag_configure("success", foreground="green")
        log_tree.tag_configure("error", foreground="red")
        log_tree.tag_configure("warning", foreground="orange")
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Export session log button
        def export_session_log():
            try:
                session_log_path = self.logging_manager.save_session_log()
                if session_log_path:
                    messagebox.showinfo("Export Complete", 
                                      f"Session log saved to:\n{session_log_path}")
                else:
                    messagebox.showerror("Export Failed", 
                                       "Failed to save session log file.")
            except Exception as e:
                messagebox.showerror("Export Error", 
                                   f"Error saving session log: {e}")
        
        ttk.Button(button_frame, text="Export Session Log", 
                  command=export_session_log).pack(side=tk.LEFT, padx=(0, 10))
        
        # Close button
        ttk.Button(button_frame, text="Close", 
                  command=results_window.destroy).pack(side=tk.RIGHT)
    
    def load_city_cache(self):
        """Load city cache from file on application startup."""
        try:
            if self.city_cache.load_cache():
                stats = self.city_cache.get_cache_stats()
                if self.app_logger:
                    self.app_logger.info(f"City cache loaded successfully: {stats['total_entries']} entries")
                self.update_cache_status(f"Cache loaded: {stats['total_entries']} entries")
            else:
                if self.app_logger:
                    self.app_logger.warning("Failed to load city cache, starting with empty cache")
                self.update_cache_status("Cache: Empty (new)")
        except Exception as e:
            if self.app_logger:
                self.app_logger.error(f"Error loading city cache: {e}")
            self.update_cache_status("Cache: Error loading")
    
    def save_city_cache(self):
        """Save city cache to file on application shutdown."""
        try:
            if self.city_cache.save_cache():
                stats = self.city_cache.get_cache_stats()
                if self.app_logger:
                    self.app_logger.info(f"City cache saved successfully: {stats['total_entries']} entries")
            else:
                if self.app_logger:
                    self.app_logger.warning("Failed to save city cache")
        except Exception as e:
            if self.app_logger:
                self.app_logger.error(f"Error saving city cache: {e}")
    
    def update_cache_status(self, status_text: str = None):
        """
        Update cache status display in GUI with enhanced statistics.
        
        Args:
            status_text: Optional custom status text, otherwise generates from cache stats
        """
        # Generate detailed cache status if not provided
        if status_text is None:
            try:
                stats = self.city_cache.get_cache_stats()
                total = stats.get('total_entries', 0)
                hits = stats.get('cache_hits', 0)
                misses = stats.get('cache_misses', 0)
                
                if total > 0:
                    hit_rate = (hits / (hits + misses)) * 100 if (hits + misses) > 0 else 0
                    status_text = f"Cache: {total} entries ({hit_rate:.1f}% hit rate)"
                else:
                    status_text = "Cache: Empty"
            except Exception as e:
                status_text = "Cache: Error"
                if self.app_logger:
                    self.app_logger.warning(f"Error getting cache stats: {e}")
        
        # Store cache status for later use if GUI not ready
        self._cache_status = status_text
        
        # Update GUI if logging status label exists
        if hasattr(self, 'logging_status_label'):
            current_text = self.logging_status_label.cget("text")
            if "Cache:" in current_text:
                # Replace existing cache status
                parts = current_text.split(" | ")
                non_cache_parts = [part for part in parts if not part.startswith("Cache:")]
                non_cache_parts.append(status_text)
                new_text = " | ".join(non_cache_parts)
            else:
                # Add cache status
                if current_text:
                    new_text = f"{current_text} | {status_text}"
                else:
                    new_text = status_text
            
            self.logging_status_label.config(text=new_text)
    
    def get_cache_statistics(self) -> dict:
        """Get current cache statistics for display."""
        return self.city_cache.get_cache_stats()
    
    def show_detailed_status(self, event=None):
        """Show detailed cache and logging statistics in a popup window."""
        try:
            # Create status window
            status_window = tk.Toplevel(self.root)
            status_window.title("System Status - Cache & Logging Statistics")
            status_window.geometry("500x400")
            status_window.transient(self.root)
            status_window.grab_set()
            
            # Center the window
            center_window(status_window, 500, 400)
            
            # Create main frame
            main_frame = ttk.Frame(status_window, padding="15")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Cache statistics section
            cache_frame = ttk.LabelFrame(main_frame, text="City Cache Statistics", padding="10")
            cache_frame.pack(fill=tk.X, pady=(0, 10))
            
            try:
                cache_stats = self.city_cache.get_cache_stats()
                cache_info = f"""Total Entries: {cache_stats.get('total_entries', 0)}
Cache Hits: {cache_stats.get('cache_hits', 0)}
Cache Misses: {cache_stats.get('cache_misses', 0)}
Cache File Size: {cache_stats.get('file_size_kb', 0):.1f} KB
Last Updated: {cache_stats.get('last_updated', 'Never')}
Max Entries: {cache_stats.get('max_entries', 1000)}"""
                
                if cache_stats.get('cache_hits', 0) + cache_stats.get('cache_misses', 0) > 0:
                    hit_rate = (cache_stats.get('cache_hits', 0) / 
                              (cache_stats.get('cache_hits', 0) + cache_stats.get('cache_misses', 0))) * 100
                    cache_info += f"\nHit Rate: {hit_rate:.1f}%"
                
            except Exception as e:
                cache_info = f"Error retrieving cache statistics: {e}"
            
            ttk.Label(cache_frame, text=cache_info, justify=tk.LEFT).pack(anchor=tk.W)
            
            # Logging statistics section
            logging_frame = ttk.LabelFrame(main_frame, text="Logging Status", padding="10")
            logging_frame.pack(fill=tk.X, pady=(0, 10))
            
            try:
                logging_info = f"""Application Logger: {'Active' if self.app_logger else 'Inactive'}
Session Logger: {'Active' if self.logging_manager.session_logger else 'Inactive'}
Log Directory: {os.path.abspath('logs') if os.path.exists('logs') else 'Not created'}
Current Session Operations: {len(getattr(self.logging_manager, 'session_operations', []))}"""
                
                # Add recent log files info
                if os.path.exists('logs'):
                    log_files = [f for f in os.listdir('logs') if f.endswith('.log')]
                    logging_info += f"\nRecent Log Files: {len(log_files)}"
                
            except Exception as e:
                logging_info = f"Error retrieving logging statistics: {e}"
            
            ttk.Label(logging_frame, text=logging_info, justify=tk.LEFT).pack(anchor=tk.W)
            
            # Actions section
            actions_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
            actions_frame.pack(fill=tk.X, pady=(0, 10))
            
            button_frame = ttk.Frame(actions_frame)
            button_frame.pack(fill=tk.X)
            
            # Clear cache button
            def clear_cache():
                if messagebox.askyesno("Clear Cache", "Are you sure you want to clear the city cache?"):
                    try:
                        self.city_cache.clear_cache()
                        self.update_cache_status("Cache: Cleared")
                        messagebox.showinfo("Cache Cleared", "City cache has been cleared successfully.")
                        status_window.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to clear cache: {e}")
            
            ttk.Button(button_frame, text="Clear Cache", command=clear_cache).pack(side=tk.LEFT, padx=(0, 10))
            
            # Open logs folder button
            def open_logs_folder():
                try:
                    logs_path = os.path.abspath('logs')
                    if os.path.exists(logs_path):
                        os.startfile(logs_path)  # Windows
                    else:
                        messagebox.showinfo("Logs Folder", f"Logs folder not found at: {logs_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open logs folder: {e}")
            
            ttk.Button(button_frame, text="Open Logs Folder", command=open_logs_folder).pack(side=tk.LEFT, padx=(0, 10))
            
            # Close button
            ttk.Button(button_frame, text="Close", command=status_window.destroy).pack(side=tk.RIGHT)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show detailed status: {e}")
    
    def on_closing(self):
        """Handle application closing event."""
        if self.app_logger:
            self.app_logger.info("User initiated application shutdown")
        
        # Save current window geometry
        current_geometry = self.root.geometry()
        self.settings_manager.set("window_geometry", current_geometry)
        
        if self.app_logger:
            self.app_logger.debug(f"Saving window geometry: {current_geometry}")
        
        try:
            if self.settings_manager.save_settings():
                if self.app_logger:
                    self.app_logger.info("Settings saved on application close")
            else:
                if self.app_logger:
                    self.app_logger.warning("Failed to save settings on application close")
        except Exception as e:
            if self.app_logger:
                self.app_logger.error(f"Error saving settings on close: {e}")
        
        # Save city cache on shutdown
        self.save_city_cache()
        
        # Cleanup logging
        try:
            if self.logging_manager.session_logger:
                session_log_path = self.logging_manager.save_session_log()
                if self.app_logger and session_log_path:
                    self.app_logger.info(f"Final session log saved: {session_log_path}")
            
            if self.app_logger:
                self.app_logger.info("Application shutdown completed")
        except Exception as e:
            print(f"Error during logging cleanup: {e}")
        
        # Close application
        self.root.destroy()
    
    def run(self):
        """Start the GUI application main loop."""
        self.root.mainloop()


# Additional utility functions for GUI enhancements
def center_window(window, width: int, height: int):
    """Center a window on the screen."""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    window.geometry(f"{width}x{height}+{x}+{y}")


def create_tooltip(widget, text: str):
    """Create a simple tooltip for a widget."""
    def on_enter(event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
        
        label = tk.Label(tooltip, text=text, background="lightyellow", 
                        relief="solid", borderwidth=1, font=("Arial", 8))
        label.pack()
        
        widget.tooltip = tooltip
    
    def on_leave(event):
        if hasattr(widget, 'tooltip'):
            widget.tooltip.destroy()
            del widget.tooltip
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)