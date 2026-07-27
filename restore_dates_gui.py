#!/usr/bin/env python3
"""
EXIF Date Restorer - GUI

Select a folder; the app scans it (and all sub-folders, recursively) for JPEG
files, reads the capture date/time from each filename and writes it into the
EXIF metadata - but only for files that do not already have an EXIF date.

Run:
    python restore_dates_gui.py
"""

import os
import logging
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from exif_date_restorer import (
    scan_folder,
    apply_dates,
    FileStatus,
    ScanResult,
)

# Row colours per status.
_STATUS_COLOR = {
    FileStatus.READY: "#1a7f37",     # green
    FileStatus.HAS_EXIF: "#6e7781",  # gray
    FileStatus.NO_DATE: "#bf8700",   # amber
    FileStatus.ERROR: "#cf222e",     # red
}


def _setup_logger() -> logging.Logger:
    """Create a logger that writes to logs/restore_dates_<timestamp>.log."""
    logger = logging.getLogger("exif_date_restorer.gui")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    try:
        logs_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        handler = logging.FileHandler(
            os.path.join(logs_dir, f"restore_dates_{stamp}.log"), encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    except Exception as e:
        print(f"Warning: file logging unavailable: {e}")
    return logger


class RestoreDatesGUI:
    """Tkinter GUI for restoring EXIF dates from filenames."""

    def __init__(self):
        self.logger = _setup_logger()
        self.results: list[ScanResult] = []
        self._busy = False

        self.root = tk.Tk()
        self.root.title("EXIF Date Restorer - from filename")
        self.root.geometry("880x620")
        self.root.minsize(760, 520)

        self.folder_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Select a folder and press Scan.")

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}

        # --- Folder selection row ---
        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="Folder:").pack(side="left")
        ttk.Entry(top, textvariable=self.folder_var).pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="Browse...", command=self._browse).pack(side="left")

        # --- Options + actions row ---
        opts = ttk.Frame(self.root)
        opts.pack(fill="x", padx=8)

        ttk.Checkbutton(opts, text="Include sub-folders (recursive)",
                        variable=self.recursive_var).pack(side="left")
        self.scan_btn = ttk.Button(opts, text="Scan", command=self._scan)
        self.scan_btn.pack(side="left", padx=6)
        self.apply_btn = ttk.Button(opts, text="Write EXIF dates",
                                    command=self._apply, state="disabled")
        self.apply_btn.pack(side="left")

        # --- Results table ---
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, **pad)

        columns = ("filename", "newdate", "note")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("filename", text="File path")
        self.tree.heading("newdate", text="New EXIF date")
        self.tree.heading("note", text="Note")
        self.tree.column("filename", width=460, anchor="w")
        self.tree.column("newdate", width=170, anchor="w")
        self.tree.column("note", width=220, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal",
                            command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        for status, color in _STATUS_COLOR.items():
            self.tree.tag_configure(status.value, foreground=color)

        # --- Summary counters ---
        self.summary_var = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.summary_var).pack(
            anchor="w", padx=10)

        # --- Progress + status bar ---
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=8, pady=(4, 0))
        ttk.Label(self.root, textvariable=self.status_var,
                  relief="sunken", anchor="w").pack(fill="x", side="bottom")

    # -------------------------------------------------------------- actions
    def _browse(self):
        folder = filedialog.askdirectory(title="Select folder with JPEG files")
        if folder:
            self.folder_var.set(folder)

    def _set_busy(self, busy: bool):
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.scan_btn.configure(state=state)
        # Apply is only enabled when there are files ready to write.
        if busy:
            self.apply_btn.configure(state="disabled")

    def _scan(self):
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Invalid folder",
                                 "Please select an existing folder.")
            return

        self._set_busy(True)
        self.status_var.set("Scanning...")
        self.tree.delete(*self.tree.get_children())
        self.summary_var.set("")
        recursive = self.recursive_var.get()

        def worker():
            try:
                results = scan_folder(folder, recursive=recursive,
                                      logger=self.logger)
            except Exception as e:
                self.logger.error(f"Scan failed: {e}")
                self.root.after(0, lambda: self._scan_failed(e))
                return
            self.root.after(0, lambda: self._scan_done(results))

        threading.Thread(target=worker, daemon=True).start()

    def _scan_failed(self, error: Exception):
        self._set_busy(False)
        self.status_var.set("Scan failed.")
        messagebox.showerror("Scan failed", str(error))

    def _scan_done(self, results: list[ScanResult]):
        self.results = results
        counts = {s: 0 for s in FileStatus}
        for r in results:
            counts[r.status] += 1

        # Show ONLY files that do not already have an EXIF date.
        # Files with existing EXIF are hidden (and never modified).
        shown = [r for r in results if r.status != FileStatus.HAS_EXIF]
        for r in shown:
            new_date = (r.parsed_datetime.strftime("%Y:%m:%d %H:%M:%S")
                        if r.status == FileStatus.READY and r.parsed_datetime
                        else "—")  # em dash when nothing will be written
            self.tree.insert(
                "", "end",
                values=(r.path, new_date, r.message),
                tags=(r.status.value,))

        self.summary_var.set(
            f"Without EXIF (shown): {len(shown)}   |   "
            f"Ready to convert: {counts[FileStatus.READY]}   |   "
            f"No date in name: {counts[FileStatus.NO_DATE]}   |   "
            f"Errors: {counts[FileStatus.ERROR]}   |   "
            f"Already have EXIF (hidden): {counts[FileStatus.HAS_EXIF]}")

        ready = counts[FileStatus.READY]
        self._set_busy(False)
        self.apply_btn.configure(state="normal" if ready else "disabled")
        self.status_var.set(
            f"Scan complete. {ready} file(s) ready to convert."
            if ready else "Scan complete. Nothing to convert.")

    def _apply(self):
        ready = [r for r in self.results if r.status == FileStatus.READY]
        if not ready:
            return
        if not messagebox.askyesno(
                "Confirm",
                f"Write EXIF dates into {len(ready)} JPEG file(s)?\n\n"
                "Only files without an existing EXIF date are affected. "
                "This modifies the files in place."):
            return

        self._set_busy(True)
        self.progress.configure(maximum=len(ready), value=0)
        self.status_var.set("Writing EXIF dates...")

        def on_progress(i, total, r):
            self.root.after(0, lambda: self._on_progress(i, total))

        def worker():
            written, errors = apply_dates(
                self.results, logger=self.logger, progress=on_progress)
            self.root.after(0, lambda: self._apply_done(written, errors))

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress(self, i, total):
        self.progress.configure(value=i)
        self.status_var.set(f"Writing EXIF dates... {i}/{total}")

    def _apply_done(self, written: int, errors: int):
        self._set_busy(False)
        self.status_var.set(f"Done. {written} written, {errors} error(s).")
        messagebox.showinfo(
            "Finished",
            f"EXIF dates written: {written}\nErrors: {errors}")
        # Re-scan so the table reflects the new EXIF state.
        self._scan()

    def run(self):
        self.root.mainloop()


def main():
    RestoreDatesGUI().run()


if __name__ == "__main__":
    main()
