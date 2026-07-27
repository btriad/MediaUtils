# MediaUtils Roadmap

## Phase 1 — Code Quality & Stability

Quick wins that improve reliability without changing behavior.

- [ ] Replace all bare `except:` blocks with specific exception types
- [ ] Remove duplicate `validate_folder_path()` in `settings_manager.py`
- [ ] Use `urllib.parse.urlencode()` for Nominatim API URL construction
- [ ] Replace remaining `print()` calls with proper logging
- [ ] Complete type hints across all modules
- [ ] Extract magic numbers into a `constants.py` module

## Phase 2 — Core Feature Gaps

High-impact features that users would expect from a file renaming tool.

- [ ] Undo/rollback — reverse rename operations using existing backup logs
- [ ] Dry-run mode — show exact before/after filenames without committing
- [ ] Configuration profiles — save/load multiple format presets
- [ ] Export reports — CSV or HTML summary of rename operations

## Phase 3 — Performance

Optimizations for large batches (1000+ files).

- [ ] Parallel metadata extraction using `concurrent.futures.ThreadPoolExecutor`
- [ ] Increase GPS cache default size (1000 -> 10000) with LRU eviction
- [ ] Lazy-load file list in TreeView for large directories
- [ ] Cache metadata extraction results within a session

## Phase 4 — Architecture Refactoring

Improve maintainability and testability.

- [ ] Split `FileOperations` into focused classes (discovery, resolution, renaming)
- [ ] Add `pyproject.toml` and proper Python packaging
- [ ] Consolidate duplicated GPS/date parsing into shared utilities
- [ ] Enforce dependency injection — remove default instance creation in constructors

## Phase 5 — UX & Distribution

Polish and accessibility improvements.

- [ ] Add keyboard shortcuts (Ctrl+O open, Ctrl+Z undo, etc.)
- [ ] Dark mode support
- [ ] Optional folder organization (sort into YYYY/MM subfolders)
- [ ] Package as standalone executable (PyInstaller)
- [ ] Add tooltips and accessibility features
