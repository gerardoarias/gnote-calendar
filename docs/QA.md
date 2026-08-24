# QA Checklist — gnote-calendar Qt v2.0 (Fase 5)

**Fecha:** 2026-08-23
**Stack:** PySide6 6.7.3, RAM objetivo `<60MB` (real 80MB offscreen, 50MB mínimo), arranque `<200ms`

## P0 - Críticos (100% pass)

- [ ] `make test && ./build/gnote-tests` 5/5 PASS
- [ ] `pytest tests/qt -q` 8 passed 1 skipped
- [ ] `QT_QPA_PLATFORM=offscreen python3 gui_qt.py --smoke` exit 0 sin traceback
- [ ] Crear nota Diario `Nueva nota` → aparece en lista, `Guardar` `Ctrl+S` persiste
- [ ] Búsqueda `tag:casa` `fecha:hoy` `fecha:semana` highlight amarillo `#fff176`
- [ ] Toggle tarea `Ctrl+Enter` y `doble click` en Tareas → `- [ ]` ↔ `- [x]`
- [ ] Calendario mes: puntos verdes, `Hoy` azul, `◀ ▶` cambia mes, `Hoy` vuelve
- [ ] Calendario semana: `Semana` tab muestra `QTable 24x7` con eventos, `doble click` crea evento
- [ ] Tareas `due:2026-08-23 prio:alta` filtro `Todas/alta/media/baja` colorea `alta #c62828`
- [ ] Grafo: sección `Grafo` embebido `QGraphicsView` arrastrable, filtro `tag`, click navega a nota
- [ ] Preview markdown `F9` `QTextBrowser` render `markdown 3.5.2` `#tag` azul `[[link]]` verde
- [ ] Folder Sync `QFileSystemWatcher` + `poll 5s` idempotente `sync --folder` 2ª vez 0 cambios
- [ ] ICS `export --output` + `import` deduplica `UID`
- [ ] Pomodoro `🍅 25:00` `QTimer 1s` `notify`
- [ ] Maximizar `F11` `⛶` `QMainWindow showMaximized` `flags 0x800f001` y `isMaximized` toggle
- [ ] Sidebar `94px` `86x64` `Notas/Calendario/Tareas/Grafo` sin elipsis `fits True`

## P1 - Importantes (90% pass)

- [ ] `QSystemTrayIcon` visible si `isSystemTrayAvailable()`, `notify_event` via `tray.showMessage` fallback `notify-send`
- [ ] `backup_db()` crea `notes.db.bak-YYYYMMDD` y rota últimos 7
- [ ] `QSettings` restaura `geometry` `windowState` `section` `preview` al reiniciar
- [ ] `setAccessibleName` para `Buscar` `Título` `Editor` `Lista notas/tareas` `Calendario`
- [ ] `Ctrl+H` alto contraste `QSS` amarillo sobre negro, `toggle_high_contrast`
- [ ] `QFont` escalable `Sans 11pt` + `QSS padding 16px` no apiñuscado `sidebar 14px` `item 10px 14px`
- [ ] `install.sh` elige `gui_qt.py` si `PySide6` sino `gui.py`, `desktop Exec` correcto
- [ ] `.deb` `700K` `dpkg -i` + `portable 1.7M` `tar -xzf` + `AppImage stub`
- [ ] `Flatpak` `6.9` `org.kde.Platform` `flatpak-builder --repo=repo` bundle
- [ ] `scripts/bench.sh --assert-ram 80 --assert-startup 200` `elapsed 70ms`

## A11y - Accesibilidad

- [ ] `Tab` navega `Buscar → Lista notas → Título → Editor → Botones` 100% focuseable
- [ ] `Orca` lee `accessibleName` `Buscar notas` `Editor de nota`
- [ ] `Ctrl+H` alto contraste legible `Item:selected #ffff00`
- [ ] `QSystemTray` `setAccessible` y `QIcon` visible

## Performance

- [ ] `ps -o rss -p $(pgrep -f gui_qt)` `<80MB` offscreen (50MB mínimo `QMainWindow` solo)
- [ ] `scripts/bench.sh` `CLI 70ms` `<200ms` `gui_qt 80MB` `<60MB` objetivo C++ (PySide 80MB aceptable)
- [ ] Grafo 10 nodos `30fps` `QTimer 33ms` sin >5% CPU idle

## Comandos QA

```bash
make test && ./build/gnote-tests
pytest tests/qt -v --cov=gui_qt
QT_QPA_PLATFORM=offscreen python3 gui_qt.py --smoke
bash scripts/bench.sh --assert-ram 80 --assert-startup 200
python3 -c "import gui_qt; print(gui_qt.backup_db())" && ls ~/.local/share/gnote-calendar/*.bak-*
flatpak-builder --force-clean --repo=repo build flatpak/io.github.gerardoarias.gnote_calendar.json
```

## Firmas

- QA: ___________ Fecha: ___________
- Build: `2.0.0` `PySide6 6.7.3` `build/gnote-calendar 2.1M`
