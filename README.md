# Music Production File Organizer

Automatically organizes mixed music production files into structured project folders.

## Features

- **Automatic scanning** of a directory for music production files
- **Smart classification** based on file extensions and filename keywords
- **Track grouping** by filename patterns with date extraction
- **GUI mode** (Tkinter) with folder picker, preview tree, and confirmation dialog
- **CLI fallback** for headless environments
- **CSV move log** records every file operation
- **Backup option** creates a full copy before any changes
- **Non-destructive** — files are moved, never deleted; overwrites are prevented

## Folder Structure

Each track/project gets a folder named `YYYYMMDD_TrackTitle` with these subfolders:

```
YYYYMMDD_TrackTitle/
  01_Source_Data/        # Unknown or unclassified files
  02_Prompts/            # Text files (prompts, lyrics, notes)
  03_Making_Process/     # Drafts, demos, intermediate renders
  04_Design_Cover/       # Images (cover art, artwork)
  05_Mastering/          # Files with mastering-related names
  06_Final_Output/       # Files marked as final/released
  07_Working_Files/      # DAW project files (.als, .flp, .logicx, etc.)
```

## Classification Rules

| File Type | Extensions | Default Category |
|-----------|-----------|-----------------|
| Audio | `.wav`, `.mp3`, `.flac`, `.aif`, `.ogg`, `.m4a`, `.aac` | `03_Making_Process` (or `05_Mastering` / `06_Final_Output` if keywords match) |
| Text | `.txt`, `.md`, `.rtf`, `.doc`, `.docx` | `02_Prompts` |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp`, `.svg`, `.psd`, `.ai` | `04_Design_Cover` |
| Project | `.als`, `.flp`, `.logicx`, `.ptx`, `.rpp`, `.cpr`, `.band`, `.reason` | `07_Working_Files` |
| Other | Any other extension | `01_Source_Data` |

Audio files are further classified by filename keywords:
- **"final", "release", "delivered"** → `06_Final_Output`
- **"master", "mastered", "mastering"** → `05_Mastering`
- **"draft", "demo", "wip", "mix", "bounce"** → `03_Making_Process`

## Requirements

- **Python 3.10+**
- **Tkinter** (included with standard Python on Windows)
- No external dependencies required

## Usage

### GUI Mode (default on Windows)

```bash
python music_file_organizer.py
```

1. Click **Browse...** to select the directory containing your music files
2. Click **Scan** to analyze the directory
3. Review the classification preview in the tree view
4. Toggle the **Create backup** checkbox as needed
5. Click **Organize Files** to execute
6. After completion, manually drag-and-drop files to fix any misclassifications

### CLI Mode (headless / no display)

If no display is available, the script automatically falls back to CLI mode:

```bash
python music_file_organizer.py
```

Follow the on-screen prompts to select a directory, review the plan, and confirm execution.

## Output

- **Organized folders** in the source directory
- **`move_log.csv`** — CSV log of all file moves with timestamps, source, and destination paths
- **Backup folder** (optional) — `{dirname}_backup_{timestamp}/` in the parent directory

## Safety

- Files are **moved, never deleted**
- Overwrite protection: if a destination file exists, a numeric suffix is appended
- Optional backup creates a complete copy before any changes
- Folders are **not locked** — manual correction via drag-and-drop is always possible

## Post-Organization

After the script runs, you can freely:
- Drag and drop files between subfolders to correct classifications
- Rename project folders
- Add new files to any subfolder
- Review `move_log.csv` to see what was moved where
