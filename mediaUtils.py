import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener
import subprocess

class MediaRenamerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Media File Renamer")
        self.root.geometry("800x600")
        
        # Register HEIF opener for Pillow
        register_heif_opener()
        
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif'}
        #self.image_extensions = {'.jpg333'}
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        
        # Default settings
        self.settings = {
            "folder_path": "c:\\",
            "filename_format": "%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}"
        }
        
        self.settings_file = "settings.json"
        self.load_settings()
        self.create_widgets()
        
    def create_widgets(self):
        # Folder selection frame
        folder_frame = ttk.Frame(self.root, padding="10")
        folder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(folder_frame, text="Folder Path:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.folder_var = tk.StringVar(value=self.settings["folder_path"])
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=50)
        folder_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).grid(row=1, column=1)
        
        # Format frame
        format_frame = ttk.Frame(self.root, padding="10")
        format_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(format_frame, text="Filename Format:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.format_var = tk.StringVar(value=self.settings["filename_format"])
        format_entry = ttk.Entry(format_frame, textvariable=self.format_var, width=60)
        format_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Example label
        self.example_label = ttk.Label(format_frame, foreground="gray")
        self.example_label.grid(row=2, column=0, sticky=tk.W)
        
        # Bind format change to update example
        self.format_var.trace('w', self.update_example)
        self.update_example()
        
        # Buttons frame
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=2, column=0)
        
        ttk.Button(button_frame, text="Save Settings", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Show Files", command=self.show_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Process Files", command=self.process_files).pack(side=tk.LEFT, padx=5)
        
        # Files frame
        files_frame = ttk.Frame(self.root, padding="10")
        files_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Stats and select all frame
        stats_frame = ttk.Frame(files_frame)
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.stats_label = ttk.Label(stats_frame, text="Total found: 0  Total Selected: 0")
        self.stats_label.pack(side=tk.LEFT)
        
        self.select_all_var = tk.BooleanVar()
        select_all_cb = ttk.Checkbutton(stats_frame, text="Select All", variable=self.select_all_var, command=self.toggle_all)
        select_all_cb.pack(side=tk.LEFT, padx=(20, 0))
        
        # Treeview for file list
        columns = ('Select', 'Current Name', 'New Name')
        self.tree = ttk.Treeview(files_frame, columns=columns, show='headings', height=15)
        
        self.tree.heading('Select', text='Select')
        self.tree.heading('Current Name', text='Current Name')
        self.tree.heading('New Name', text='New Name')
        
        self.tree.column('Select', width=60)
        self.tree.column('Current Name', width=300)
        self.tree.column('New Name', width=300)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)
        folder_frame.columnconfigure(0, weight=1)
        format_frame.columnconfigure(0, weight=1)
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(1, weight=1)
        
        # Bind single-click to toggle selection
        self.tree.bind('<Button-1>', self.on_click)
        
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)
            
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
        except Exception as e:
            messagebox.showwarning("Settings", f"Could not load settings: {e}")
            
    def save_settings(self):
        try:
            self.settings["folder_path"] = self.folder_var.get()
            self.settings["filename_format"] = self.format_var.get()
            
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
                
            messagebox.showinfo("Settings", "Settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {e}")
            
    def update_example(self, *args):
        try:
            format_str = self.format_var.get()
            sample_date = datetime(2024, 6, 30, 14, 32, 55)
            example = sample_date.strftime(format_str)
            example = example.replace("{increment:03d}", "001").replace("{ext}", "jpg")
            self.example_label.config(text=f"Example: {example}")
        except:
            self.example_label.config(text="Example: Invalid format")
        
    def show_files(self):
        folder_path = self.folder_var.get()
        if not os.path.exists(folder_path):
            messagebox.showerror("Error", "Selected folder does not exist.")
            return
            
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.select_all_var.set(False)
            
        try:
            files = [f for f in os.listdir(folder_path) 
                    if os.path.isfile(os.path.join(folder_path, f)) and 
                    os.path.splitext(f.lower())[1] in self.image_extensions | self.video_extensions]
            
            missing_metadata_count = 0
            for i, filename in enumerate(files, 1):
                filepath = os.path.join(folder_path, filename)
                new_name, has_metadata = self.generate_new_filename(filepath, i)
                if not has_metadata:
                    missing_metadata_count += 1
                self.tree.insert('', 'end', values=('☐', filename, new_name))
                
            self.update_stats(missing_metadata_count)
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not read folder: {e}")
            
    def generate_new_filename(self, filepath, increment):
        try:
            format_str = self.format_var.get()
            file_date, has_metadata = self.get_file_date(filepath)
            if not has_metadata:
                return "No metadata", False
            
            ext = os.path.splitext(filepath)[1][1:]  # Remove dot
            new_name = file_date.strftime(format_str)
            new_name = new_name.replace("{increment:03d}", f"{increment:03d}")
            new_name = new_name.replace("{ext}", ext)
            return new_name, True
        except Exception as e:
            return f"Error: {str(e)}", False
            
    def get_file_date(self, filepath):
        try:
            ext = os.path.splitext(filepath.lower())[1]
            
            # Handle images
            if ext in self.image_extensions:
                with Image.open(filepath) as img:
                    exif = img.getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == 'DateTimeOriginal':
                                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S'), True
                        
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == 'DateTimeDigitized':
                                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S'), True
                        
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == 'DateTime':
                                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S'), True
            
            # Handle videos using local or system ffprobe
            elif ext in self.video_extensions:
                # Try local ffprobe.exe first, then system PATH
                ffprobe_paths = [
                    os.path.join(os.path.dirname(__file__), 'ffprobe.exe'),  # Local
                    'ffprobe'  # System PATH
                ]
                
                for ffprobe_path in ffprobe_paths:
                    try:
                        for field in ['creation_time', 'date']:
                            result = subprocess.run([
                                ffprobe_path, '-v', 'quiet', '-show_entries', f'format_tags={field}',
                                '-of', 'csv=p=0', filepath
                            ], capture_output=True, text=True, timeout=10)
                            
                            if result.returncode == 0 and result.stdout.strip():
                                date_str = result.stdout.strip()
                                for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ']:
                                    try:
                                        return datetime.strptime(date_str, fmt), True
                                    except:
                                        continue
                        break  # If ffprobe worked, don't try other paths
                    except:
                        continue  # Try next ffprobe path
            
            return None, False
            
        except:
            return None, False
            
    def on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            if column == '#1':  # Select column
                values = list(self.tree.item(item, 'values'))
                values[0] = '☑' if values[0] == '☐' else '☐'
                self.tree.item(item, values=values)
                self.update_stats()
                
    def toggle_all(self):
        state = '☑' if self.select_all_var.get() else '☐'
        for item in self.tree.get_children():
            values = list(self.tree.item(item, 'values'))
            values[0] = state
            self.tree.item(item, values=values)
        self.update_stats()
        
    def update_stats(self, missing_metadata_count=0):
        total = len(self.tree.get_children())
        selected = sum(1 for item in self.tree.get_children() 
                      if self.tree.item(item, 'values')[0] == '☑')
        
        stats_text = f"Total found: {total}  Total Selected: {selected}"
        if missing_metadata_count > 0:
            stats_text += f"  Missing metadata: {missing_metadata_count}"
        
        self.stats_label.config(text=stats_text)
        
        # Update select all checkbox state
        if selected == 0:
            self.select_all_var.set(False)
        elif selected == total:
            self.select_all_var.set(True)
            
    def process_files(self):
        # Placeholder for file processing
        messagebox.showinfo("Process Files", "File processing functionality will be implemented next.")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MediaRenamerGUI()
    app.run()