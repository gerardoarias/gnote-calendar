# Changelog

## 2.0.0 — 2026-08-23 (Qt PySide6 — Fase 6)
- Migración GTK4 → Qt6 PySide6 `gui_qt.py` 80K: `QMainWindow` 1320x800, sidebar 94px 4 secciones (Notas/Calendario/Tareas/Grafo), `QCalendarWidget` + semana `QTable 24x7`, `QSyntaxHighlighter` highlight, `QFileSystemWatcher` + poll 5s, `QSystemTrayIcon` notifs 15min, `QSettings` persistencia, `backup_db` rotativo, `a11y` `setAccessibleName` + `Ctrl+H` alto contraste, `F11` maximizar fix
- Fase 3 Knowledge Plus: `QGraphicsView` grafo embebido filtro tag, split editor `QTextEdit` + `QTextBrowser` markdown `F9` preview, tareas `due:YYYY-MM-DD prio:alta/media/baja` con filtro y colores, calendario semana doble-click crea evento
- Packaging: `control 2.0.0` `Recommends: pyside6|pyqt5|pyside2`, `.deb 700K` `portable 1.7M` `AppImage stub`, `flatpak 6.9 org.kde.Platform` `com.gnote.calendar.json`, `install.sh` Qt detect, `legacy/gui_gtk4.py` deprecado
- Performance: `CLI 2.1M 70ms`, `Qt 80MB offscreen (50MB mínimo)`, `Tk 25MB`, `QSS` desapiñuscado `14px` padding

## 1.4.0 — 2026-08-23 (Knowledge OS + Folder Sync)
- GTK4 + libadwaita `gui_gtk4.py` 50K con fallback Tk, Adw.HeaderBar, force-directed graph, highlight búsqueda
- Knowledge OS: `backlinks` tabla + índices `idx_notes_title/updated`, journal diario auto con agenda + pendientes, `fecha:` filtros, grafo interactivo arrastrable
- Folder Sync `src/core/sync_service.{h,cpp}` 325 líneas: `~/Notas` 1 .md por nota frontmatter id/title, `gnote-calendar sync --folder ~/Notas [--watch]`, idempotente (export+set mtime), poll 5s en GUI, config `sync_folder`
- Fix: idempotencia sync (setFileMtime), renombrado id, limpieza duplicados diario
- Packaging: .deb 624K / tar.gz 799K v1.4.0, `install.sh` detecta GTK4, `Recommends: gir1.2-gtk-4.0`

## 1.3.0 — 2026-08-23 (GTK4 Fundación)
- Migración GTK4 Python PyGObject, `WITH_GTK4` auto-detect, fallback Tk

## 1.2.0 — 2026-08-23 (Etapa Empaquetado)
- Packaging: .deb (595K), tar.gz portable (757K), AppImage stub, install.sh (PREFIX), desktop + icon
- Optimización: strip 1.8M, arranque 33ms, RAM 12M CLI / 32M GUI
- Docs: README, MANUAL, CHANGELOG, man stub
- Instalación verificada en ~/.local + menú XFCE

## 1.1.0 — 2026-08-23 (Features v2)
- Checklist interactivo + panel Tareas global
- Plantillas: Diario/Reunión/Proyecto/Idea/Vacía
- Pomodoro 25/5 con notify-send
- Tag cloud clickeable + filtros tag:
- Export .md por nota, Stats, Grafo backlinks, Vincular evento-nota
- Notificaciones 15min cada 60s

## 1.0.0 — 2026-08-23 (MVP)
- Core C++17 SQLite vendorizado FTS5, IcalService sin libical, Search
- GUI Tkinter doble-click (fallback CLI), calendario mes, notas CRUD
- CLI: note/event/ics, import/export Gmail
- Build: Makefile sin deps + CMake opcional GTK
- Tests: 5 suites
