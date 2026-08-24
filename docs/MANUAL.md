# Manual gnote-calendar

## 1. Atajos

- `Ctrl+N` nueva nota (usa plantilla seleccionada)
- `Ctrl+S` guardar nota actual (crea si no existe)
- `Ctrl+Enter` toggle tarea en línea actual (`- [ ]` <-> `- [x]`)
- `Ctrl+P` pomodoro
- `Esc` en búsqueda limpia filtro
- Doble click en calendario -> selecciona día
- Doble click en tarea global -> completa/incompleta
- Doble click en evento -> detalle

## 2. Sintaxis notas

- `#tag` etiqueta (aparece en tag cloud)
- `[[Nombre Nota]]` backlink (grafo)
- `- [ ] texto` tarea pendiente
- `- [x] texto` tarea hecha
- Markdown básico en editor (preview no render, texto plano ligero)

## 3. Plantillas + Journal diario auto

- **Diario:** `#diario 2026-08-23` se crea solo al iniciar con agenda hoy + pendientes vencidos. Usa plantilla `Diario` con mañana/tarde/gratitud.
- **Reunión:** agenda + acuerdos checklist
- **Proyecto:** objetivo + tareas + enlaces `[[link]]`
- **Idea:** captura rápida
- Selecciona plantilla arriba y `Nueva nota`.

## 4. Pomodoro

1. `🍅 Pomodoro` -> `Iniciar`
2. Trabaja 25min -> notify + auto switch a 5min descanso
3. `Pausa`/`Reset` disponibles

## 5. Sincronizar Gmail + Folder Sync

- **Gmail:** `Export .ics` / `Import .ics` estándar, sin internet.
- **Folder Sync (Knowledge OS):** `~/Notas` 1 `.md` por nota con frontmatter:
  ```
  ---
  id: 42
  title: "Reunión"
  tags: [trabajo]
  created: 2026-08-23T10:00:00Z
  updated: 2026-08-23T11:00:00Z
  ---
  Cuerpo...
  ```
  CLI: `gnote-calendar sync --folder ~/Notas` (idempotente, `setFileMtime`), `--watch` poll 2s.
  GUI: `📁 Folder Sync` → `Elegir carpeta` → `Sincronizar ahora` (poll 5s auto). Compatible Syncthing/Nextcloud/Git.
  Búsqueda: `tag:`, `fecha:hoy/semana/YYYY-MM-DD` (`refresh_notes` `gui_gtk4.py:416`), highlight amarillo.
  Grafo: `🕸️ Grafo` force-directed arrastrable (repulsión/atracción), click navega.
- **Backlinks:** `backlinks` tabla `src_id→dst_title`, `getNotesLinkingTo` `src/core/storage.cpp:58`, status `enlazada por #x`, diario auto incluye agenda.

## 6. CLI avanzado

```bash
gnote-calendar note search "tag:trabajo reunión"
gnote-calendar event add "X" "2026-08-24 10:00" "2026-08-24 11:00" --note 2
gnote-calendar ics export --output /tmp/mes.ics --month 2026-08
```

## 7. Backup

```bash
cp ~/.local/share/gnote-calendar/notes.db ~/backup-$(date +%F).db
# o con CLI: sqlite3 ~/.local/share/gnote-calendar/notes.db .dump > backup.sql
```

## 8. Solución problemas

- **Doble click no abre:** usar `~/Desktop/gnote-calendar.desktop` (GUI) no el binario `build/gnote-calendar`
- **Falta icono en menú:** `update-desktop-database ~/.local/share/applications`
- **Compila GTK nativa:** `sudo apt install libgtkmm-3.0-dev && make WITH_GTK=1`
