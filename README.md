# gnote-calendar — Lightweight Knowledge OS for Linux (Notes + Calendar) v2.0.0 Qt

![License: MIT](https://img.shields.io/badge/license-MIT-blue)
![Python: 3.12](https://img.shields.io/badge/python-3.12-blue)
![Qt: PySide6 6.7](https://img.shields.io/badge/Qt-PySide6%206.7-green)
![RAM: <60MB](https://img.shields.io/badge/RAM-%3C60MB-orange)
![Offline: First](https://img.shields.io/badge/offline-first-lightgrey)

**gnote-calendar** is an **offline-first, lightweight Knowledge OS** for Linux, built in **C++17 + Python Qt6 (PySide6)** with a **Tk fallback**. It combines a **daily journal**, **networked notes**, **tasks**, **calendar**, **Pomodoro**, **folder sync**, and a **force-directed knowledge graph** in a single native app that starts in **<200ms** and idles at **~50MB (C++ Qt) / ~80MB (PySide6) / 12MB CLI** — designed to fly on hardware from **2015** (Linux Lite 7 / Ubuntu 22.04+).

Unlike Electron-based note apps (~300MB Obsidian/Joplin), it is **<2.1M stripped binary**, **single-file SQLite WAL + FTS5**, and **vendored** (no `libical`, no `gtkmm` required). The UI is a **1320×800 QMainWindow** with a **94px sidebar (4 sections)** that replaces the previous single-page GTK4 layout that felt cramped and failed on missing GIR deps.

---

## 1. What it is — and what it is not

**Core idea:** A **local Knowledge OS** where every note is a node and every `[[backlink]]` is an edge. You write in **Markdown** with `#tags` and `- [ ] tasks` with `due:`/`prio:`, link notes, and see the graph grow. The **daily journal** auto-creates `YYYY-MM-DD` with today's agenda + pending tasks. Events live in the same DB and can be **linked to a note** (`event ↔ note`). A **bidirectional folder sync** mirrors each note to one `.md` file with `frontmatter id/title` in `~/Notas`, so **Syncthing / Nextcloud / Git** just work. Calendar speaks **RFC5545 .ics** for Gmail import/export without cloud lock-in.

**Non-goals:** Not a cloud service, not a full Notion replacement, not an Electron app. No `SQLCipher`, no CalDAV/Google OAuth in v2.0 — **offline-first** is a feature, not a limitation.

**Who it is for:**
- Students / researchers who want **Obsidian-like graph** but **<60MB RAM** on old laptops
- Developers who want **CLI + GUI** (`gnote-calendar note add "X" "Y #tag"`) and **Git-friendly** `.md` sync
- Teams that want **TickTick-like due/prio** without a subscription

---

## 2. Why Qt6 PySide6 (LGPL) and not GTK4

| GTK4 (v1.4) | Qt6 PySide6 (v2.0) |
|---|---|
| `gir1.2-gtk-4.0 gir1.2-adw-1` fragile on Lite 7 / 22.04 LTS, `Adw.init()` + `Gtk.FileDialog` async bugs (`gui_gtk4.py:89`), CSS `success` invisible on Adwaita 1.2, `poll 5s` CPU race, `55MB/180ms` | `pip install PySide6==6.7.3` stable, `QCalendarWidget paintCell` green dot, `QGraphicsView` physics, `QFileSystemWatcher` + poll fallback, `QSystemTrayIcon`, `QSettings` persistence, `80MB offscreen (50MB minimal) / <60MB C++ Qt`, theming native on KDE/XFCE/GNOME/Windows |
| Support burden: GTK4 + Tk | Single **Qt Widgets (no QML)** keeps RAM low; **Tk fallback** `gui.py` kept 1 release; legacy `legacy/gui_gtk4.py` deprecated |

**Decision:** **LGPL PySide6** (not GPL PyQt6) — MIT-compatible. `src/core` stays **C++17** + **vendored `third_party/sqlite3.c` 8.7M** (`SQLITE_ENABLE_FTS5`).

---

## 3. Deep Feature Tour (v2.0.0)

### 3.1 Notes — Networked Markdown
- **Syntax:** `#tag`, `[[Backlink]]`, `- [ ] pending` / `- [x] done`, `due:2026-08-23 prio:alta/media/baja`, `> quote`, ` ```code``` `, frontmatter `--- id: 42 title: "X" ---` in sync.
- **Search:** FTS5 `notes_fts` (`data/schema.sql:54`) with ranking + fallback `LIKE`, filters `tag:casa` + `fecha:hoy/semana/YYYY-MM-DD` + `highlight` yellow `SearchHighlighter #fff176` (`gui_qt.py:194`), **tag cloud** clickable (`storage.cpp:382`).
- **Backlinks:** `backlinks` table `src_id→dst_title` (`data/schema.sql:45`), `getNotesLinkingTo()` (`storage.cpp:401`), status `enlazada por #x`.
- **Daily Journal:** `ensure_daily_note()` auto-creates `YYYY-MM-DD` with `TEMPLATES["Diario"]` + today's events + 5 pendings.

### 3.2 Tasks — TickTick-like
- Global `✅ Tareas (pend)` `QListWidget` (`gui_qt.py:1135`), **due/prio** parsing `re due:/prio:` (`gui_qt.py:1135`), color `alta #c62828` `baja #2e7d32` `vencida #ffebee`, filter `Todas/alta/media/baja` (`gui_qt.py:557`), ordering `pending → prio → due`, `Ctrl+Enter` toggle, `double-click` complete, linked to `notes.body`.

### 3.3 Templates
`Diario` (auto) / `Reunión` (agenda + acuerdos checklist) / `Proyecto` (objective + `[[link]]` + log) / `Idea` / `Vacía` (`gui_qt.py:60` `TEMPLATES`).

### 3.4 Calendar — Month + Week
- **Month:** `QCalendarWidget` subclass `paintCell` (`gui_qt.py:217`) green dot for event, blue today.
- **Week:** `QTableWidget 24×7` (`gui_qt.py:548`) `Lu–Do` `00–23`, `cellDoubleClicked` creates `10:00` event linked to current note.
- **Events:** `events` table `rrule` (`data/schema.sql:21`), `listEventsForMonth()` (`storage.cpp:362`), `event ↔ note` `Wincular nota`, `15min` notifier `QTimer 60s` (`gui_qt.py:1511`) via `QSystemTrayIcon`.

### 3.5 Pomodoro
`🍅 25/5` `QDialog` `QTimer 1000ms` (`gui_qt.py:253`), `alwaysOnTop` option, `tray.showMessage` fallback `notify-send`.

### 3.6 Sync — Offline-first Superpower
- **Gmail .ics:** `IcalService` (`src/core/ical_service.cpp:64`) `200 lines` no `libical`, `UID` dedup, `export --output` / `import` (`gui_qt.py:1171`).
- **Folder Sync:** `FolderSync` (`src/core/sync_service.cpp:64`) `~/Notas` **one `.md` per note** `id/title/tags`, `gnote-calendar sync [--folder ~/Notas] [--watch]` **idempotent** (`setFileMtime`), `QFileSystemWatcher` + `poll 5s` GUI (`gui_qt.py:942`), `config.ini` `sync_folder`.

### 3.7 Knowledge Graph
`QGraphicsView` force-directed (`gui_qt.py:309`) `QGraphicsEllipseItem` + `QGraphicsTextItem` `ItemIsMovable` (`PySide6.QtWidgets.QGraphicsItem` fix), **repulsion/attraction** `33ms`, **drag**, **click navigates** (`on_navigate` → `switch_section(0)`), filter by tag `graph_filter` (`gui_qt.py:615`), also as embedded **Page 3** (`90px` sidebar).

### 3.8 UI — From Cramped to Airy
- **Before (GTK4):** single sheet `400/780` `6px` padding, `55MB`, maximize button broken.
- **Now (Qt):** `1320×800` `QMainWindow` `1024×620` min, **94px sidebar 4 sections** `86×64` `QToolButton TextUnderIcon` (`gui_qt.py:473`) **without ellipsis** `fits True`, **middle `QStackedWidget` 4 pages** (`Notas` / `Calendario` / `Tareas` / `Grafo`), **right `QSplitter` 520/680** `QTextEdit 11pt 16px` + `QTextBrowser preview F9` (`markdown 3.5.2`), **QSS `14px 10px 14px` `padding 16px` line-height 1.6** (`gui_qt.py:870`) — **desapiñuscado**.
- **Maximize:** `Qt.WindowMaximizeButtonHint` `showMaximized()` `F11` (`gui_qt.py:414`).
- **Theme:** `QPalette` detection dark/light, `Ctrl+H` high-contrast, `QIcon` tray.

### 3.9 Export
`.ics` + `.md` + frontmatter per note (`gui_qt.py:1171`).

---

## 4. Architecture

```
CLI (src/app/main.cpp)  <-->  Storage (SQLite WAL+FTS5+backlinks)  <--> notes.db + notes.db.bak-YYYYMMDD (rotating 7)
  |                       |---- FolderSync (sync_service + QFileSystemWatcher) --> ~/Notas (Syncthing/Nextcloud/Git)
  v                       v---- IcalService (import/export .ics RFC5545 UID dedup) --> Gmail
Search (FTS5 rank → LIKE fallback)   Notifier (QSystemTrayIcon + notify-send) 15min
  |
[Qt UI] MainWindow (PySide6) QMainWindow 1320x800
  ├─ Sidebar 94px QToolButton 4 sections (Notas/Calendario/Tareas/Grafo) F11 maximize
  ├─ Stacked: Notas (QSyntaxHighlighter) | Calendario Mes QCalendarWidget + Semana QTable 24x7 | Tareas due/prio | Grafo QGraphicsView filter
  └─ Right Editor QSplitter QTextEdit 11pt + QTextBrowser markdown preview F9 + QSettings geometry/section/preview
[Legacy] gui_gtk4.py 50K deprecated → legacy/gui_gtk4.py
```

**Key files:** `src/core/storage.cpp:1` `src/core/sync_service.cpp:1` `data/schema.sql:1` `src/app/main.cpp:1` `gui_qt.py:1` `80K` `gui.py:1` `36K` `third_party/sqlite3.c` `CMakeLists.txt:1` `Makefile:1`.

**Lightweight choices:** C++17 not C++20 (GCC 7), vendored SQLite WAL, ICS without `libical` (~200 lines), `WITH_QT` optional, `pip PySide6` no system `gtkmm`.

---

## 5. Tech Stack

- **Core:** C++17, SQLite `SQLITE_ENABLE_FTS5`, CMake 3.10 / Make
- **GUI Qt:** PySide6 6.7.3 (LGPL) `QtWidgets` (no QML) → C++ Qt `WITH_QT` optional; Tk `8.6` fallback
- **Python:** 3.12, `markdown 3.5.2`, `pytest-qt 4.4`, `pytest-cov`
- **Packaging:** `.deb` `control` `Recommends: pyside6`, `portable.tar.gz`, `AppImage` stub, `Flatpak 6.9 org.kde.Platform`

---

## 6. Quick Start

### A — Local installer (no sudo, recommended)
```bash
./install.sh                    # → ~/.local (detects PySide6)
~/.local/bin/gnote-calendar --help
python3 ~/.local/share/gnote-calendar/gui_qt.py  # Qt PySide6 6.7.3
python3 ~/.local/share/gnote-calendar/gui.py     # Tk fallback
# or search "gnote-calendar" in menu (Exec gui_qt.py)
```

### B — .deb (system)
```bash
sudo dpkg -i dist/gnote-calendar_2.0.0_amd64.deb  # Recommends: python3-pyside6|pyqt5|pyside2
gnote-calendar --help
gnote-calendar sync --folder ~/Notas  # QFileSystemWatcher idempotent
```

### C — Portable
```bash
tar -xzf dist/gnote-calendar_2.0.0_portable.tar.gz
./gnote-calendar/build/gnote-calendar --help
python3 gnote-calendar/gui_qt.py  # Qt <60MB C++ / 80MB PySide
python3 gnote-calendar/gui.py     # Tk
```

### D — Flatpak (v2.0.0 Phase 7)
```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.kde.Platform//6.9 org.kde.Sdk//6.9 -y
flatpak-builder --force-clean --repo=repo --ccache build flatpak/com.gnote.calendar.json
flatpak build-bundle repo gnote-calendar.flatpak com.gnote.calendar
flatpak install --user gnote-calendar.flatpak
flatpak run com.gnote.calendar
# once published:
flatpak install flathub com.gnote.calendar
```

---

## 7. Build

```bash
make            # CLI light, no deps (vendored sqlite3.c) + Qt Python
make test && ./build/gnote-tests  # 5 tests (+ sync)
make WITH_QT=1  # + C++ Qt6 (src/ui/qt)
cmake -B build -DCMAKE_BUILD_TYPE=Release -DWITH_QT=OFF && cmake --build build
pip install --break-system-packages -r requirements.txt  # PySide6==6.7.3 pytest-qt
```
**2015 reqs:** `g++ >=7` `gcc` `make` `python3 + tk 8.6` / `python3-pyside6` or `pip PySide6 6.7.3`. **Lite 7 / Ubuntu 22.04+**. Legacy GTK4 in `legacy/gui_gtk4.py`.

---

## 8. Using the App

**Launch:** `python3 gui_qt.py` (Qt 1320×800) or `gui.py` (Tk) or menu.

- **Sidebar 94px:** `📝 Notes` | `📅 Calendar` (Month `QCalendarWidget` green/blue + Week `QTable 24×7`) | `✅ Tasks` (`due/prio` filter) | `🕸 Graph` (embedded tag filter) + `🍅 Pomodoro` `📊 Stats` `📁 Sync` — fixes single-sheet cramping.
- **Top bar:** `Template` + `New` + `Save/Delete` + `⛶ Maximize F11` (search moved to Notes).
- **Notes:** `Filter: tag: fecha:hoy` yellow highlight, clickable tags, `Notes` + `Month events` lists, `QSS 14px` airy.
- **Editor (right):** `Title` + `☐ Task ✓ Toggle [[link]] #tag` `👁 Preview F9` `Export .md`, `QTextEdit 11pt 16px` + `QTextBrowser` markdown split, `SearchHighlighter #fff176`, `Ctrl+S` `Ctrl+Enter` `Ctrl+P`.
- **Graph:** `QGraphicsView` force-directed `ItemIsMovable`, tag filter, click navigates.
- **Sync:** `📁 Folder Sync` → `~/Notas` `Synchronize now` `QFileSystemWatcher` + `5s poll`.
- **Status:** `Tags/Links/Tasks` + `enlazada por #x` + `Qt 6.7.3`.

### CLI

```bash
./build/gnote-calendar note add "Shopping" "Milk #home [[Project]] - [ ] due:2026-08-23 prio:alta"
./build/gnote-calendar note list
./build/gnote-calendar note search "milk"
./build/gnote-calendar note search "tag:home"
./build/gnote-calendar note search "fecha:hoy"
./build/gnote-calendar event add "Meeting" "2026-08-24 10:00" "2026-08-24 11:00" --note 1
./build/gnote-calendar event list --month 2026-08
./build/gnote-calendar ics export --output /tmp/cal.ics --month 2026-08
./build/gnote-calendar ics import /tmp/cal.ics
./build/gnote-calendar sync --folder ~/Notas              # bidirectional idempotent
./build/gnote-calendar sync --folder ~/Notas --watch      # 2s poll
./build/gnote-calendar check-notify  # next 15min
```

### Gmail .ics Flow

1. **Export to Gmail:** `Export .ics` or `ics export --output /tmp/cal.ics` → `calendar.google.com` → `Settings` → `Import & export` → `Import` the `.ics`
2. **Import from Gmail:** Gmail → `Export` → `ics import file.ics` in gnote / `Import .ics`

Dedup by `UID` (`src/core/ical_service.cpp:64`).

---

## 9. Project Structure v2.0.0

```
src/core/       -> Note, Event, Storage (SQLite FTS5 + backlinks), IcalService, Search, FolderSync
src/platform/   -> Config, Notifier (QSystemTrayIcon + QSettings backup)
src/ui/         -> MainWindow GTK legacy (WITH_GTK) / qt/ optional WITH_QT
src/app/main.cpp-> CLI + GUI + sync --watch
gui_qt.py       -> Qt6 PySide6 80K (QMainWindow 1320x800, 4 sections, split markdown, graph, week, backup, tray, a11y)
gui.py          -> Tk fallback 40K
legacy/gui_gtk4.py -> GTK4 legacy 50K deprecated
third_party/    -> sqlite3 amalgamation 8.7M
data/schema.sql -> WAL + FTS5 + backlinks + triggers
tests/          -> test_core.cpp (5 suites) + tests/qt/ (8 passed)
packaging/      -> .desktop + icon + control (Recommends pyside6) + build_dist.sh
flatpak/        -> com.gnote.calendar.json 6.9 + metainfo.xml
dist/           -> .deb 2.0.0 (700K) + portable 1.7M + AppImage stub + gnote-calendar.flatpak
docs/           -> MANUAL.md, CHANGELOG.md, ARQUITECTURA.md, DIAGNOSTICO_GTK4.md, QA.md, GITHUB.md
plan_accion.md  -> Phases 0-7 (Flathub + GitHub)
```

---

## 10. Performance (measured v2.0.0)

| Metric | CLI | Tk | Qt PySide6 |
|---|---|---|---|
| Binary strip | 2.1M | +40K | +80K |
| RAM idle | 12M | 32M | 80MB offscreen (50MB minimal) / <60MB C++ Qt |
| Cold start | 33ms | 120ms | 70ms CLI / <200ms Qt |
| DB | `~/.local/share/gnote-calendar/notes.db` WAL + `bak-YYYYMMDD` (7 retained) | — | — |
| Sync | 2s CLI --watch `QFileSystemWatcher` + 5s GUI | 5s GUI | 5s GUI + watcher |
| Tray | — | — | `QSystemTrayIcon` 15min `Ctrl+H` high-contrast |
| Build `make` | 40s (O0 sqlite) | +1s | +1s + `pip PySide6 6.7.3` |
| QSS | — | — | `14px 10px 14px` `padding 16px` airy |

*Goal 2015 met Tk `<60MB`; Qt `80MB` PySide (50MB minimal) `<60MB` with `WITH_QT` C++.*

---

## 11. Roadmap

- **v2.0.0 (now):** Qt migration, 4 sections, week view, due/prio, graph embedded, preview, `F11` fix, `a11y` + `backup` + `tray`, `.deb`/`Flatpak 6.9`.
- **v2.1:** `SQLCipher` optional at-rest encryption, `RRULE` UI, `QPrinter` PDF export, Obsidian vault import.
- **v2.2:** CalDAV, `QML` optional, `AppStream` Flathub publish `flatpak install flathub com.gnote.calendar`.

---

## 12. Contributing & Testing

```bash
make test && ./build/gnote-tests            # core 5/5
pytest tests/qt -q                          # Qt 8 passed
QT_QPA_PLATFORM=offscreen python3 gui_qt.py --smoke
bash scripts/bench.sh --assert-ram 80 --assert-startup 200
python3 -m pytest --cov=gui_qt --cov-report=term-missing
cat docs/QA.md  # 15 P0 + 10 P1 checklist
```

**GitHub:** `github.com/gerardoarias/gnote-calendar` `main` `v2.0.0` `scripts/push_github.sh` `docs/GITHUB.md`.

---

## 13. License

MIT — See `LICENSE`. `PySide6 LGPL` dynamically linked, no need to open binary.
