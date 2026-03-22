"""
Music Production File Organizer
================================
Automatically organizes mixed music production files into structured project folders.

Features:
- Scans a directory for music production files
- Groups files by track/project based on filename patterns
- Classifies files into subfolders (Source, Prompts, Making, Cover, Mastering, Final, Working)
- Tkinter GUI with folder picker, preview, and confirmation
- CSV move log for all operations
- Optional backup before execution
- No file deletion — move only with overwrite protection

Usage:
    python music_file_organizer.py
"""

import csv
import os
import re
import shutil
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUBFOLDERS = [
    "01_Source_Data",
    "02_Prompts",
    "03_Making_Process",
    "04_Design_Cover",
    "05_Mastering",
    "06_Final_Output",
    "07_Working_Files",
]

# Extension-based classification
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aif", ".aiff", ".ogg", ".m4a", ".aac"}
PROMPT_EXTENSIONS = {".txt", ".md", ".rtf", ".doc", ".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".svg", ".psd", ".ai"}
PROJECT_EXTENSIONS = {".als", ".flp", ".logicx", ".ptx", ".rpp", ".cpr", ".band", ".reason"}

# Keywords for classification refinement
FINAL_KEYWORDS = ["final", "release", "delivered", "finished", "completed", "approved"]
MASTER_KEYWORDS = ["master", "mastered", "mastering", "premaster", "pre-master", "loudness"]
DRAFT_KEYWORDS = ["draft", "demo", "wip", "work-in-progress", "sketch", "rough", "bounce", "render", "mix", "v1", "v2", "v3", "v4", "v5", "rev"]
COVER_KEYWORDS = ["cover", "artwork", "album", "sleeve", "booklet", "design", "thumbnail", "poster"]
PROMPT_KEYWORDS = ["prompt", "lyric", "lyrics", "notes", "reference", "brief", "description", "instruction"]

# Date patterns in filenames
DATE_PATTERNS = [
    (r"(\d{4})[-_.](\d{2})[-_.](\d{2})", "%Y-%m-%d"),   # 2024-01-15 or 2024_01_15
    (r"(\d{8})", "%Y%m%d"),                               # 20240115
    (r"(\d{2})[-_.](\d{2})[-_.](\d{4})", "%m-%d-%Y"),     # 01-15-2024
    (r"(\d{6})", "%y%m%d"),                                # 240115
]


# ---------------------------------------------------------------------------
# File Scanner & Classifier
# ---------------------------------------------------------------------------

def get_file_creation_date(filepath: str) -> datetime.date:
    """Return the file creation date (or modification date as fallback)."""
    stat = os.stat(filepath)
    # On Windows, st_ctime is creation time; on Unix it's metadata change time.
    timestamp = getattr(stat, "st_birthtime", None) or stat.st_ctime
    return datetime.date.fromtimestamp(timestamp)


def extract_date_from_filename(filename: str) -> Optional[datetime.date]:
    """Try to extract a date from the filename using known patterns."""
    name = os.path.splitext(filename)[0]

    # Try YYYYMMDD (8 digits) first — but only if it looks like a date
    match = re.search(r"(\d{4})([-_.]?)(\d{2})\2(\d{2})", name)
    if match:
        try:
            year, _, month, day = match.group(1), match.group(2), match.group(3), match.group(4)
            return datetime.date(int(year), int(month), int(day))
        except ValueError:
            pass

    # Try YYYYMMDD without separators
    match = re.search(r"(?<!\d)(\d{8})(?!\d)", name)
    if match:
        try:
            d = match.group(1)
            return datetime.date(int(d[:4]), int(d[4:6]), int(d[6:8]))
        except ValueError:
            pass

    # Try YYMMDD (6 digits)
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", name)
    if match:
        try:
            d = match.group(1)
            year = 2000 + int(d[:2])
            return datetime.date(year, int(d[2:4]), int(d[4:6]))
        except ValueError:
            pass

    return None


def extract_track_title(filename: str) -> str:
    """Infer a track title from the filename."""
    name = os.path.splitext(filename)[0]

    # Remove date-like patterns
    name = re.sub(r"\d{4}[-_.]?\d{2}[-_.]?\d{2}", "", name)
    name = re.sub(r"(?<!\d)\d{6}(?!\d)", "", name)

    # Remove common suffixes/prefixes
    noise = (
        FINAL_KEYWORDS + MASTER_KEYWORDS + DRAFT_KEYWORDS
        + COVER_KEYWORDS + PROMPT_KEYWORDS
        + ["v\\d+", "rev\\d+", "mix\\d+"]
    )
    for word in noise:
        name = re.sub(rf"[-_ ]*\b{word}\b[-_ ]*", " ", name, flags=re.IGNORECASE)

    # Clean up separators
    name = re.sub(r"[-_]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    if not name:
        name = "Untitled"

    # Title-case
    return name.title()


def classify_file(filename: str, extension: str) -> str:
    """
    Classify a file into one of the 7 subfolder categories.
    Returns the subfolder name.
    """
    ext = extension.lower()
    name_lower = filename.lower()

    # --- Project files → Working_Files ---
    if ext in PROJECT_EXTENSIONS:
        return "07_Working_Files"

    # --- Text files → Prompts ---
    if ext in PROMPT_EXTENSIONS:
        # Check if it's actually a prompt/lyric or something else
        if any(kw in name_lower for kw in PROMPT_KEYWORDS):
            return "02_Prompts"
        # Default text files to Prompts
        return "02_Prompts"

    # --- Image files → Design_Cover ---
    if ext in IMAGE_EXTENSIONS:
        return "04_Design_Cover"

    # --- Audio files: needs deeper analysis ---
    if ext in AUDIO_EXTENSIONS:
        # Check for final output keywords
        if any(kw in name_lower for kw in FINAL_KEYWORDS):
            return "06_Final_Output"
        # Check for mastering keywords
        if any(kw in name_lower for kw in MASTER_KEYWORDS):
            return "05_Mastering"
        # Check for draft/intermediate keywords
        if any(kw in name_lower for kw in DRAFT_KEYWORDS):
            return "03_Making_Process"
        # Default audio → Making_Process
        return "03_Making_Process"

    # --- Unknown → Source_Data ---
    return "01_Source_Data"


def group_files_by_track(file_list: list[dict]) -> dict[str, list[dict]]:
    """
    Group files by track/project.
    Returns dict mapping track_key → list of file_info dicts.

    Strategy:
    1. Extract a "base name" from each file (removing dates, version tags, category keywords).
    2. Group files with the same or very similar base names.
    3. If no clear grouping, fall back to date-based grouping.
    """
    # First pass: extract base names
    for f in file_list:
        f["track_title"] = extract_track_title(f["filename"])
        f["file_date"] = extract_date_from_filename(f["filename"]) or get_file_creation_date(f["filepath"])

    # Group by track title
    groups: dict[str, list[dict]] = {}
    for f in file_list:
        title = f["track_title"]
        if title not in groups:
            groups[title] = []
        groups[title].append(f)

    return groups


def build_folder_name(track_title: str, files: list[dict]) -> str:
    """Build the YYYYMMDD_TrackTitle folder name for a group of files."""
    # Pick the earliest date from the group
    dates = [f["file_date"] for f in files if f.get("file_date")]
    if dates:
        earliest = min(dates)
    else:
        earliest = datetime.date.today()

    date_str = earliest.strftime("%Y%m%d")

    # Clean title for folder name
    safe_title = re.sub(r'[<>:"/\\|?*]', "", track_title)
    safe_title = safe_title.strip()
    if not safe_title:
        safe_title = "Untitled"

    return f"{date_str}_{safe_title}"


def scan_directory(directory: str) -> list[dict]:
    """Scan a directory and return a list of file info dicts."""
    files = []
    for entry in os.scandir(directory):
        if entry.is_file():
            name = entry.name
            ext = os.path.splitext(name)[1]
            category = classify_file(name, ext)
            files.append({
                "filename": name,
                "filepath": entry.path,
                "extension": ext.lower(),
                "category": category,
                "size": entry.stat().st_size,
            })
    return files


def create_classification_plan(directory: str) -> dict:
    """
    Scan directory and create a full classification plan.
    Returns a dict with track groups and their file assignments.
    """
    files = scan_directory(directory)

    if not files:
        return {"tracks": {}, "source_dir": directory, "total_files": 0}

    groups = group_files_by_track(files)

    plan = {"tracks": {}, "source_dir": directory, "total_files": len(files)}

    for title, group_files in groups.items():
        folder_name = build_folder_name(title, group_files)
        plan["tracks"][folder_name] = []
        for f in group_files:
            plan["tracks"][folder_name].append({
                "filename": f["filename"],
                "filepath": f["filepath"],
                "category": f["category"],
                "extension": f["extension"],
                "size": f["size"],
            })

    return plan


# ---------------------------------------------------------------------------
# File Mover & Backup
# ---------------------------------------------------------------------------

def create_backup(source_dir: str, backup_dir: Optional[str] = None) -> str:
    """Create a backup copy of the source directory."""
    if backup_dir is None:
        parent = os.path.dirname(source_dir)
        dir_name = os.path.basename(source_dir)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(parent, f"{dir_name}_backup_{timestamp}")

    shutil.copytree(source_dir, backup_dir)
    return backup_dir


def execute_plan(plan: dict, log_path: Optional[str] = None) -> list[dict]:
    """
    Execute the classification plan: create folders and move files.
    Returns a list of move records for logging.
    """
    source_dir = plan["source_dir"]
    move_log = []

    for folder_name, files in plan["tracks"].items():
        # Create the project folder
        project_dir = os.path.join(source_dir, folder_name)
        os.makedirs(project_dir, exist_ok=True)

        # Create all subfolders
        for subfolder in SUBFOLDERS:
            os.makedirs(os.path.join(project_dir, subfolder), exist_ok=True)

        # Move files
        for f in files:
            src = f["filepath"]
            category = f["category"]
            dest_dir = os.path.join(project_dir, category)
            dest = os.path.join(dest_dir, f["filename"])

            # Handle overwrite protection
            if os.path.exists(dest):
                base, ext = os.path.splitext(f["filename"])
                counter = 1
                while os.path.exists(dest):
                    dest = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                    counter += 1

            # Only move if source still exists (safety check)
            if os.path.exists(src):
                shutil.move(src, dest)
                move_log.append({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "filename": f["filename"],
                    "source": src,
                    "destination": dest,
                    "category": category,
                    "project_folder": folder_name,
                })

    # Write log file
    if log_path is None:
        log_path = os.path.join(source_dir, "move_log.csv")

    write_move_log(move_log, log_path)

    return move_log


def write_move_log(move_log: list[dict], log_path: str) -> None:
    """Write the move log to a CSV file."""
    if not move_log:
        return

    fieldnames = ["timestamp", "filename", "source", "destination", "category", "project_folder"]
    with open(log_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for record in move_log:
            writer.writerow(record)


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------

class MusicFileOrganizerApp:
    """Main application GUI."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Music Production File Organizer")
        self.root.geometry("950x700")
        self.root.minsize(800, 600)

        self.source_dir: Optional[str] = None
        self.plan: Optional[dict] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the full UI layout."""
        # --- Top Frame: Directory Selection ---
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Source Directory:").pack(side=tk.LEFT)
        self.dir_var = tk.StringVar()
        dir_entry = ttk.Entry(top_frame, textvariable=self.dir_var, width=60)
        dir_entry.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        ttk.Button(top_frame, text="Browse...", command=self._browse_directory).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Scan", command=self._scan_directory).pack(side=tk.LEFT, padx=(5, 0))

        # --- Options Frame ---
        opts_frame = ttk.LabelFrame(self.root, text="Options", padding=10)
        opts_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text="Create backup before organizing", variable=self.backup_var).pack(
            side=tk.LEFT
        )

        # --- Preview Frame: Treeview ---
        preview_frame = ttk.LabelFrame(self.root, text="Classification Preview", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview with scrollbar
        tree_scroll_y = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL)
        tree_scroll_x = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(
            preview_frame,
            columns=("category", "extension", "size"),
            show="tree headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
        )
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)

        self.tree.heading("#0", text="File / Folder", anchor=tk.W)
        self.tree.heading("category", text="Category", anchor=tk.W)
        self.tree.heading("extension", text="Extension", anchor=tk.W)
        self.tree.heading("size", text="Size", anchor=tk.E)

        self.tree.column("#0", width=350, minwidth=200)
        self.tree.column("category", width=200, minwidth=100)
        self.tree.column("extension", width=80, minwidth=60)
        self.tree.column("size", width=100, minwidth=60, anchor=tk.E)

        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # --- Status bar ---
        self.status_var = tk.StringVar(value="Select a directory and click Scan to begin.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 5))

        # --- Bottom Frame: Action Buttons ---
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.execute_btn = ttk.Button(
            bottom_frame, text="Organize Files", command=self._execute, state=tk.DISABLED
        )
        self.execute_btn.pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(bottom_frame, text="Quit", command=self.root.quit).pack(side=tk.RIGHT)

    def _browse_directory(self) -> None:
        """Open a folder selection dialog."""
        directory = filedialog.askdirectory(title="Select directory with music files")
        if directory:
            self.dir_var.set(directory)

    def _scan_directory(self) -> None:
        """Scan the selected directory and show preview."""
        directory = self.dir_var.get().strip()
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("Error", "Please select a valid directory.")
            return

        self.source_dir = directory
        self.status_var.set("Scanning...")
        self.root.update_idletasks()

        self.plan = create_classification_plan(directory)

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        if self.plan["total_files"] == 0:
            self.status_var.set("No files found in the selected directory.")
            self.execute_btn.config(state=tk.DISABLED)
            return

        # Populate tree
        for folder_name, files in sorted(self.plan["tracks"].items()):
            folder_id = self.tree.insert(
                "", tk.END,
                text=f"\U0001F4C1 {folder_name}",
                values=("", "", ""),
                open=True,
            )

            # Group files by category within this folder
            by_cat: dict[str, list[dict]] = {}
            for f in files:
                cat = f["category"]
                if cat not in by_cat:
                    by_cat[cat] = []
                by_cat[cat].append(f)

            for cat_name in SUBFOLDERS:
                if cat_name not in by_cat:
                    continue
                cat_id = self.tree.insert(
                    folder_id, tk.END,
                    text=f"  \U0001F4C2 {cat_name}",
                    values=("", "", ""),
                    open=True,
                )
                for f in by_cat[cat_name]:
                    size_str = self._format_size(f["size"])
                    self.tree.insert(
                        cat_id, tk.END,
                        text=f"    \U0001F3B5 {f['filename']}",
                        values=(cat_name, f["extension"], size_str),
                    )

        total = self.plan["total_files"]
        tracks = len(self.plan["tracks"])
        self.status_var.set(f"Found {total} file(s) across {tracks} track group(s). Review and click 'Organize Files'.")
        self.execute_btn.config(state=tk.NORMAL)

    def _execute(self) -> None:
        """Execute the organization plan after user confirmation."""
        if not self.plan or not self.source_dir:
            return

        total = self.plan["total_files"]
        tracks = len(self.plan["tracks"])

        confirm = messagebox.askyesno(
            "Confirm",
            f"This will organize {total} file(s) into {tracks} project folder(s).\n\n"
            "Files will be MOVED (not copied). No files will be deleted.\n"
            f"Backup: {'Yes' if self.backup_var.get() else 'No'}\n\n"
            "Continue?",
        )

        if not confirm:
            return

        # Backup
        if self.backup_var.get():
            self.status_var.set("Creating backup...")
            self.root.update_idletasks()
            try:
                backup_path = create_backup(self.source_dir)
                self.status_var.set(f"Backup created at: {backup_path}")
                self.root.update_idletasks()
            except Exception as e:
                messagebox.showerror("Backup Error", f"Failed to create backup:\n{e}")
                return

        # Execute
        self.status_var.set("Organizing files...")
        self.root.update_idletasks()

        try:
            log_path = os.path.join(self.source_dir, "move_log.csv")
            move_log = execute_plan(self.plan, log_path)
            self.status_var.set(
                f"Done! Moved {len(move_log)} file(s). Log saved to: {log_path}\n"
                "You can now manually drag-and-drop files to correct any misplacements."
            )
            self.execute_btn.config(state=tk.DISABLED)
            messagebox.showinfo(
                "Complete",
                f"Successfully organized {len(move_log)} file(s)!\n\n"
                f"Move log: {log_path}\n\n"
                "Folders are unlocked — feel free to manually move files "
                "to correct any misplacements.",
            )
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{e}")
            self.status_var.set(f"Error: {e}")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# ---------------------------------------------------------------------------
# CLI fallback (for headless environments)
# ---------------------------------------------------------------------------

def cli_mode() -> None:
    """Simple CLI fallback for environments without display."""
    print("=" * 60)
    print("  Music Production File Organizer (CLI Mode)")
    print("=" * 60)

    directory = input("\nEnter the directory path to organize: ").strip()
    if not directory or not os.path.isdir(directory):
        print("Error: Invalid directory path.")
        return

    print("\nScanning directory...")
    plan = create_classification_plan(directory)

    if plan["total_files"] == 0:
        print("No files found in the directory.")
        return

    # Show preview
    print(f"\nFound {plan['total_files']} file(s) in {len(plan['tracks'])} track group(s):\n")
    for folder_name, files in sorted(plan["tracks"].items()):
        print(f"  {folder_name}/")
        by_cat: dict[str, list[dict]] = {}
        for f in files:
            cat = f["category"]
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(f)

        for cat_name in SUBFOLDERS:
            if cat_name not in by_cat:
                continue
            print(f"    {cat_name}/")
            for f in by_cat[cat_name]:
                print(f"      - {f['filename']}")
        print()

    # Backup option
    do_backup = input("Create backup before organizing? (y/n) [y]: ").strip().lower()
    if do_backup in ("", "y", "yes"):
        print("Creating backup...")
        try:
            backup_path = create_backup(directory)
            print(f"Backup created at: {backup_path}")
        except Exception as e:
            print(f"Backup failed: {e}")
            abort = input("Continue without backup? (y/n) [n]: ").strip().lower()
            if abort not in ("y", "yes"):
                print("Aborted.")
                return

    # Confirm
    confirm = input("\nProceed with organizing files? (y/n) [n]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Aborted.")
        return

    # Execute
    print("\nOrganizing files...")
    log_path = os.path.join(directory, "move_log.csv")
    move_log = execute_plan(plan, log_path)
    print(f"\nDone! Moved {len(move_log)} file(s).")
    print(f"Move log saved to: {log_path}")
    print("\nFolders are unlocked. You can manually drag-and-drop files to correct any misplacements.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Launch the application — GUI if display available, CLI otherwise."""
    try:
        root = tk.Tk()
        # Test if display is available
        root.withdraw()
        root.update()
        root.deiconify()
        MusicFileOrganizerApp(root)
        root.mainloop()
    except tk.TclError:
        # No display available, fall back to CLI
        print("No display detected. Falling back to CLI mode.\n")
        cli_mode()


if __name__ == "__main__":
    main()
