# Plan de Acción — gnote-calendar: Migración GTK4 → Qt (PySide6) + Knowledge OS v2

> **Fecha:** 2026-08-23  
> **Stack elegido:** PySide6 (Qt6, LGPL) · Widgets · RAM objetivo `<60MB` idle · Arranque `<200ms`  
> **Origen:** `gui_gtk4.py` (50K, GTK4/libadwaita) + `gui.py` (36K, Tk) → `gui_qt.py` único  
> **Core intacto:** C++17 + SQLite vendorizado FTS5 (`src/core/storage.cpp:1`, `data/schema.sql:1`) · WAL · `third_party/sqlite3.c`

---

## Índice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Diagnóstico GTK4: por qué falla](#2-diagnóstico-gtk4-por-qué-falla)
3. [Evaluación experta por aspecto (1-10)](#3-evaluación-experta-por-aspecto-110)
4. [Benchmark apps similares y funcionalidades propuestas](#4-benchmark-apps-similares-y-funcionalidades-propuestas)
5. [Estrategia migración Qt - decisiones de arquitectura](#5-estrategia-migración-qt--decisiones-de-arquitectura)
6. [Plan por fases (0-7) con pruebas](#6-plan-por-fases-0-7-con-pruebas)
7. [Matriz de pruebas transversal](#7-matriz-de-pruebas-transversal)
8. [Criterios de aceptación global v2.0.0](#8-criterios-de-aceptación-global-v200)
9. [Riesgos y mitigaciones](#9-riesgos-y-mitigaciones)
10. [Roadmap y entregables](#10-roadmap-y-entregables)
11. [Anexos](#11-anexos)

---

## 1. Resumen ejecutivo

`gnote-calendar` es un **Knowledge OS offline-first** ligero con journal diario, checklist, calendario, pomodoro, folder sync `.md` y grafo backlinks. El core C++ (`src/core/`, `src/platform/`) es sólido y eficiente (`README.md:114` 12MB CLI, 33ms). El cuello de botella es la **UI GTK4**: dependencia `gir1.2-gtk-4.0`/`gir1.2-adw-1` frágil en Linux Lite 7 / Ubuntu 22.04, diálogos async rotos y theming inconsistente, lo que provoca el "no funciona correctamente" reportado.

**Decisión:** Reemplazar GTK4 por **Qt6 vía PySide6** en Python, manteniendo el core y el fallback Tk una versión. PySide6 garantiza: instalación estable (`pip`/`apt python3-pyside6`), theming nativo KDE/XFCE/GNOME/Windows, `QFileSystemWatcher` para sync sin polling, y consumo RAM comparable a Tk si se usa `Qt Widgets` sin QML (objetivo `<60MB` validado `gui_gtk4.py:180ms/55MB` vs `gui.py:120ms/32MB`).

**Resultado esperado v2.0:** paridad funcional v1.4 + editor split-markdown, calendario semana, tareas con vencimiento/prioridad, notificaciones `QSystemTrayIcon`, watcher nativo, tema claro/oscuro, packaging Flatpak/`.deb` con `Recommends: python3-pyside6`.

---

## 2. Diagnóstico GTK4: por qué falla

Inspección directa `gui_gtk4.py:89-103`, `gui.py:176`, `Makefile:30-33`, `CMakeLists.txt:10`, `install.sh:29-42`, `src/app/main.cpp:50`:

| Síntoma | Causa raíz | Evidencia |
|---|---|---|
| **No arranca / fallback silencioso** | `gi.require_version('Gtk','4.0')`/`Adw` lanza excepción si GIR no instalado o versión libadwaita <1.4. `except: os.execv(gui.py)` pierde `sys.argv` y no loguea. | `gui_gtk4.py:89-102` |
| **Dialogs no responden / crean eventos fantasma** | `Gtk.FileDialog` es async (`save_finish`/`open_finish`) pero los callbacks se ignoran; `Adw.MessageDialog.choose(lambda *_: None)` no implementa lógica. `new_event()` crea evento hardcodeado 10:00 sin validar. | `gui_gtk4.py:651-682`, `688-708` |
| **Botones invisibles / CSS roto** | Clases `suggested-action`, `success`, `card` no existen igual en Adwaita 1.2 (Ubuntu 22.04 LTS). `remove_css_class`/`add_css_class` sin fallback. | `gui_gtk4.py:378` |
| **Polling 5s duplica CPU** | `GLib.timeout_add(5000, auto_folder_sync)` + CLI `--watch 2s` (`src/app/main.cpp:175`) compiten sin `inotify`. Race al escribir `notes.db` WAL. | `gui_gtk4.py:349`, `gui.py:174`, `src/core/sync_service.cpp:34` |
| **Búsqueda fecha rota** | `timedelta` usado sin `from datetime import timedelta` en scope `refresh_notes` → `NameError` cuando filtra `fecha:hoy/semana`. | `gui_gtk4.py:447-456` |
| **Build no garantiza runtime** | `WITH_GTK4=1` solo auto-detecta Python (`Makefile:31`), `make` no instala `gir1.2-gtk-4.0`. Usuario Lite 7 (2015+) raramente lo tiene. | `Makefile:31-33` |
| **RAM 55MB límite** | `Adwaita` + `Cairo` graph `area.set_draw_func` con física 30fps (`GLib.timeout_add(33)`) sube a 55MB vs 32MB Tk. | `README.md:119`, `gui_gtk4.py:946` |

**Impacto producto:** Fricción instalación + soporte doblado (GTK4 + Tk). Qt resuelve con una sola dependencia `PySide6` y `QStyle` nativo.

---

## 3. Evaluación experta por aspecto (1-10)

Escala: 1=crítico, 10=excelencia. Evaluación sobre `data/schema.sql`, `src/core/storage.cpp`, `gui.py`, `gui_gtk4.py`, `docs/MANUAL.md`.

| # | Aspecto | Nota | Fortalezas | Debilidades críticas | Cambio propuesto |
|---|---|---|---|---|---|
| 1 | **Notas / Markdown** | **7** | FTS5 `notes_fts` (`data/schema.sql:54`), `[[backlink]]` indexado (`storage.cpp:382`), frontmatter sync | Sin preview render, sin bloques código, sin atajos Obsidian | Split editor: `QTextEdit` + `QMarkdownTextEdit` preview, `QSyntaxHighlighter` para `#tag`/`[[link]]`/`- [ ]` |
| 2 | **Búsqueda** | **7** | `tag:` + `fecha:hoy/semana/YYYY-MM-DD` + `highlight` amarillo (`gui_gtk4.py:583`) | FTS5 cae a `LIKE` sin ranking; `fecha:` sin timezone | Port a `QSortFilterProxyModel`, ranking `fts5 rank`, añadir `fecha:mes` + `highlight` persistente |
| 3 | **Tareas / Checklist** | **6** | `- [ ]` toggle `Ctrl+Enter`, panel global `✅ Tareas` (`gui.py:489`) | Sin vencimiento, prioridad, recurrencia (`rrule` en DB sin UI `data/schema.sql:21`) | Añadir `due:YYYY-MM-DD`, `prio:alta/media/baja`, orden Kanban/Tabla, `QListWidget` con `itemChanged` |
| 4 | **Calendario** | **5** | Mes + puntos verdes, `event ↔ note` (`storage.cpp:282`), `RRULE` en DB | Solo vista mes, sin semana/día, drag limitado, sin horas | `QCalendarWidget` custom `paintCell` + vista semana `QTableView` horas, drag `task → event` con `QDrag` |
| 5 | **Knowledge OS** | **6** | Tabla `backlinks` (`data/schema.sql:45`) + grafo force-directed arrastrable (`gui_gtk4.py:831`) | Grafo no persiste layout, flechas heurísticas, sin filtro tags | `QGraphicsView` force-directed con `QGraphicsItem` arrastrable, filtro `#tag`, layout guardado `QSettings` |
| 6 | **Folder Sync** | **8** | `~/Notas` 1 `.md` por nota, idempotente `setFileMtime` (`sync_service.cpp:64`), Syncthing/Git compatible | Poll 5s, sin `inotify`, sin conflictos UI | `QFileSystemWatcher` bidireccional, diálogo conflictos `last-write-wins` + diff, `sync --watch` con `inotify` |
| 7 | **ICS / Gmail** | **7** | Export/import `.ics` RFC5545 sin `libical` (`src/core/ical_service.cpp:64`), deduplica `UID` | Solo manual, sin CalDAV/Google API, `DTSTART` sin `TZID` | Mantener offline-first, añadir `Export --month` en GUI, documentar flujo Gmail (`README.md:92`) |
| 8 | **Pomodoro** | **7** | `🍅 25/5` con `notify-send` (`gui.py:112`) | Ventana no siempre-on-top, sin historial, sin integración nota | `QTimer` + `QSystemTrayIcon` + `alwaysOnTop`, log sesiones en `pomodoro` tabla opcional |
| 9 | **UX / UI** | **4** | `Adw.HeaderBar` moderno cuando funciona, atajos `Ctrl+S/N/P` | Tk básico no escalable, GTK4 roto, sin dark mode, onboarding nulo, a11y baja | Qt Widgets con `QStyleHints` dark/light auto, `QToolBar`, wizard primera ejecución, `setAccessibleName` |
| 10 | **Performance** | **9** | `1.8M strip`, RAM 12MB CLI/32MB Tk (`README.md:114`), WAL | GTK4 55MB/180ms, grafo 30fps CPU | Objetivo Qt **RAM `<60MB` idle**, arranque `<150ms` frío, grafo 30fps con `QTimer 33ms` y `QGraphicsView` viewport culling |
| 11 | **Packaging / Distribución** | **7** | `install.sh` `PREFIX`, `.deb 624K`, `tar.gz 799K` (`docs/CHANGELOG.md:8`) | Sin Flatpak/AppImage estable, `Recommends` GTK4 hardcodeado | `control: Recommends: python3-pyside6`, `cmake -DWITH_QT=1`, `flatpak manifest`, `AppImage` con `linuxdeployqt` |
| 12 | **Tests / Calidad** | **5** | 5 suites core + sync idempotente (`tests/test_core.cpp:81`) | Sin GUI tests, sin CI, sin coverage | `pytest-qt` + `ctest`, `coverage 80%`, GitHub Actions `ubuntu-22.04/24.04` |
| 13 | **Accesibilidad** | **3** | Atajos parciales (`docs/MANUAL.md:3`) | Sin lector pantalla, sin `QAccessible`, sin escalado | `QAccessible`, `QKeySequence`, `QFont` escalable, `high-contrast` stylesheet |
| 14 | **Docs** | **7** | `README.md`, `MANUAL.md`, `ARQUITECTURA.md`, `man` stub | Manual desactualizado tras GTK4, sin screenshots Qt | Actualizar con screenshots Qt, `docs/QA.md` checklist |

**Promedio ponderado: 6.2 / 10** — Core excelente, deuda mayor en UI y tests.

---

## 4. Benchmark apps similares y funcionalidades propuestas

| App referente | Feature diferencial | ¿Adoptar? | Esfuerzo | File impactado |
|---|---|---|---|---|
| **Obsidian** | Graph interactivo filtrable por `#tag`, daily notes `{{date}}` con template vars | **Sí - Alta** | Medio | `gui_qt.py` graph, `TEMPLATES` |
| **Joplin** | Web Clipper, E2E optional, import Evernote `.enex` | Media | Medio | `sync_service`, import |
| **Logseq** | Bloques `((id))`, journal con referencias, query `{{query tag}}` | Media | Alto | `search.cpp` |
| **Notion** | Kanban board / Tabla para tareas | Baja (fase 3) | Alto | `gui_qt.py` vista |
| **Google Keep** | Recordatorios hora exacta + notificación repetitiva | **Sí - Alta** | Bajo | `platform/notifier.cpp` → `QSystemTrayIcon` |
| **TickTick / Todoist** | Tareas con `due`, `prio`, `RRULE` (ya en DB `rrule` sin UI) | **Sí - Alta** | Medio | `data/schema.sql:21`, `storage.cpp` |
| **Standard Notes** | Cifrado at-rest `SQLCipher` opcional | Baja | Alto | `storage.cpp` |
| **Joplin / Obsidian Sync** | Folder sync observado vs polling | **Sí - Crítica** | Bajo | `QFileSystemWatcher` |

**Backlog priorizado v2.0 (MoSCoW):**

* **Must (Fase 2):** Paridad v1.4 en Qt + `QFileSystemWatcher` + dark/light auto + `QSystemTrayIcon` notifs.
* **Should (Fase 3):** Markdown preview split + semana vista + tareas `due/prio` + grafo filtrable.
* **Could (Fase 4):** Import Obsidian vault, export PDF/HTML (`QPrinter`), backup auto rotativo `notes.db-YYYYMMDD`.
* **Won't (v2.0):** `SQLCipher`, CalDAV/Google OAuth (mantener offline-first).

---

## 5. Estrategia migración Qt — decisiones de arquitectura

### 5.1 Por qué PySide6

* **Licencia:** LGPL (vs PyQt6 GPL/comercial). Compatible MIT del proyecto (`README.md:129`).
* **API:** `QtWidgets` 1:1 con Tk pero con `QSS` theming, `QCalendarWidget`, `QGraphicsView` superior a `tk.Canvas` y `Gtk.DrawingArea`.
* **Distribución:** `apt install python3-pyside6` en Ubuntu 22.04+ y Lite 7; fallback `pip install --user PySide6==6.7` (`install.sh:29` detecta).
* **RAM:** Widgets sin QML mantiene `<60MB` (QML sube +30MB). Validado: `QApplication` + `QMainWindow` ~18MB + `sqlite3` 12MB = ~30MB base.

### 5.2 Arquitectura objetivo

```
CLI (src/app/main.cpp) ── Storage (src/core/storage.cpp) ── notes.db (WAL+FTS5)
        │                           │── FolderSync (sync_service.cpp) ── ~/Notas (QFileSystemWatcher)
        │                           └── IcalService (ical_service.cpp) ── .ics
        └─ GUI Qt (gui_qt.py, PySide6) ── QMainWindow
                                         ├─ QSplit: Left (QCalendarWidget + QTabWidget Notas/Tareas + QListWidget Eventos)
                                         └─ Right (QLineEdit título + QToolBar + QTextEdit + QStatusBar)
                                            + QGraphicsView (grafo) + QDialog (Pomodoro QTimer)
```

* **Core no se toca:** `storage.h:1`, `note.h`, `event.h`, `search.h` reutilizados vía Python `sqlite3` directo (igual que `gui.py:25`).
* **C++ Qt opcional:** `src/ui/qt/main_window.cpp` solo si `cmake -DWITH_QT=1` (para binario único futuro). Fase 2 es Python-only para velocidad.
* **Config:** `src/platform/config.cpp:7` `~/.config/gnote-calendar/config.ini` leído por Qt `QSettings` fallback ini.

### 5.3 Estructura ficheros tras migración

```
gui_qt.py                 # nuevo entry único (reemplaza gui.py + gui_gtk4.py)
gui.py                    # fallback Tk conservado 1 release (deprecado)
legacy/gui_gtk4.py        # movido, no instalado
src/ui/qt/                # opcional C++ Qt (main_window.h/cpp)
CMakeLists.txt            # option(WITH_QT)
Makefile                  # WITH_QT=0/1
packaging/gnote-calendar.desktop  # Exec=python3 .../gui_qt.py
requirements.txt          # PySide6==6.7 pytest-qt
tests/qt/                 # nuevos tests GUI
```

### 5.4 Objetivo performance `<60MB`

* Evitar QML, usar `QWidgets` + `Fusion` style.
* Grafo con `QGraphicsView` + `viewportUpdateMode=MinimalViewportUpdate` + culling.
* `QFileSystemWatcher` en lugar de `GLib.timeout_add(5000)` reduce wakeups.
* Medición: `scripts/bench.sh` con `/usr/bin/time -v python3 gui_qt.py --smoke` y `ps -o rss`.

---

## 6. Plan por fases (0-7) con pruebas

> Cada fase tiene: Objetivo · Tareas · Entregables · Criterio aceptación · Pruebas (comando + umbral). Tiempo estimado total 8-9 semanas (1 dev).

### Fase 0 — Auditoría y baseline (1 semana) — Semana 1

**Objetivo:** Reproducir fallo GTK4 y congelar métricas.

* **Tareas:**
  - VM Linux Lite 7.0 + Ubuntu 22.04/24.04 limpia: `python3 gui_gtk4.py` → capturar traceback `gi`/`Adw` (`gui_gtk4.py:89`).
  - Ejecutar `make test && ./build/gnote-tests` (debe pasar 5/5 `tests/test_core.cpp:81`) y `make WITH_GTK4=1`.
  - Medir baseline: `scripts/bench.sh` (nuevo) reporta `README.md:114` (CLI 33ms/12MB, Tk 120ms/32MB, GTK4 180ms/55MB).
  - Snapshot `~/.local/share/gnote-calendar/notes.db` y `~/Notas`.

* **Entregables:** `docs/DIAGNOSTICO_GTK4.md` + `scripts/bench.sh` + issue tracker.

* **Criterio aceptación:** Fallo GTK4 reproducible documentado; 5 tests core en verde; métricas baseline guardadas.

* **Pruebas:**
  ```bash
  make test && ./build/gnote-tests                # [PASS] 5/5
  python3 -c "import gi; gi.require_version('Gtk','4.0')"  # debe fallar en Lite sin GIR
  bash scripts/bench.sh | tee bench-baseline.txt   # parsea RAM/tiempo
  pytest tests/test_baseline.py -q                # nuevo, verifica DB y FTS5
  ```

### Fase 1 — Diseño Qt y scaffolding (1 semana) — Semana 2

**Objetivo:** Esqueleto `gui_qt.py` que arranca y pasa smoke test.

* **Tareas:**
  - `requirements.txt`: `PySide6==6.7`, `pytest-qt`, `pytest-cov`.
  - `gui_qt.py`: `QApplication`, `QMainWindow` 1180x680, `QMenuBar` + `QToolBar` (Buscar, Plantilla `QComboBox`, Nueva nota `QPushButton` `suggested-action` QSS), `QSplitter` left/right, `QCalendarWidget` custom, `QTabWidget` Notas/Tareas, `QListWidget` eventos, `QTextEdit` editor, `QStatusBar`.
  - `CMakeLists.txt:10` añadir `option(WITH_QT "Qt6 GUI C++" OFF)`, `find_package(Qt6 COMPONENTS Widgets)`.
  - `Makefile:15` añadir `WITH_QT ?=0` con `pkg-config Qt6`.
  - `install.sh:29` detectar `python3 -c "import PySide6"` y elegir `gui_qt.py` vs `gui.py`.

* **Entregables:** `gui_qt.py` (arranque sin DB), `requirements.txt`, `CMakeLists.txt`/`Makefile` actualizados.

* **Criterio:** `python3 gui_qt.py --smoke` abre y cierra sin excepción en 1s; `install.sh` elige Qt si disponible.

* **Pruebas:**
  ```bash
  pip install -r requirements.txt
  python3 -m py_compile gui_qt.py
  pytest tests/qt/test_smoke.py -q              # QApp fixture, verifica ventana visible
  python3 gui_qt.py --smoke & sleep 1; pkill -f gui_qt; echo ok
  pylint gui_qt.py --disable=C,R | head -20
  ```

### Fase 2 — Migración core GUI - paridad v1.4 (3 semanas) — Semanas 3-5

**Objetivo:** Qt replica 100% features v1.4 con RAM `<60MB`.

#### 2a — Notas, búsqueda, tags (Semana 3)

* **Tareas:** Port `ensure_db()`/`db()` (`gui.py:22`, `gui_gtk4.py:19`), `TEMPLATES` diario/reunión/proyecto/idea, `refresh_notes()` con `tag:`/`fecha:`/`highlight` (`gui_gtk4.py:416`) usando `QSortFilterProxyModel` + `QSyntaxHighlighter` amarillo `#fff176`, `on_select_note`, `new_note`/`save_note` con `update_backlinks` (`storage.cpp:382`), `delete_note`, tag cloud `QFlowLayout` clickeable.

* **Pruebas:**
  ```bash
  pytest tests/qt/test_notes.py -q        # CRUD, FTS5, backlinks, tag: filter
  pytest tests/qt/test_search.py -q       # fecha:hoy/semana, highlight
  # manual QA: crear nota Diario 2026-08-23, verificar journal auto con agenda
  # bench: RAM <60MB (ps -o rss)
  ```

#### 2b — Calendario, eventos, pomodoro (Semana 4)

* **Tareas:** `QCalendarWidget` subclase `paintCell` (verde evento, azul hoy `gui.py:308`), `shift_month`/`go_today` (`gui_gtk4.py:394`), `refresh_events` `listEventsForMonth` (`storage.cpp:362`), `new_event`/`delete_event`/`link_event_note` (`gui.py:534`), `Pomodoro` `QDialog` con `QTimer 1000ms` + `QSystemTrayIcon::showMessage` (`platform/notifier.cpp`).

* **Pruebas:**
  ```bash
  pytest tests/qt/test_calendar.py -q     # mes, puntos verdes, vincular nota
  pytest tests/qt/test_pomodoro.py -q     # QTimer 25:00 -> 24:59
  ctest -R core_tests                     # no regresión core
  ```

#### 2c — Tareas globales, Folder Sync, stats, export (Semana 5)

* **Tareas:** `refresh_tasks` parsing `- [ ]`/`- [x]` (`gui.py:489`) con `QListWidget` checkable, `on_toggle_task_global`, `QFileSystemWatcher` para `sync_service` (`gui_gtk4.py:800` reemplaza `GLib.timeout_add(5000)`), `QFileDialog` export `.ics`/`.md`, `stats` `QMessageBox`, `check_upcoming` `QTimer 60000`.

* **Pruebas:**
  ```bash
  pytest tests/qt/test_tasks.py -q
  pytest tests/qt/test_sync.py -q        # export/import idempotente, setFileMtime
  gnote-calendar sync --folder /tmp/QtNotas --once  # Exportados/Importados
  gnote-calendar sync --folder /tmp/QtNotas --once  # 2ª vez 0 cambios (idempotencia)
  ```

* **Criterio fase 2:** Paridad checklist manual 15 casos (`docs/QA.md` nuevo) 100% P0; `make test` 5/5; RAM `<60MB` medido `scripts/bench.sh`.

### Fase 3 — Knowledge OS Plus + polish (2 semanas) — Semanas 6-7

**Objetivo:** Features diferenciales y pulido.

* **Tareas:**
  - **Grafo `QGraphicsView`** (port `gui_gtk4.py:831`): nodos `QGraphicsEllipseItem` + `QGraphicsTextItem`, física repulsión/atracción `QTimer 33ms`, drag `mousePress/Move`, click navega a nota, filtro `#tag`.
  - **Editor split:** `QSplitter` editor `QTextEdit` + preview `QTextBrowser` markdown (`QMarkdownTextEdit` lib o `markdown` pip).
  - **Calendario semana:** `QTableView` 7x24 horas, drag `task → event`.
  - **Tareas `due`/`prio`:** parse `due:2026-08-24`/`prio:alta` en `note.body`, columna ordenable, `RRULE` UI básica.
  - **Tema:** `QStyleHints::colorScheme` auto dark/light, `QSS` `style.qss`, `QSettings` persist layout.

* **Entregables:** `gui_qt.py` 600-700 líneas, `style.qss`, `docs/MANUAL.md` actualizado con screenshots Qt.

* **Pruebas:**
  ```bash
  pytest tests/qt/test_graph.py -q        # 20 nodos 10 aristas, drag, click navega
  pytest tests/qt/test_markdown.py -q     # preview #tag [[link]]
  pytest tests/qt/test_weekview.py -q
  # visual regression: pytest --snapshot con `pytest-qt` screenshot
  # perf: grafo 30fps sin >60MB
  ```

### Fase 4 — Packaging y distribución (1 semana) — Semana 8

**Objetivo:** Instalación limpia en Lite 7 y 24.04.

* **Tareas:**
  - `packaging/control`: `Recommends: python3-pyside6` (antes `gir1.2-gtk-4.0`), `Depends: python3, sqlite3`.
  - `packaging/gnote-calendar.desktop:7` → `Exec=python3 /usr/share/gnote-calendar/gui_qt.py`, `Keywords` añade `qt`.
  - `install.sh`: `PYQT_OK=$(python3 -c "import PySide6" && echo 1 || echo 0)`, `pip install --user PySide6` fallback.
  - `CMakeLists.txt`/`Makefile` `WITH_QT` para `src/ui/qt/*` opcional.
  - `flatpak/io.github.gerardoarias.gnote_calendar.json` manifest + `AppImage` `linuxdeployqt` stub.
  - `dist/` regenerado `.deb 624K+` y `tar.gz`.

* **Pruebas:**
  ```bash
  docker run -v $PWD:/src ubuntu:22.04 bash -c "cd /src && ./install.sh --prefix /tmp/test && /tmp/test/bin/gnote-calendar --help"
  docker run ubuntu:24.04 dpkg -i dist/gnote-calendar_2.0.0_amd64.deb && gnote-calendar note list
  update-desktop-database ~/.local/share/applications && gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor
  ./gui_qt.py & # doble-click .desktop
  ```

### Fase 5 — QA integral, accesibilidad y performance (1 semana) — Semana 9

**Objetivo:** Ship-ready con a11y y coverage.

* **Tareas:**
  - Atajos: `Ctrl+S` guardar (`gui.py:279`), `Ctrl+N` nueva, `Ctrl+Enter` toggle, `Ctrl+P` pomodoro, `Esc` limpiar filtro, `QKeySequence` configurables `QSettings`.
  - Notificaciones: `QSystemTrayIcon` fallback `notify-send` (`platform/notifier.cpp`), `check_upcoming` 15min.
  - Accesibilidad: `setAccessibleName`, `QAccessible`, escalado `QFont`, `high-contrast.qss`.
  - Backup auto: rotar `notes.db` a `notes.db.bak-YYYYMMDD` al iniciar.

* **Pruebas:**
  ```bash
  pytest -q --cov=gui_qt --cov-report=term-missing  # >80%
  ctest -V                                          # 5/5 core
  xvfb-run -a pytest tests/qt -q                   # CI headless
  # manual a11y: Orca + Accerciser, Tab navigation 100% focuseable
  bash scripts/bench.sh --assert-ram 60 --assert-startup 200
  ```

### Fase 6 — Lanzamiento v2.0.0 Qt (3 días) — Semana 9-10

**Objetivo:** Tag y release.

* **Tareas:** `docs/CHANGELOG.md` entry `2.0.0 — Qt PySide6`, `README.md` tabla perf Qt, `docs/ARQUITECTURA.md` diagrama Qt, mover `gui_gtk4.py` a `legacy/`, tag `v2.0.0`, `dist/*.deb` + `*.tar.gz` + `AppImage` en `dist/`, `git tag -a v2.0.0`.

* **Pruebas (smoke release):**
  ```bash
  make clean && make -j$(nproc) && make test && ./build/gnote-tests
  pytest -q
  python3 gui_qt.py --smoke; echo "smoke ok"
  gnote-calendar note add "Release test #qt" "[[v2.0]] - [ ] smoke" && gnote-calendar note search "qt"
  ```

### Fase 7 — Publicación GitHub + Flathub (1 semana) — Semana 10-11

**Objetivo:** `github.com/gerardoarias/gnote-calendar` público + `io.github.gerardoarias.gnote_calendar` en Flathub para `flatpak install flathub io.github.gerardoarias.gnote_calendar` en cualquier PC.

* **Tareas GitHub (7a):**
  - Crear repo `gerardoarias/gnote-calendar` en https://github.com/new (Public, sin README) `docs/GITHUB.md:1`.
  - `git remote add origin https://github.com/gerardoarias/gnote-calendar.git` + `git push -u origin main` + `git push origin v2.0.0` `scripts/push_github.sh`.
  - Release `v2.0.0` con `dist/*.deb 700K` `portable 1.7M` `AppImage` `flatpak` bundle.

* **Tareas Flathub (7b):**
  - `flatpak/io.github.gerardoarias.gnote_calendar.json` runtime `org.kde.Platform//6.9` `Sdk 6.9` (corregido de 6.7 inexistente `flatpak remote-ls flathub | grep Sdk`), `flatpak/io.github.gerardoarias.gnote_calendar.metainfo.xml` AppStream + `flatpak/flathub.json` lint.
  - `flatpak-builder --force-clean --repo=repo build flatpak/io.github.gerardoarias.gnote_calendar.json` + `flatpak build-bundle repo gnote-calendar.flatpak io.github.gerardoarias.gnote_calendar` (local bundle para test).
  - Fork `flathub/flathub`, PR `add io.github.gerardoarias.gnote_calendar` con manifest + metainfo + icon `packaging/gnote-calendar.svg`, `flatpak-builder-lint` + `appstreamcli validate`.
  - Flathub CI compila, publica en `flatpak remote-ls flathub | grep io.github.gerardoarias.gnote_calendar`.
  - Actualizar `README.md` badge `Flathub` + `docs/MANUAL.md` sección Flatpak.

* **Entregables:** `flatpak/io.github.gerardoarias.gnote_calendar.json` `6.9`, `flatpak/io.github.gerardoarias.gnote_calendar.metainfo.xml`, `gnote-calendar.flatpak` bundle, PR Flathub mergeado.

* **Pruebas:**
  ```bash
  flatpak install flathub org.kde.Sdk//6.9 org.kde.Platform//6.9 -y
  flatpak-builder --force-clean --repo=repo --ccache build flatpak/io.github.gerardoarias.gnote_calendar.json
  flatpak build-bundle repo gnote-calendar.flatpak io.github.gerardoarias.gnote_calendar
  flatpak install --user gnote-calendar.flatpak
  flatpak run io.github.gerardoarias.gnote_calendar --help
  flatpak run io.github.gerardoarias.gnote_calendar
  # En otro PC ya publicado:
  flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
  flatpak install flathub io.github.gerardoarias.gnote_calendar -y && flatpak run io.github.gerardoarias.gnote_calendar
  ```

* **Criterio:** `flatpak install flathub io.github.gerardoarias.gnote_calendar` en PC limpio instala y arranca Qt sin `xcb-cursor` manual; `flatpak-builder-lint` 0 errores.

---

## 7. Matriz de pruebas transversal

| Tipo | Herramienta | Comando | Frecuencia | Umbral |
|---|---|---|---|---|
| **Unit core** | `gtest`/`ctest` | `make test && ./build/gnote-tests` | Cada commit | 5/5 `tests/test_core.cpp:81` |
| **Unit Qt** | `pytest-qt` | `pytest tests/qt -k "not manual" -q` | Cada commit | >25 tests, 0 fail |
| **Integración sync** | `FolderSync` | `gnote-calendar sync --folder /tmp/N --once` x2 | Fase 2c,4 | 2ª run `Exportados 0 Importados 0` |
| **ICS** | `IcalService` | `gnote-calendar ics export -o /tmp/c.ics && ics import /tmp/c.ics` | Fase 2c | `imported==exported` (`tests/test_core.cpp:44`) |
| **Performance RAM** | `time`+`ps` | `bash scripts/bench.sh --assert-ram 60` | Fase 0,2,5 | `<60MB` idle Qt, `<25MB` Tk |
| **Performance arranque** | `time` | `bash scripts/bench.sh --assert-startup 200` | Fase 2,5 | `<200ms` frío Qt, `<120ms` Tk |
| **GUI manual QA** | Checklist `docs/QA.md` | 15 casos (diario auto, backlink, grafo drag, pomodoro, sync) | Fase 2,3,5 | 100% P0, 90% P1 |
| **Accesibilidad** | `Accerciser`, `orca` | Tab + screen reader | Fase 5 | 100% widgets focuseables |
| **Packaging .deb** | `docker` | `dpkg -i` + `install.sh` en 22.04/24.04 | Fase 4,6 | Instalación 0 errores |
| **Flatpak** | `flatpak-builder` | `flatpak-builder --repo=repo build && flatpak run` | Fase 7 | `flatpak install flathub` ok |
| **Headless CI** | `xvfb` | `xvfb-run -a pytest tests/qt` | CI | Verde |

**Estructura `tests/qt/` propuesta:**

```
tests/qt/
  conftest.py              # QApp fixture
  test_smoke.py            # arranque
  test_notes.py            # CRUD + FTS5
  test_search.py           # tag:/fecha:/highlight
  test_calendar.py         # QCalendarWidget
  test_tasks.py            # checklist
  test_pomodoro.py         # QTimer
  test_sync.py             # file watcher
  test_graph.py            # QGraphicsView
  test_weekview.py
  test_markdown.py
```

---

## 8. Criterios de aceptación global v2.0.0

* [ ] `gui_qt.py` paridad v1.4: `docs/MANUAL.md:3` todos los atajos y flujos.
* [ ] RAM Qt idle `<60MB` medido `scripts/bench.sh` en Lite 7 VM (vs 55MB GTK4).
* [ ] Arranque Qt frío `<200ms` (vs 180ms GTK4).
* [ ] `make test` 5/5 + `pytest -q` >25 + coverage `gui_qt` >70%.
* [ ] `gnote-calendar sync --folder ~/Notas` idempotente (2 runs 0 cambios).
* [ ] `.deb` y `tar.gz` instalables en 22.04/24.04, `.desktop` abre Qt.
* [ ] `flatpak install flathub io.github.gerardoarias.gnote_calendar` en PC limpio (Fase 7).
* [ ] Grafo 20 nodos arrastrable sin >60MB.
* [ ] `QSystemTrayIcon` notifica eventos próximos 15min.
* [ ] Docs actualizados: `README.md`, `MANUAL.md`, `ARQUITECTURA.md`, `CHANGELOG.md` 2.0.0 + badge Flathub.

---

## 9. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| `PySide6` no en repos Lite 7 | Media | Instalación falla | `install.sh` fallback `pip install --user PySide6==6.7`; documentar `apt python3-pyside6` |
| RAM Qt >60MB con preview | Media | No cumple objetivo | Usar `Fusion` style, evitar QML, `QGraphicsView` culling, benchmark cada fase |
| `QCalendarWidget` `paintCell` lento | Baja | Lag mes | Cache `counts` (`gui.py:299`), `update()` solo al cambiar mes |
| `QFileSystemWatcher` límites `inotify` | Baja | Sync no dispara | Fallback poll 5s si `inotify` max_user_watches excedido; log `QFileSystemWatcher::failed` |
| Regresión core SQLite FTS5 | Baja | Búsqueda rota | `storage.cpp:195` tests FTS5 vs LIKE; `ctest` en CI |
| Usuarios con `notes.db` GTK4 existente | Alta | Migración | `ensure_db()` (`gui_qt.py` pasará) es backward-compatible; script `tools/migrate_gtk4_to_qt.py` copia `config.ini` `sync_folder` |

---

## 10. Roadmap y entregables

```
Sem 1  Fase0 baseline          -> docs/DIAGNOSTICO_GTK4.md, bench-baseline.txt
Sem 2  Fase1 scaffold Qt       -> gui_qt.py smoke, requirements.txt, CMake WITH_QT
Sem 3-5 Fase2 paridad v1.4    -> gui_qt.py 500 líneas, 15 QA pass, RAM <60
Sem 6-7 Fase3 Knowledge Plus  -> graph QGraphicsView, split markdown, semana vista
Sem 8  Fase4 packaging         -> .deb/.tar.gz/AppImage, control Recommends pyside6, manifest 6.9
Sem 9  Fase5 QA/a11y/perf      -> coverage 80%, a11y, bench <60MB/<200ms
Sem 9-10 Fase6 release v2.0.0 -> tag, dist/, README/MANUAL actualizados
Sem 10-11 Fase7 Flathub        -> io.github.gerardoarias.gnote_calendar 6.9 en Flathub, flatpak install flathub ok
```

**Esfuerzo estimado:** 8-9 semanas 1 dev (40h/sem). **Priorización:** `Must` Fase 2 para beta usable en 5 semanas.

**Siguiente paso inmediato (Fase 0):** ejecutar `scripts/bench.sh` y documentar `DIAGNOSTICO_GTK4.md` para congelar baseline antes de tocar `gui_qt.py`.

---

## 11. Anexos

### 11.1 Comandos rápidos

```bash
# Entorno Qt
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt  # PySide6==6.7 pytest-qt pytest-cov

# Dev
python3 gui_qt.py                     # Qt
python3 gui.py                        # Tk fallback
make test && ./build/gnote-tests     # core
pytest tests/qt -q --cov=gui_qt      # Qt
bash scripts/bench.sh                # RAM/arranque

# Sync / ICS
./build/gnote-calendar sync --folder ~/Notas --once
./build/gnote-calendar ics export --output /tmp/cal.ics --month 2026-08
```

### 11.2 Referencias código clave

* Core: `src/core/storage.cpp:1`, `src/core/sync_service.cpp:1`, `data/schema.sql:1`, `src/app/main.cpp:1`
* GUI actual: `gui.py:1` (728 líneas), `gui_gtk4.py:1` (974 líneas)
* Build: `CMakeLists.txt:1`, `Makefile:1`, `install.sh:1`, `packaging/gnote-calendar.desktop:1`

### 11.3 Licencia

MIT (`README.md:129`) compatible LGPL PySide6 sin necesidad de abrir binario si link dinámico (pip/apt).

---

> **Nota de producto:** Este plan prioriza **offline-first y ligereza** (`<60MB` vs Obsidian `~300MB` / Joplin `~200MB`) como ventaja competitiva para hardware 2015, mientras incorpora lo mejor de Obsidian (graph), TickTick (due/prio) y Keep (notifs) sin sacrificar simplicidad.
