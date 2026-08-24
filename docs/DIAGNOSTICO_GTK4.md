# Diagnóstico GTK4 — gnote-calendar v1.4

**Fecha:** 2026-08-23
**Ramas:** `gui_gtk4.py` (974 líneas), `gui.py` (728 líneas)
**Sistema prueba:** Linux Lite 7.0 / Ubuntu 22.04 LTS (Noble) — VM limpia
**Comando:** `python3 gui_gtk4.py` vs `python3 gui.py`

## 1. Reproducción

### 1.1 Entorno sin GIR
```bash
python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')"
# Error: ValueError: Namespace Gtk not available
python3 gui_gtk4.py
# GTK4/Adw no disponible (Namespace Gtk not available, ...), usando fallback Tk...
# -> os.execv(gui.py) pierde argv y no logea a usuario
```

`gui_gtk4.py:89-103` captura genérica `except Exception as e: GTK4_AVAILABLE=False` y hace `execv`. No hay diálogo al usuario; si `gui.py` también falla, el usuario ve salida vacía.

### 1.2 Con GIR pero libadwaita 1.2 (Ubuntu 22.04)
```bash
apt show gir1.2-adw-1  # 1.2.x en 22.04, 1.4 en 24.04
python3 gui_gtk4.py
# Adw.init() ok, pero botones con css "success" no existen -> invisibles
# Calendar botones: gui_gtk4.py:378 b.add_css_class("success") -> no efecto
```

### 1.3 Diálogos async rotos
* `new_event()` `gui_gtk4.py:651` crea `Adw.MessageDialog` y llama `dlg.choose(None, lambda *_: None)` sin esperar respuesta; inmediatamente inserta evento `10:00` hardcodeado sin título del usuario.
* `export_ics()` `gui_gtk4.py:688` usa `Gtk.FileDialog.save()` async correctamente, pero `new_note()` `gui_gtk4.py:511` crea `Gtk.Dialog` y hace `dlg.present()` + `dlg.close()` sin esperar entrada → título siempre `title_base`.
* Resultado: usuario reporta "no funciona correctamente" — crea notas/eventos con datos dummy.

### 1.4 Búsqueda fecha NameError
`gui_gtk4.py:447` usa `timedelta` sin importar en ese scope:
```python
if fecha=="semana": is_week=True
...
cutoff=_date.today()-timedelta(days=7)  # NameError: name 'timedelta' is not defined
```
Solo `from datetime import datetime` importado arriba `gui_gtk4.py:7`; `timedelta` no importado globalmente. Causa crash al buscar `fecha:semana`.

### 1.5 Performance
* Medido `scripts/bench.sh`: GTK4 `~180ms/55MB`, Tk `~120ms/32MB`, CLI `33ms/12MB` (`README.md:119`).
* Física grafo `GLib.timeout_add(33)` 30fps `gui_gtk4.py:946` mantiene CPU 5-8% idle.

## 2. Causa raíz arquitectura

| Factor | Detalle |
|--------|---------|
| **Dependencia sistema frágil** | `WITH_GTK4` auto-detect `Makefile:31` no instala `gir1.2-gtk-4.0 gir1.2-adw-1`; `install.sh:29` detecta pero no instala. |
| **Dos GUIs a mantener** | `gui.py` y `gui_gtk4.py` duplican 80% lógica (search, backlinks, sync) pero divergen en bugs. |
| **Async GTK4 mal usado** | `Gtk.FileDialog` async requiere `Gio.AsyncResult` correcto; `Adw.MessageDialog` no es para input texto. |
| **Testing nulo** | `tests/test_core.cpp:81` solo core; sin `pytest-qt` para GUI. |

## 3. Baseline métricas (congeladas pre-migración)

```
Binario strip: 1.8M (BUILD/gnote-calendar)
CLI RAM idle: 12M
GUI Tk RAM idle: 32M, arranque 120ms
GUI GTK4 RAM idle: 55M, arranque 180ms
DB: ~/.local/share/gnote-calendar/notes.db WAL
make test: 5/5 PASS
```

Comando para re-medir post Qt: `bash scripts/bench.sh --assert-ram 60 --assert-startup 200`

## 4. Recomendación

Migrar a **PySide6 Qt Widgets** con un único `gui_qt.py` y conservar `gui.py` 1 release como fallback. Objetivo `<60MB` alcanzable con Widgets (no QML). Ver `plan_accion.md` Fases 0-6.
