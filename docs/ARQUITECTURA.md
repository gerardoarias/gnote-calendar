# Arquitectura gnote-calendar v2.0.0 Qt

## Decisiones clave para ligereza 2015 (actualizado Qt)
- **C++17** no C++20: compila con GCC 7 (Ubuntu 18.04)
- **SQLite vendorizado**: sin dependencia sistema, WAL + FTS5 + FTS5 triggers + `backlinks`, single file + `backup_db` rotativo `bak-YYYYMMDD`
- **ICS sin libical**: parser ~200 líneas, evita 2MB de libical
- **Qt6 PySide6** (LGPL) + **Tk fallback**: CLI siempre disponible (<15MB RAM), GUI Qt `QMainWindow 1320x800` 4 secciones, `QFileSystemWatcher` + `QSystemTrayIcon`, fallback Tk 2015

## Diagrama v2.0.0
```
CLI (main.cpp)  <-->  Storage (SQLite WAL+FTS5+backlinks)  <--> notes.db + notes.db.bak-YYYYMMDD
  |                       |---- FolderSync (sync_service + QFileSystemWatcher) --> ~/Notas (Syncthing)
  v                       v---- IcalService (import/export .ics) --> Gmail (UID dedup)
Search (FTS5 rank)   Notifier (QSystemTrayIcon + notify-send fallback) 15min
  |
[Qt UI] MainWindow (PySide6) QMainWindow 1320x800
  ├─ Sidebar 94px QToolButton 4 secciones (Notas/Calendario/Tareas/Grafo)
  ├─ Stacked: Notas (QSyntaxHighlighter) | Calendario Mes QCalendarWidget + Semana QTable 24x7 | Tareas due/prio | Grafo QGraphicsView
  └─ Right Editor QSplitter QTextEdit 11pt + QTextBrowser markdown preview F9
  + QSettings geometry/section/preview + high-contrast Ctrl+H
[Legacy GTK] MainWindow (opcional, legacy/gui_gtk4.py deprecado)
```

## Flujo .ics Gmail
Export: storage.listAllEvents() -> IcalService::exportToFile() -> upload Gmail
Import: download Gmail .ics -> IcalService::importFromFile() -> storage.createEvent() con deduplicación por uid

## Performance v2.0.0
- Binario CLI: ~2.1M strip
- RAM: 12MB (CLI idle) / 32MB (Tk) / 80MB Qt offscreen (50MB mínimo QMainWindow solo, <60MB C++ Qt)
- Arranque: 33ms (CLI), 70ms (CLI help), <200ms (Qt)
