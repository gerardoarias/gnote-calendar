# gnote-calendar — Gestor de Notas y Calendario Ligero para Linux (Knowledge OS) v2.0.0 Qt

App nativa C++17 + Python Qt6 PySide6/Tk, **offline-first**, `<60MB RAM` Qt (`80MB` PySide medido `50MB` mínimo) / `<25MB Tk`, **arranque <120ms CLI / <200ms Qt**, para hardware desde 2015. Knowledge OS con journal diario, backlinks, grafo force-directed, folder sync y `F11` maximizar fix.

![License: MIT](https://img.shields.io/badge/license-MIT-blue)

## ✨ Features v2.0.0 — Knowledge OS Qt

| Categoría | Features v2.0.0 |
|---|---|
| **Notas** | Markdown + preview `F9` `QTextBrowser` `markdown 3.5.2`, `#tag`, `[[backlink]]` indexado, FTS5, `tag:` + `fecha:hoy/semana/YYYY-MM-DD` + `highlight` amarillo, journal diario auto |
| **Tareas** | `- [ ]` checklist `due:2026-08-23 prio:alta/media/baja` filtro/orden, toggle `Ctrl+Enter` / doble-click, panel global `✅ Tareas (pend)` colores, `QSystemTray` notif |
| **Plantillas** | Diario (auto hoy) / Reunión / Proyecto / Idea / Vacía |
| **Calendario** | Mes `QCalendarWidget` + semana `QTable 24x7` puntos verdes, todo el día, vincular `evento ↔ nota`, `RRULE` en DB, doble-click semana crea evento |
| **Pomodoro** | `🍅 25/5` `QTimer` + `QSystemTrayIcon` `notify-send`, integrado a nota |
| **Sync Gmail** | `.ics` RFC5545 |
| **Folder Sync** | `~/Notas` 1 `.md` por nota frontmatter `id/title/tags`, `gnote-calendar sync [--folder ~/Notas] [--watch]`, idempotente `QFileSystemWatcher` + poll 5s GUI |
| **Knowledge** | Backlinks tabla, grafo `QGraphicsView` embebido filtro `tag`, `F11` maximizar fix, `QSettings` persistencia |
| **Export** | `.ics` + `.md` + frontmatter |
| **UI** | Qt6 PySide6 moderno (`gui_qt.py` 80K `1320x800` sidebar 94px 4 secciones `F11`) fallback Tk (`gui.py` 36K) legacy `gui_gtk4.py` `legacy/` |

## 📦 Instalación rápida

### Opción A — Instalador local (sin sudo, recomendado)
```bash
./install.sh                    # instala en ~/.local (detecta PySide6)
~/.local/bin/gnote-calendar --help
python3 ~/.local/share/gnote-calendar/gui_qt.py  # GUI Qt (PySide6 6.7.3)
python3 ~/.local/share/gnote-calendar/gui.py     # fallback Tk
# o busca "gnote-calendar" en el menú (Exec gui_qt.py)
```

### Opción B — .deb (sistema)
```bash
sudo dpkg -i dist/gnote-calendar_2.0.0_amd64.deb  # Recommends: python3-pyside6|pyqt5|pyside2
gnote-calendar --help
gnote-calendar sync --folder ~/Notas  # folder sync idempotente QFileSystemWatcher
```

### Opción C — Portable
```bash
tar -xzf dist/gnote-calendar_2.0.0_portable.tar.gz
./gnote-calendar/build/gnote-calendar --help
python3 gnote-calendar/gui_qt.py  # Qt PySide6 <60MB
python3 gnote-calendar/gui.py     # fallback Tk
```

### Opción D — Flatpak (v2.0.0 Fase 7)
```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.kde.Platform//6.9 org.kde.Sdk//6.9 -y
flatpak-builder --force-clean --repo=repo --ccache build flatpak/com.gnote.calendar.json
flatpak build-bundle repo gnote-calendar.flatpak com.gnote.calendar
flatpak install --user gnote-calendar.flatpak
flatpak run com.gnote.calendar
```

### Opción D — Doble click (ya instalado)
Escritorio → `gnote-calendar` (GUI Tkinter) o `gnote-calendar (Terminal)` para debug.

## 🏗️ Compilación

```bash
make            # CLI ligero sin dependencias (vendoriza sqlite3.c) + Qt Python
make test && ./build/gnote-tests  # 5 tests (+ sync idempotente)
make WITH_QT=1  # + GUI C++ Qt6 opcional (src/ui/qt)
cmake -B build -DCMAKE_BUILD_TYPE=Release -DWITH_QT=OFF && cmake --build build
pip install --break-system-packages -r requirements.txt  # PySide6==6.7.3 pytest-qt
```

Requisitos 2015: `g++ >=7`, `gcc`, `make`, `python3 + tk` (8.6) / `python3-pyside6` o `pip PySide6 6.7.3` para Qt moderno. Todo en Linux Lite 7 / Ubuntu 22.04+.
Fallback Tk si Qt no disponible. Legacy GTK4 en `legacy/gui_gtk4.py` deprecado.

## 💻 Uso GUI v2.0.0 Qt

`python3 gui_qt.py` (Qt PySide6 1320x800) o `python3 gui.py` (Tk fallback) o menú `gnote-calendar`.

- **Sidebar 94px 4 secciones:** `📝 Notas` | `📅 Calendario` (Mes `QCalendarWidget` verde/azul + Semana `QTable 24x7`) | `✅ Tareas` (`due/prio` filtro) | `🕸️ Grafo` (embebido filtro tag) + herramientas `🍅 Pomodoro` `📊 Stats` `📁 Sync` - despeja saturación 1 hoja
- **Top:** `Plantilla` + `Nueva nota` + `Guardar/Borrar` + `⛶ Maximizar F11` (buscador movido a Notas)
- **Notas:** `Filtrar: tag: fecha:hoy` highlight amarillo, tags clickeables, lista `Notas` + `Eventos del mes`, `QSS 14px 10px 14px` desapiñuscado
- **Derecha Editor:** título + toolbar `☐ Tarea ✓ Toggle [[link]] #tag` `👁 Vista previa F9` `Export .md`, `QTextEdit 11pt 16px padding` + `QTextBrowser` markdown `F9` split, highlight `SearchHighlighter` `#fff176`, `Ctrl+S` guardar `Ctrl+Enter` toggle `Ctrl+P` pomodoro
- **Grafo:** `QGraphicsView` force-directed arrastrable `QGraphicsItem.ItemIsMovable`, filtro tag, click navega `switch_section`
- **Folder Sync:** `📁 Folder Sync` elige `~/Notas` + `Sincronizar ahora` `QFileSystemWatcher` + poll 5s auto
- **Status:** hints `Tags/Enlaces/Tareas` + `enlazada por #x` + `Qt 6.7.3`

## ⌨️ Uso CLI

```bash
./build/gnote-calendar note add "Compra" "Leche #casa [[Proyecto]] - [ ] pendiente"
./build/gnote-calendar note list
./build/gnote-calendar note search "leche"
./build/gnote-calendar note search "tag:casa"
./build/gnote-calendar note search "fecha:hoy"
./build/gnote-calendar event add "Reunión" "2026-08-24 10:00" "2026-08-24 11:00" --note 1
./build/gnote-calendar event list --month 2026-08
./build/gnote-calendar ics export --output /tmp/cal.ics --month 2026-08
./build/gnote-calendar ics import /tmp/cal.ics
./build/gnote-calendar sync --folder ~/Notas              # bidireccional idempotente
./build/gnote-calendar sync --folder ~/Notas --watch      # poll 2s
./build/gnote-calendar check-notify  # próximos 15min
```

## 🔄 Flujo Gmail (.ics)

1. **Exportar a Gmail:** GUI `Export .ics` o `ics export --output /tmp/cal.ics` → `calendar.google.com` → `Ajustes` → `Importar y exportar` → `Importar` el `.ics`
2. **Importar desde Gmail:** Gmail → `Exportar` → `ics import archivo.ics` en gnote/GUI `Import .ics`

Deduplica por `UID` (`src/core/ical_service.cpp:64`).

## 📁 Estructura v2.0.0

```
src/core/       -> Note, Event, Storage (SQLite FTS5 + backlinks), IcalService, Search, FolderSync (sync_service)
src/platform/   -> Config, Notifier (QSystemTrayIcon)
src/ui/         -> MainWindow GTK legacy (WITH_GTK) / qt/ opcional WITH_QT
src/app/main.cpp-> CLI + GUI + sync --watch
gui_qt.py       -> GUI Qt6 PySide6 80K (QMainWindow 1320x800, 4 secciones, 1320x800, split markdown, graph, week)
gui.py          -> GUI Tk fallback 40K (Tk)
legacy/gui_gtk4.py -> GUI GTK4 legacy deprecado 50K
third_party/    -> sqlite3 amalgamation vendorizado (8.7M)
data/schema.sql -> Esquema WAL + FTS5 + backlinks + triggers
tests/          -> test_core.cpp (5 suites) + tests/qt/ (8 passed)
packaging/      -> .desktop + icon + control (Recommends pyside6) + build_dist.sh
flatpak/        -> com.gnote.calendar.json 6.9 + metainfo.xml
dist/           -> .deb 2.0.0 (700K) + portable 1.7M + AppImage stub + gnote-calendar.flatpak
```

## ⚡ Performance (medido v2.0.0)

| Métrica | CLI | GUI Tk | GUI Qt PySide6 |
|---|---|---|---|
| Binario strip | 2.1M | +40K | +80K |
| RAM idle | 12M | 32M | 80MB offscreen (50MB mínimo) / <60MB C++ Qt |
| Arranque frío | 33ms | 120ms | 70ms CLI / <200ms Qt |
| DB | `~/.local/share/gnote-calendar/notes.db` WAL + `bak-YYYYMMDD` | — | — |
| Sync | 2s CLI --watch `QFileSystemWatcher` + poll 5s GUI | 5s GUI | 5s GUI + watcher |
| Tray | — | — | `QSystemTrayIcon` notif 15min `Ctrl+H` alto contraste |
| Build `make` | 40s (O0 sqlite) | +1s | +1s + `pip PySide6 6.7.3` |
| QSS | — | — | `14px 10px 14px` `padding 16px` desapiñuscado |

Objetivo 2015 cumplido Tk `<60MB`; Qt `80MB` PySide (50MB mínimo) `<60MB` con `WITH_QT` C++.

## 📄 Licencia

MIT — Ver `LICENSE`.
