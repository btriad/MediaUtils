# Media File Renamer - GUI Application for renaming media files based on EXIF metadata
# Supports images (JPG, JPEG, PNG, HEIC, etc.) and videos (MP4, MOV, AVI, etc.)
# Features: Date/time extraction, GPS location extraction, city name lookup, custom filename formats

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from datetime import datetime
from PIL import Image  # For image processing and EXIF data extraction
from PIL.ExifTags import TAGS  # For EXIF tag name mapping
from pillow_heif import register_heif_opener  # For HEIC/HEIF image support
import subprocess  # For running ffprobe to extract video metadata

class MediaRenamerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Media File Renamer")
        self.root.geometry("1200x600")
        
        # Register HEIF opener for Pillow
        register_heif_opener()
        
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif'}
        #self.image_extensions = {'.jp4g'}
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
        self.process_button = ttk.Button(button_frame, text="Process Files", command=self.process_files)
        self.process_button.pack(side=tk.LEFT, padx=5)
        
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
        columns = ('Select', 'Current Name', 'New Name', 'Location', 'City')
        self.tree = ttk.Treeview(files_frame, columns=columns, show='headings', height=15)
        
        self.tree.heading('Select', text='Select')
        self.tree.heading('Current Name', text='Current Name')
        self.tree.heading('New Name', text='New Name')
        self.tree.heading('Location', text='Location')
        self.tree.heading('City', text='City')
        
        self.tree.column('Select', width=60)
        self.tree.column('Current Name', width=200)
        self.tree.column('New Name', width=200)
        self.tree.column('Location', width=150)
        self.tree.column('City', width=150)
        
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
        
        # Status label for loading indicator
        self.status_label = ttk.Label(files_frame, text="", foreground="blue")
        self.status_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        
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
            example = example.replace("{increment:03d}", "001").replace("{city}", "NeoPsihiko").replace("{ext}", "jpg")
            self.example_label.config(text=f"Example: {example}")
        except:
            self.example_label.config(text="Example: Invalid format")
        
    def show_files(self):
        folder_path = self.folder_var.get()
        if not os.path.exists(folder_path):
            messagebox.showerror("Error", "Selected folder does not exist.")
            return
            
        # Show loading message
        self.status_label.config(text="Working... Reading files...")
        self.root.update()
            
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
                location, city = self.get_location_and_city(filepath)
                self.tree.insert('', 'end', values=('☐', filename, new_name, location, city))
                
                # Update progress
                self.status_label.config(text=f"Working... Processing {i}/{len(files)} files...")
                self.root.update()
                
            self.update_stats(missing_metadata_count)
            self.status_label.config(text="")
                
        except Exception as e:
            self.status_label.config(text="")
            messagebox.showerror("Error", f"Could not read folder: {e}")
            
    def generate_new_filename(self, filepath, increment):
        try:
            format_str = self.format_var.get()
            file_date, has_metadata = self.get_file_date(filepath)
            
            if not has_metadata:
                return "No metadata", False
            
            ext = os.path.splitext(filepath)[1][1:]  # Remove dot
            location, city = self.get_location_and_city(filepath)
            city_formatted = city.replace(' ', '') if city else ''
            
            new_name = file_date.strftime(format_str)
            new_name = new_name.replace("{increment:03d}", f"{increment:03d}")
            new_name = new_name.replace("{city}", city_formatted)
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
            
    def get_location_and_city(self, filepath):
        try:
            ext = os.path.splitext(filepath.lower())[1]
            

            
            if ext in self.image_extensions:
                with Image.open(filepath) as img:
                    exif = img.getexif()
                    if exif:
                        # Get GPS data - try both methods
                        gps_info = None
                        try:
                            gps_info = exif.get_ifd(0x8825)  # GPS IFD
                        except:
                            # Fallback: check if GPS data is directly in EXIF
                            for tag_id, value in exif.items():
                                tag = TAGS.get(tag_id, tag_id)
                                if tag == 'GPSInfo':
                                    gps_info = value
                                    break
                        
                        if gps_info and isinstance(gps_info, dict):
                            lat = self.get_gps_coordinate(gps_info, 2, 1)  # Latitude
                            lon = self.get_gps_coordinate(gps_info, 4, 3)  # Longitude
                            if lat is not None and lon is not None:
                                location = f"{lat:.4f}, {lon:.4f}"
                                city = self.get_city_from_coords(lat, lon)
                                return location, city
            elif ext in self.video_extensions:
                ffprobe_paths = [
                    os.path.join(os.path.dirname(__file__), 'ffprobe.exe'),
                    'ffprobe'
                ]
                
                for ffprobe_path in ffprobe_paths:
                    try:
                        # Get format tags which contain GPS data
                        result = subprocess.run([
                            ffprobe_path, '-v', 'quiet', '-show_entries', 'format_tags',
                            '-of', 'csv=p=0', filepath
                        ], capture_output=True, text=True, timeout=10)
                        
                        if result.returncode == 0:
                            output = result.stdout.strip()
                            
                            # Look for GPS pattern like +38.0150+023.8204+214.199005/
                            import re
                            gps_match = re.search(r'([+-]\d+\.\d+)([+-]\d+\.\d+)', output)
                            if gps_match:
                                lat = float(gps_match.group(1))
                                lon = float(gps_match.group(2))
                                location = f"{lat:.4f}, {lon:.4f}"
                                city = self.get_city_from_coords(lat, lon)
                                return location, city

                        break
                    except Exception as e:
                        continue
            return "No GPS", ""
        except Exception as e:
            return "No GPS", ""
            
    def get_city_from_coords(self, lat, lon):
        try:
            import urllib.request
            import urllib.parse
            
            # Use OpenStreetMap Nominatim API for reverse geocoding in English
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1&accept-language=en"
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'MediaRenamer/1.0')
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
            address = data.get('address', {})
            
            # Get friendly city name in priority order
            city = (address.get('city') or 
                   address.get('town') or 
                   address.get('village') or 
                   address.get('municipality'))
            
            # Clean up Greek municipal names
            if city:
                city = self.clean_city_name(city)
            
            return city or address.get('county', '')
        except:
            return ""
            
    def clean_city_name(self, city_name):
        # Remove redundant prefixes and get clean city names
        cleanups = {
            'Δημοτική Κοινότητα Καρλοβασίου': 'Karlovasi',
            'Capital city of ': '',
            'City of ': '',
            'Δημοτική Κοινότητα': '',
            'Δήμος': '',
            'Municipality of ': '',
            'Municipal Unit of ': ''
        }
        
        cleaned = city_name
        for prefix, replacement in cleanups.items():
            if cleaned.startswith(prefix):
                cleaned = cleaned.replace(prefix, replacement, 1).strip()
                
        return cleaned if cleaned else city_name
            
    def extract_gps_from_tags(self, tags):
        # Check various GPS tag names
        gps_tags = [
            'location', 'GPS', 'com.apple.quicktime.location.ISO6709',
            'com.apple.quicktime.GPS', 'gpslocation', 'coordinates',
            'latitude', 'longitude', 'gps_coordinates'
        ]
        
        for tag_name in gps_tags:
            for key, value in tags.items():
                if tag_name.lower() in key.lower() and value:
                    lat, lon = self.parse_video_gps(str(value))
                    if lat is not None and lon is not None:
                        return lat, lon
        
        # Check for separate lat/lon tags
        lat_val = None
        lon_val = None
        for key, value in tags.items():
            key_lower = key.lower()
            if 'lat' in key_lower and value:
                try:
                    lat_val = float(value)
                except:
                    pass
            elif 'lon' in key_lower and value:
                try:
                    lon_val = float(value)
                except:
                    pass
        
        if lat_val is not None and lon_val is not None:
            return lat_val, lon_val
            
        return None, None
        
    def parse_video_gps(self, location_str):
        try:
            # Handle ISO 6709 format: +37.9755-023.7348/ or +37.9755-023.7348+123.456/
            if '+' in location_str and '-' in location_str:
                location_str = location_str.replace('/', '')
                # Split on the second occurrence of + or -
                import re
                match = re.match(r'([+-]?\d+\.\d+)([+-]\d+\.\d+)', location_str)
                if match:
                    lat = float(match.group(1))
                    lon = float(match.group(2))
                    return lat, lon
            
            # Handle comma-separated format: "37.9755, -23.7348"
            if ',' in location_str:
                parts = location_str.split(',')
                if len(parts) >= 2:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    return lat, lon
                    
            return None, None
        except:
            return None, None
            
    def get_gps_coordinate(self, gps_info, coord_key, ref_key):
        try:
            # Check if gps_info is a dictionary
            if not isinstance(gps_info, dict):
                return None
                
            coord = gps_info.get(coord_key)
            ref = gps_info.get(ref_key)
            if coord and ref:
                # Handle different coordinate formats
                if isinstance(coord, (list, tuple)) and len(coord) >= 3:
                    degrees = float(coord[0])
                    minutes = float(coord[1]) if coord[1] else 0
                    seconds = float(coord[2]) if coord[2] else 0
                    decimal = degrees + minutes/60 + seconds/3600
                    if ref in ['S', 'W']:
                        decimal = -decimal
                    return decimal
        except Exception as e:
            print(f"GPS coordinate error: {e}")  # Debug
            pass
        return None
            
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
        # Get selected files
        selected_files = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values[0] == '☑':
                selected_files.append((values[1], values[2]))  # (current_name, new_name)
        
        if not selected_files:
            messagebox.showwarning("Warning", "No files selected for processing.")
            return
            
        # Show loading message and disable button
        self.status_label.config(text="Working... Processing files...")
        self.process_button.config(state='disabled')
        self.root.update()
        
        try:
            folder_path = self.folder_var.get()
            processed_count = 0
            errors = []
            
            for i, (current_name, new_name) in enumerate(selected_files, 1):
                if new_name.startswith("Error:"):
                    errors.append(f"{current_name}: {new_name}")
                    continue
                    
                try:
                    current_path = os.path.join(folder_path, current_name)
                    
                    # Handle files with no metadata - add underscore prefix
                    if new_name == "No metadata":
                        if current_name.startswith('_'):
                            errors.append(f"{current_name}: Already has underscore prefix")
                            continue
                        new_path = os.path.join(folder_path, f"_{current_name}")
                    else:
                        new_path = os.path.join(folder_path, new_name)
                    
                    # Check if target file already exists
                    if os.path.exists(new_path):
                        errors.append(f"{current_name}: Target file already exists")
                        continue
                        
                    os.rename(current_path, new_path)
                    processed_count += 1
                    
                    # Update progress
                    self.status_label.config(text=f"Working... Processing {i}/{len(selected_files)} files...")
                    self.root.update()
                    
                except Exception as e:
                    errors.append(f"{current_name}: {str(e)}")
            
            # Show results
            result_msg = f"Successfully processed {processed_count} files."
            if errors:
                result_msg += f"\n\nErrors ({len(errors)}):"[:200]  # Limit message length
                for error in errors[:5]:  # Show first 5 errors
                    result_msg += f"\n• {error}"
                if len(errors) > 5:
                    result_msg += f"\n... and {len(errors) - 5} more errors"
            
            if processed_count > 0:
                messagebox.showinfo("Process Complete", result_msg)
                # Refresh the file list
                self.show_files()
            else:
                messagebox.showwarning("Process Complete", result_msg)
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during processing: {e}")
        finally:
            # Clear loading message and re-enable button
            self.status_label.config(text="")
            self.process_button.config(state='normal')
            self.root.update()
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MediaRenamerGUI()
    app.run()