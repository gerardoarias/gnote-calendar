#!/usr/bin/env python3
# gnote-calendar GUI GTK4 + libadwaita - Knowledge OS v1.3 (Etapa 1)
# Fallback automático a gui.py (Tk) si GTK4/Adw no disponible
# <55MB RAM, moderno GNOME, mantiene core C++ SQLite

import os, sys, re, subprocess, time, calendar, sqlite3
from datetime import datetime

DB_PATH = os.path.expanduser("~/.local/share/gnote-calendar/notes.db")
BIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build/gnote-calendar")
TEMPLATES = {
    "Diario": "#diario {date}\n## Mañana ☀️\n- [ ] Revisar agenda\n\n## Tarde\n- [ ] \n\n## Notas del día\n\n## Gratitud\n- \n",
    "Reunión": "#reunión #{date} {title}\n**Fecha:** {date}  **Lugar:** \n\n## Asistentes\n- \n\n## Agenda\n1. \n2. \n\n## Acuerdos\n- [ ] \n\n## Notas\n",
    "Proyecto": "#proyecto {title}\n## 🎯 Objetivo\n\n\n## 📋 Tareas\n- [ ] Definir alcance\n- [ ] \n\n## 🔗 Enlaces\n[[Nota relacionada]]\n\n## 📝 Log\n",
    "Idea rápida": "#idea {title}\n> {date}\n\n**Idea:** \n\n**Pasos:**\n- [ ] \n",
    "Vacía": ""
}

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(BIN_PATH):
        subprocess.run([BIN_PATH, "note", "list"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try: cur.execute("SELECT count(*) FROM notes")
    except:
        schema_path = os.path.join(os.path.dirname(__file__), "data/schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path) as f: cur.executescript(f.read())
        else:
            cur.executescript("""
            CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '', location TEXT DEFAULT '', start_ts INTEGER NOT NULL, end_ts INTEGER NOT NULL, rrule TEXT DEFAULT '', note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL, uid TEXT UNIQUE, source TEXT DEFAULT 'local', created_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_ts);
            """)
        con.commit()
    con.close()

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def update_backlinks(note_id, body):
    try:
        con = db(); cur = con.cursor()
        cur.execute("DELETE FROM backlinks WHERE src_id=?", (note_id,))
        for m in re.findall(r"\[\[([^\]]+)\]\]", body):
            cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (note_id, m.strip()))
        con.commit(); con.close()
    except: pass

def ensure_daily_note():
    today = datetime.now().strftime("%Y-%m-%d")
    title = today
    con = db(); cur = con.cursor()
    cur.execute("SELECT id FROM notes WHERE title=?", (title,))
    row = cur.fetchone()
    if row:
        con.close(); return row[0]
    # crear nota diaria con agenda + tareas vencidas
    body = TEMPLATES["Diario"].format(date=today, title=title)
    # agregar eventos de hoy
    start = int(datetime.now().replace(hour=0, minute=0, second=0).timestamp())
    end = int(datetime.now().replace(hour=23, minute=59, second=59).timestamp())
    cur.execute("SELECT title, start_ts FROM events WHERE start_ts>=? AND start_ts<=? ORDER BY start_ts LIMIT 5", (start, end))
    evs = cur.fetchall()
    if evs:
        body += "\n## 📅 Hoy\n"
        for e in evs:
            body += f"- {datetime.fromtimestamp(e['start_ts']).strftime('%H:%M')} {e['title']}\n"
    # tareas vencidas
    cur.execute("SELECT title, body FROM notes WHERE body LIKE '%- [ ]%'")
    pend = []
    for r in cur.fetchall():
        for line in r["body"].splitlines():
            if line.startswith("- [ ]"): pend.append(f"- [ ] {line[4:][:40]} — {r['title'][:16]}")
            if len(pend) >= 3: break
    if pend:
        body += "\n## ⚠️ Pendientes\n" + "\n".join(pend[:5]) + "\n"
    now = int(time.time())
    cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (title, body, now, now))
    nid = cur.lastrowid
    update_backlinks(nid, body)
    con.commit(); con.close()
    return nid

# Intento GTK4/Adw, fallback a Tk
try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw, Gio, GLib, Pango
    GTK4_AVAILABLE = True
except Exception as e:
    print(f"GTK4/Adw no disponible ({e}), usando fallback Tk...", file=sys.stderr)
    GTK4_AVAILABLE = False

if not GTK4_AVAILABLE:
    # fallback exec gui.py Tk
    tk_path = os.path.join(os.path.dirname(__file__), "gui.py")
    os.execv(sys.executable, [sys.executable, tk_path] + sys.argv[1:])
    sys.exit(0)

Adw.init()

def toggle_task_line(line):
    if re.match(r"^- \[ \]", line): return re.sub(r"^- \[ \]", "- [x]", line, count=1)
    if re.match(r"^- \[[xX]\]", line): return re.sub(r"^- \[[xX]\]", "- [ ]", line, count=1)
    return line

class PomodoroWindow(Adw.Window):
    def __init__(self, app):
        super().__init__(application=app, title="Pomodoro — 25:00", default_width=280, default_height=180)
        self.remaining = 25*60
        self.running = False
        self.mode = "work"
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        self.set_content(box)
        self.label = Gtk.Label(label="25:00")
        self.label.add_css_class("title-1")
        box.append(self.label)
        self.mode_label = Gtk.Label(label="🍅 Trabajo — enfócate")
        box.append(self.mode_label)
        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.CENTER)
        b1 = Gtk.Button(label="Iniciar", css_classes=["suggested-action"])
        b1.connect("clicked", lambda _: self.start())
        b2 = Gtk.Button(label="Pausa")
        b2.connect("clicked", lambda _: self.pause())
        b3 = Gtk.Button(label="Reset")
        b3.connect("clicked", lambda _: self.reset())
        btns.append(b1); btns.append(b2); btns.append(b3)
        box.append(btns)
        GLib.timeout_add(1000, self.tick)
    def start(self): self.running=True
    def pause(self): self.running=False
    def reset(self):
        self.running=False; self.mode="work"; self.remaining=25*60
        self.label.set_label("25:00"); self.mode_label.set_label("🍅 Trabajo"); self.set_title("Pomodoro — 25:00")
    def tick(self):
        if self.running and self.remaining>0:
            self.remaining-=1
            m,s=divmod(self.remaining,60)
            self.label.set_label(f"{m:02d}:{s:02d}")
            self.set_title(f"Pomodoro — {m:02d}:{s:02d}")
            if self.remaining==0:
                self.running=False
                try: subprocess.run(["notify-send","Pomodoro","¡Tiempo terminado!"], timeout=2)
                except: pass
                dlg = Adw.MessageDialog(transient_for=self, heading="Pomodoro", body="¡Tiempo terminado! " + ("Descanso 5 min" if self.mode=="work" else "Vuelve al trabajo"))
                dlg.add_response("ok","OK", appearance=Adw.ResponseAppearance.SUGGESTED)
                dlg.present()
                if self.mode=="work": self.mode="break"; self.remaining=5*60; self.mode_label.set_label("☕ Descanso 5 min")
                else: self.mode="work"; self.remaining=25*60; self.mode_label.set_label("🍅 Trabajo")
        return True

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="gnote-calendar — Notas y Calendario", default_width=1180, default_height=680)
        self.current_note_id = None
        self.selected_date = datetime.now()
        self.pomodoro_win = None

        # Header
        header = Adw.HeaderBar()
        # Search
        self.search_entry = Gtk.SearchEntry(placeholder_text="Buscar #tag texto…", hexpand=False, width_request=260)
        self.search_entry.connect("search-changed", lambda _: self.refresh_notes())
        header.pack_start(self.search_entry)
        # Template combo
        self.template_combo = Gtk.DropDown.new_from_strings(list(TEMPLATES.keys()))
        self.template_combo.set_selected(0)
        header.pack_start(self.template_combo)
        btn_new = Gtk.Button(label="Nueva nota", css_classes=["suggested-action"])
        btn_new.connect("clicked", lambda _: self.new_note())
        header.pack_start(btn_new)

        btn_save = Gtk.Button(label="Guardar")
        btn_save.connect("clicked", lambda _: self.save_note())
        header.pack_start(btn_save)

        # Right header actions
        btn_pomodoro = Gtk.Button(label="🍅")
        btn_pomodoro.set_tooltip_text("Pomodoro (Ctrl+P)")
        btn_pomodoro.connect("clicked", lambda _: self.open_pomodoro())
        header.pack_end(btn_pomodoro)

        menu = Gio.Menu()
        menu.append("📁 Folder Sync", "app.folder_sync")
        menu.append("📊 Estadísticas", "app.stats")
        menu.append("🕸️ Grafo", "app.graph")
        menu.append("Exportar .md", "app.export_md")
        menu.append("Exportar .ics → Gmail", "app.export_ics")
        menu.append("Importar .ics", "app.import_ics")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_btn)

        # Main layout
        self.content = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, shrink_start_child=False, shrink_end_child=False)
        self.set_content(Gtk.Box(orientation=Gtk.Orientation.VERTICAL))
        self.get_content().append(header)
        self.get_content().append(self.content)

        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        left_box.set_size_request(380, -1)
        self.content.set_start_child(left_box)

        # Calendar header
        cal_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.cal_label = Gtk.Label(label="", css_classes=["heading"])
        cal_head.append(self.cal_label)
        self.cal_label.set_hexpand(True)
        self.cal_label.set_xalign(0)
        btn_today = Gtk.Button(label="Hoy")
        btn_today.connect("clicked", lambda _: self.go_today())
        cal_head.append(btn_today)
        btn_prev = Gtk.Button(icon_name="go-previous-symbolic")
        btn_prev.connect("clicked", lambda _: self.shift_month(-1))
        btn_next = Gtk.Button(icon_name="go-next-symbolic")
        btn_next.connect("clicked", lambda _: self.shift_month(1))
        cal_head.append(btn_prev); cal_head.append(btn_next)
        left_box.append(cal_head)

        # Calendar grid
        self.cal_grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=True, column_spacing=2, row_spacing=2)
        left_box.append(self.cal_grid)
        for i, d in enumerate(["Lu","Ma","Mi","Ju","Vi","Sá","Do"]):
            lbl = Gtk.Label(label=d, css_classes=["dim-label"])
            self.cal_grid.attach(lbl, i, 0, 1, 1)
        self.cal_buttons = []
        for r in range(6):
            row=[]
            for c in range(7):
                b = Gtk.Button(label="", has_frame=False)
                b.add_css_class("card")
                b.connect("clicked", lambda btn, r=r,c=c: self.on_cal_click(r,c))
                self.cal_grid.attach(b, c, r+1, 1, 1)
                row.append(b)
            self.cal_buttons.append(row)

        # Tag cloud
        tag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tag_box.append(Gtk.Label(label="Tags:", css_classes=["dim-label"]))
        self.tag_flow = Gtk.FlowBox(max_children_per_line=6, selection_mode=Gtk.SelectionMode.NONE)
        self.tag_flow.set_hexpand(True)
        tag_box.append(self.tag_flow)
        btn_clear = Gtk.Button(label="✕", has_frame=False)
        btn_clear.set_tooltip_text("Limpiar filtro")
        btn_clear.connect("clicked", lambda _: self.search_entry.set_text(""))
        tag_box.append(btn_clear)
        left_box.append(tag_box)

        # Notebook Notas / Tareas
        self.left_nb = Gtk.Notebook()
        left_box.append(self.left_nb)
        # Tab Notas: ListBox
        tab_notes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.notes_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE, css_classes=["boxed-list"])
        self.notes_list.connect("row-selected", lambda _, row: self.on_select_note(row))
        scroll_notes = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER, vscrollbar_policy=Gtk.PolicyType.AUTOMATIC)
        scroll_notes.set_child(self.notes_list)
        scroll_notes.set_vexpand(True)
        # Need to set size
        scroll_notes.set_min_content_height(220)
        tab_notes_box.append(scroll_notes)
        self.left_nb.append_page(tab_notes_box, Gtk.Label(label="📝 Notas"))

        # Tab Tareas
        tab_tasks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.task_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE, css_classes=["boxed-list"])
        self.task_list.connect("row-activated", lambda _, row: self.on_toggle_task_global(row))
        scroll_tasks = Gtk.ScrolledWindow(vexpand=True)
        scroll_tasks.set_child(self.task_list)
        scroll_tasks.set_min_content_height(220)
        tab_tasks_box.append(scroll_tasks)
        btn_upd = Gtk.Button(label="Actualizar")
        btn_upd.connect("clicked", lambda _: self.refresh_tasks())
        tab_tasks_box.append(btn_upd)
        self.left_nb.append_page(tab_tasks_box, Gtk.Label(label="✅ Tareas"))

        # Eventos del mes
        left_box.append(Gtk.Label(label="Eventos del mes", css_classes=["heading"], xalign=0))
        self.event_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE, css_classes=["boxed-list"])
        self.event_list.connect("row-activated", lambda _, row: self.on_edit_event(row))
        scroll_ev = Gtk.ScrolledWindow(min_content_height=120, max_content_height=140)
        scroll_ev.set_child(self.event_list)
        left_box.append(scroll_ev)
        ev_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_ne = Gtk.Button(label="Nuevo evento")
        b_ne.connect("clicked", lambda _: self.new_event())
        b_de = Gtk.Button(label="Borrar")
        b_de.connect("clicked", lambda _: self.delete_event())
        b_ln = Gtk.Button(label="Vincular nota")
        b_ln.connect("clicked", lambda _: self.link_event_note())
        ev_btns.append(b_ne); ev_btns.append(b_de); ev_btns.append(b_ln)
        left_box.append(ev_btns)

        # Right editor
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        right_box.set_hexpand(True)
        self.content.set_end_child(right_box)
        self.content.set_resize_end_child(True)

        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hdr.append(Gtk.Label(label="Título:"))
        self.title_entry = Gtk.Entry(hexpand=True, placeholder_text="Título de la nota…")
        self.title_entry.connect("changed", lambda _: self.auto_tag_hint())
        hdr.append(self.title_entry)
        right_box.append(hdr)

        # toolbar
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        for label, cb in [("☐ Tarea", self.insert_task), ("✓ Toggle", self.toggle_task_in_editor), ("🔗 [[link]]", self.insert_link), ("#tag", self.insert_tag)]:
            b = Gtk.Button(label=label)
            b.connect("clicked", lambda _, cb=cb: cb())
            tb.append(b)
        right_box.append(tb)

        self.text_view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD, left_margin=8, right_margin=8, top_margin=8, bottom_margin=8, hexpand=True, vexpand=True)
        self.text_view.set_monospace(False)
        self.text_view.get_buffer().connect("changed", lambda _: self.auto_tag_hint())
        scroll_text = Gtk.ScrolledWindow(vexpand=True)
        scroll_text.set_child(self.text_view)
        right_box.append(scroll_text)

        self.status_label = Gtk.Label(label="Listo. Usa #tag y [[enlace]]  •  Ctrl+S guardar  •  Ctrl+Enter toggle", css_classes=["dim-label"], xalign=0)
        right_box.append(self.status_label)

        # Key controller
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self.on_key)
        self.add_controller(key)

        # Actions for menu
        for name, cb in [("folder_sync", self.show_folder_sync), ("stats", self.show_stats), ("graph", self.show_graph), ("export_md", self.export_markdown), ("export_ics", self.export_ics), ("import_ics", self.import_ics)]:
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", lambda _, __, cb=cb: cb())
            app.add_action(act)

        # Knowledge OS: diario auto + backlinks ya migrados en storage
        try: ensure_daily_note()
        except: pass
        self.refresh_notes()
        self.refresh_calendar()
        self.refresh_tasks()
        self.refresh_tag_cloud()
        GLib.timeout_add(60000, self.check_upcoming)
        # Folder sync auto poll cada 5s si hay carpeta configurada
        GLib.timeout_add(5000, self.auto_folder_sync)

    def on_key(self, _, keyval, keycode, state):
        if state & Gtk.EventControllerKey.get_current_event_state and keyval == 115 and state & 4: # Ctrl+S
            self.save_note(); return True
        return False

    # Calendar
    def refresh_calendar(self):
        dt = self.selected_date
        self.cal_label.set_label(f"{calendar.month_name[dt.month]} {dt.year}")
        con = db(); cur = con.cursor()
        start = int(datetime(dt.year, dt.month, 1).timestamp())
        end = int(datetime(dt.year+1,1,1).timestamp()) if dt.month==12 else int(datetime(dt.year, dt.month+1,1).timestamp())
        cur.execute("SELECT start_ts FROM events WHERE start_ts>=? AND start_ts<?", (start,end))
        counts={}
        for r in cur.fetchall(): counts[datetime.fromtimestamp(r[0]).day] = counts.get(datetime.fromtimestamp(r[0]).day,0)+1
        con.close()
        first_wd, days = calendar.monthrange(dt.year, dt.month)
        day=1; today=datetime.now()
        for r in range(6):
            for c in range(7):
                b=self.cal_buttons[r][c]; idx=r*7+c
                if idx < first_wd or day>days:
                    b.set_label(""); b.set_sensitive(False)
                else:
                    b.set_label(str(day)); b.set_sensitive(True)
                    b.day = day
                    # style
                    for cls in ["suggested-action","destructive-action","card"]: b.remove_css_class(cls)
                    is_today = (day==today.day and dt.month==today.month and dt.year==today.year)
                    has_evt = day in counts
                    if is_today: b.add_css_class("suggested-action")
                    elif has_evt: b.add_css_class("card"); b.add_css_class("success")
                    elif self.selected_date.day==day: b.add_css_class("card")
                    day+=1
        self.refresh_events()

    def on_cal_click(self, r,c):
        b=self.cal_buttons[r][c]
        if not b.get_sensitive(): return
        self.selected_date = self.selected_date.replace(day=b.day)
        self.refresh_calendar()
        self.status_label.set_label(f"Seleccionado {self.selected_date.date()}")

    def shift_month(self, delta):
        y=self.selected_date.year; m=self.selected_date.month+delta
        if m<1: m=12; y-=1
        if m>12: m=1; y+=1
        self.selected_date = self.selected_date.replace(year=y, month=m, day=1)
        self.refresh_calendar()
    def go_today(self): self.selected_date=datetime.now(); self.refresh_calendar()

    def refresh_tag_cloud(self):
        while child := self.tag_flow.get_first_child(): self.tag_flow.remove(child)
        con=db(); cur=con.cursor()
        try: cur.execute("SELECT name FROM tags ORDER BY name LIMIT 12"); tags=[r[0] for r in cur.fetchall()]
        except: tags=[]
        if not tags:
            cur.execute("SELECT title,body FROM notes")
            seen=set()
            for r in cur.fetchall():
                for t in re.findall(r"#(\w+)", r["title"]+" "+r["body"]): seen.add(t)
            tags=list(seen)[:12]
        con.close()
        for t in tags:
            b=Gtk.Button(label=f"#{t}", has_frame=False)
            b.connect("clicked", lambda _, t=t: self.search_entry.set_text(f"#{t}"))
            self.tag_flow.append(b)

    def refresh_notes(self):
        q=self.search_entry.get_text().strip() if hasattr(self,'search_entry') else ""
        tag=None; fecha=None; text_q=q
        m=re.search(r"tag:(\w+)", q)
        if m: tag=m.group(1); text_q=re.sub(r"tag:\w+", "", text_q).strip()
        mf=re.search(r"fecha:(\S+)", q)
        if mf:
            fecha=mf.group(1); text_q=re.sub(r"fecha:\S+", "", text_q).strip()
        con=db(); cur=con.cursor()
        if text_q and "#" in text_q:
            mf2=re.search(r"#(\w+)", text_q)
            if mf2 and not tag: tag=mf2.group(1)
        if q:
            try:
                if text_q:
                    cur.execute("SELECT n.id,n.title,n.body,n.updated_at FROM notes n JOIN notes_fts f ON n.id=f.rowid WHERE notes_fts MATCH ? ORDER BY n.updated_at DESC LIMIT 100", (text_q,))
                    rows=cur.fetchall()
                    if not rows: raise Exception("no fts")
                else: rows=[]
            except:
                like=f"%{text_q}%"
                if text_q: cur.execute("SELECT id,title,body,updated_at FROM notes WHERE title LIKE ? OR body LIKE ? ORDER BY updated_at DESC LIMIT 100", (like,like))
                else: cur.execute("SELECT id,title,body,updated_at FROM notes ORDER BY updated_at DESC LIMIT 100")
                rows=cur.fetchall()
            if tag: rows=[r for r in rows if f"#{tag}" in (r["title"]+" "+r["body"])]
            # fecha filter
            if fecha:
                from datetime import date as _date
                target=None; is_week=False
                if fecha=="hoy": target=_date.today()
                elif fecha=="ayer": target=_date.today()-timedelta(days=1)
                elif fecha=="semana": is_week=True
                else:
                    try: target=datetime.strptime(fecha, "%Y-%m-%d").date()
                    except: target=None
                if is_week:
                    cutoff=_date.today()-timedelta(days=7)
                    rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date() >= cutoff]
                elif target:
                    rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date()==target]
        else:
            cur.execute("SELECT id,title,body,updated_at FROM notes ORDER BY updated_at DESC LIMIT 100"); rows=cur.fetchall()
            if fecha:
                from datetime import date as _date
                if fecha=="hoy": rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date()==_date.today()]
                elif fecha=="semana":
                    cutoff=_date.today()-timedelta(days=7)
                    rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date() >= cutoff]
        con.close()
        while child := self.notes_list.get_first_child(): self.notes_list.remove(child)
        self._note_rows = rows
        for r in rows:
            ts=datetime.fromtimestamp(r["updated_at"]).strftime("%m-%d %H:%M")
            pend=r["body"].count("- [ ]")
            suffix=f"  ☐{pend}" if pend else ""
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=4, margin_bottom=4, margin_start=6, margin_end=6)
            box.append(Gtk.Label(label=str(r["id"]), width_request=30))
            box.append(Gtk.Label(label=r["title"][:44]+suffix, hexpand=True, xalign=0, ellipsize=Pango.EllipsizeMode.END))
            box.append(Gtk.Label(label=ts, css_classes=["dim-label"]))
            row.set_child(box); row.note_id = r["id"]
            self.notes_list.append(row)
        self.status_label.set_label(f"{len(rows)} notas" + (f" • filtro: {q}" if q else ""))

    def on_select_note(self, row):
        if not row: return
        nid=row.note_id
        con=db(); cur=con.cursor(); cur.execute("SELECT * FROM notes WHERE id=?", (nid,)); r=cur.fetchone()
        if not r: con.close(); return
        # backlinks: quién enlaza a esta nota
        cur.execute("SELECT src_id FROM backlinks WHERE dst_title=?", (r["title"],))
        linked=[str(x[0]) for x in cur.fetchall()]
        con.close()
        if not r: return
        self.current_note_id=nid
        self.title_entry.set_text(r["title"])
        buf=self.text_view.get_buffer()
        buf.set_text(r["body"], -1)
        # highlight búsqueda
        self.auto_tag_hint()
        back = f" • enlazada por #{', #'.join(linked)}" if linked else ""
        self.status_label.set_label(f"Nota #{nid} • {len(re.findall(r'#(\\w+)', r['body']+r['title']))} tags{back}")

    def new_note(self):
        tmpl_name=self.template_combo.get_selected()
        tmpl_key=list(TEMPLATES.keys())[tmpl_name] if tmpl_name < len(TEMPLATES) else "Diario"
        tmpl=TEMPLATES.get(tmpl_key, "")
        title_base=self.selected_date.strftime("%Y-%m-%d")
        body=tmpl.format(date=self.selected_date.strftime("%Y-%m-%d"), title=title_base)
        title=title_base
        if tmpl_key!="Diario":
            dlg = Gtk.Dialog(title="Nueva nota", transient_for=self, modal=True)
            dlg.add_button("Cancelar", Gtk.ResponseType.CANCEL); dlg.add_button("Crear", Gtk.ResponseType.OK)
            entry = Gtk.Entry(text=title_base, placeholder_text="Título")
            dlg.get_content_area().append(entry)
            dlg.present()
            # simple sync: usar Adw.MessageDialog con entry no trivial, fallback a title_base
            title = title_base
            dlg.close()
        con=db(); cur=con.cursor(); now=int(time.time())
        cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (title, body, now, now))
        nid=cur.lastrowid
        # Knowledge OS: index backlinks
        try:
            for m in re.findall(r"\[\[([^\]]+)\]\]", body):
                cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (nid, m.strip()))
        except: pass
        con.commit(); con.close()
        self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
        self.status_label.set_label(f"Nota creada #{nid}")

    def save_note(self):
        title=self.title_entry.get_text()
        buf=self.text_view.get_buffer()
        start, end = buf.get_bounds()
        body=buf.get_text(start, end, False).strip()
        if not self.current_note_id:
            if not title.strip() and not body: return
            con=db(); cur=con.cursor(); now=int(time.time())
            cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (title or "Sin título", body, now, now))
            self.current_note_id=cur.lastrowid
            try:
                for m in re.findall(r"\[\[([^\]]+)\]\]", body):
                    cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (self.current_note_id, m.strip()))
            except: pass
            con.commit(); con.close()
            self.refresh_notes(); self.status_label.set_label(f"Nota creada #{self.current_note_id}"); return
        con=db(); cur=con.cursor(); now=int(time.time())
        cur.execute("UPDATE notes SET title=?, body=?, updated_at=? WHERE id=?", (title, body, now, self.current_note_id))
        tags=re.findall(r"#(\w+)", title+" "+body)
        cur.execute("DELETE FROM note_tags WHERE note_id=?", (self.current_note_id,))
        for t in tags:
            cur.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (t,))
            cur.execute("SELECT id FROM tags WHERE name=?", (t,)); tid=cur.fetchone()[0]
            cur.execute("INSERT OR IGNORE INTO note_tags(note_id,tag_id) VALUES(?,?)", (self.current_note_id, tid))
        # Knowledge OS: backlinks reindex
        cur.execute("DELETE FROM backlinks WHERE src_id=?", (self.current_note_id,))
        for m in re.findall(r"\[\[([^\]]+)\]\]", body):
            cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (self.current_note_id, m.strip()))
        con.commit(); con.close()
        self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
        self.status_label.set_label(f"Guardado #{self.current_note_id} ✓")

    def insert_task(self):
        buf=self.text_view.get_buffer()
        buf.insert_at_cursor("- [ ] ", -1)
        self.text_view.grab_focus()
    def insert_link(self):
        # simple
        buf=self.text_view.get_buffer()
        buf.insert_at_cursor("[[enlace]]", -1)
    def insert_tag(self):
        buf=self.text_view.get_buffer()
        buf.insert_at_cursor("#tag ", -1)
    def toggle_task_in_editor(self):
        buf=self.text_view.get_buffer()
        cursor=buf.get_iter_at_mark(buf.get_insert())
        line=cursor.get_line()
        start=buf.get_iter_at_line(line); end=buf.get_iter_at_line(line); end.forward_to_line_end()
        text=buf.get_text(start,end,False)
        if re.match(r"^- \[[ xX]\]", text):
            new=toggle_task_line(text)
            buf.delete(start,end); buf.insert(start,new,-1)

    def auto_tag_hint(self):
        # highlight búsqueda en editor si hay filtro
        q=self.search_entry.get_text().strip()
        buf=self.text_view.get_buffer()
        # limpiar tag previo
        start,end=buf.get_bounds()
        buf.remove_tag_by_name("search_match", start, end) if buf.get_tag_table().lookup("search_match") else None
        if not q: return
        # crear tag si no existe
        if not buf.get_tag_table().lookup("search_match"):
            tag=buf.create_tag("search_match", background="#fff176")
        else: tag=buf.get_tag_table().lookup("search_match")
        # quitar tag: y # para highlight
        qs=re.sub(r"tag:\w+|#\w+", "", q).strip()
        if not qs: return
        # buscar todas ocurrencias case-insensitive
        text=buf.get_text(start,end,False)
        for m in re.finditer(re.escape(qs), text, re.IGNORECASE):
            s=buf.get_iter_at_offset(m.start()); e=buf.get_iter_at_offset(m.end())
            buf.apply_tag(tag, s, e)

    def highlight_current_search(self): self.auto_tag_hint()

    def refresh_tasks(self):
        while child := self.task_list.get_first_child(): self.task_list.remove(child)
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body FROM notes"); rows=cur.fetchall(); con.close()
        self._task_map=[]
        pend=0
        for r in rows:
            for i,line in enumerate(r["body"].splitlines()):
                m=re.match(r"^- \[([ xX])\] (.+)", line)
                if m:
                    done=m.group(1).lower()=="x"
                    if not done: pend+=1
                    row=Gtk.ListBoxRow()
                    lbl=Gtk.Label(label=f"{'☑' if done else '☐'} {m.group(2)[:48]}  — {r['title'][:18]} #{r['id']}", xalign=0)
                    if done: lbl.add_css_class("dim-label")
                    row.set_child(lbl); self.task_list.append(row)
                    self._task_map.append((r["id"], i, line))
        # update notebook tab label - skip for now

    def on_toggle_task_global(self, row):
        idx=row.get_index()
        nid, line_idx, _ = self._task_map[idx]
        con=db(); cur=con.cursor(); cur.execute("SELECT body FROM notes WHERE id=?", (nid,)); body=cur.fetchone()["body"]
        lines=body.splitlines(); lines[line_idx]=toggle_task_line(lines[line_idx])
        new_body="\n".join(lines)
        cur.execute("UPDATE notes SET body=?, updated_at=? WHERE id=?", (new_body, int(time.time()), nid)); con.commit(); con.close()
        self.refresh_tasks()

    def refresh_events(self):
        while child := self.event_list.get_first_child(): self.event_list.remove(child)
        con=db(); cur=con.cursor()
        dt=self.selected_date
        start=int(datetime(dt.year, dt.month, 1).timestamp())
        end=int(datetime(dt.year+1,1,1).timestamp()) if dt.month==12 else int(datetime(dt.year, dt.month+1,1).timestamp())
        cur.execute("SELECT id,title,start_ts,end_ts,note_id FROM events WHERE start_ts>=? AND start_ts<? ORDER BY start_ts", (start,end))
        self._event_ids=[]
        for r in cur.fetchall():
            d=datetime.fromtimestamp(r["start_ts"]).strftime("%d %H:%M")
            suffix=f" → nota #{r['note_id']}" if r["note_id"] else ""
            row=Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=f"{d}  {r['title']}{suffix}", xalign=0, margin_top=4, margin_bottom=4, margin_start=6))
            self.event_list.append(row); self._event_ids.append(r["id"])
        con.close()

    def new_event(self):
        # simple dialog
        dlg = Adw.MessageDialog(transient_for=self, heading="Nuevo evento", body="Se crea a las 10:00 del día seleccionado. Edita luego.")
        dlg.add_response("cancel","Cancelar", appearance=Adw.ResponseAppearance.DEFAULT)
        dlg.add_response("ok","Crear", appearance=Adw.ResponseAppearance.SUGGESTED)
        dlg.choose(None, lambda *_: None)
        # for now auto create
        title="Nuevo evento"
        dt=self.selected_date.replace(hour=10, minute=0, second=0)
        start=int(dt.timestamp()); end=start+3600
        con=db(); cur=con.cursor(); uid=f"{int(time.time())}-{start}@gnote.local"
        cur.execute("INSERT INTO events(title,description,location,start_ts,end_ts,uid,source,created_at,note_id) VALUES(?,?,?,?,?,?,?,?,?)",
                    (title, "", "", start, end, uid, "local", int(time.time()), self.current_note_id or None))
        con.commit(); con.close(); self.refresh_calendar()

    def delete_event(self):
        row=self.event_list.get_selected_row()
        if not row: return
        idx=row.get_index(); eid=self._event_ids[idx]
        con=db(); con.execute("DELETE FROM events WHERE id=?", (eid,)); con.commit(); con.close(); self.refresh_calendar()

    def link_event_note(self):
        row=self.event_list.get_selected_row()
        if not row or not self.current_note_id: return
        eid=self._event_ids[row.get_index()]
        con=db(); con.execute("UPDATE events SET note_id=? WHERE id=?", (self.current_note_id, eid)); con.commit(); con.close()
        self.refresh_events()

    def on_edit_event(self, row):
        idx=row.get_index(); eid=self._event_ids[idx]
        con=db(); cur=con.cursor(); cur.execute("SELECT * FROM events WHERE id=?", (eid,)); r=cur.fetchone(); con.close()
        if r:
            dlg=Adw.MessageDialog(transient_for=self, heading=r["title"], body=f"{datetime.fromtimestamp(r['start_ts'])}\n→ {datetime.fromtimestamp(r['end_ts'])}\n{r['description']}")
            dlg.add_response("ok","OK", appearance=Adw.ResponseAppearance.SUGGESTED); dlg.present()

    def export_ics(self):
        # use FileDialog (GTK4)
        dialog = Gtk.FileDialog(title="Exportar .ics", initial_name="calendario.ics")
        dialog.save(self, None, self._export_ics_cb)
    def _export_ics_cb(self, dlg, res):
        try: f=dlg.save_finish(res)
        except: return
        path=f.get_path()
        if os.path.exists(BIN_PATH):
            r=subprocess.run([BIN_PATH, "ics", "export", "--output", path], capture_output=True, text=True)
            dlg2=Adw.MessageDialog(transient_for=self, heading="Exportar", body=r.stdout.strip() if r.returncode==0 else r.stderr)
            dlg2.add_response("ok","OK", appearance=Adw.ResponseAppearance.SUGGESTED); dlg2.present()

    def import_ics(self):
        dialog = Gtk.FileDialog(title="Importar .ics")
        f = Gtk.FileFilter(); f.set_name("ICS"); f.add_pattern("*.ics"); dialog.set_filters(Gio.ListStore.new(Gtk.FileFilter)); dialog.get_filters().append(f)
        dialog.open(self, None, self._import_ics_cb)
    def _import_ics_cb(self, dlg, res):
        try: f=dlg.open_finish(res)
        except: return
        path=f.get_path()
        r=subprocess.run([BIN_PATH, "ics", "import", path], capture_output=True, text=True)
        dlg2=Adw.MessageDialog(transient_for=self, heading="Importar", body=(r.stdout+r.stderr).strip())
        dlg2.add_response("ok","OK", appearance=Adw.ResponseAppearance.SUGGESTED); dlg2.present()
        self.refresh_calendar()

    def export_markdown(self):
        if not self.current_note_id: return
        dialog = Gtk.FileDialog(title="Exportar .md", initial_name=f"nota-{self.current_note_id}.md")
        dialog.save(self, None, self._export_md_cb)
    def _export_md_cb(self, dlg, res):
        try: f=dlg.save_finish(res)
        except: return
        path=f.get_path()
        title=self.title_entry.get_text()
        buf=self.text_view.get_buffer(); s,e=buf.get_bounds(); body=buf.get_text(s,e,False)
        open(path,"w",encoding="utf-8").write(f"# {title}\n\n{body}\n")

    def get_sync_folder(self):
        # lee config.ini
        for p in [os.path.expanduser("~/.config/gnote-calendar/config.ini"), os.path.join(os.path.dirname(__file__), "config.ini")]:
            if os.path.exists(p):
                try:
                    with open(p) as f:
                        for line in f:
                            if line.strip().startswith("sync_folder"):
                                return line.split("=",1)[1].strip()
                except: pass
        return os.path.expanduser("~/Notas")

    def set_sync_folder(self, folder):
        p=os.path.expanduser("~/.config/gnote-calendar/config.ini")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        cfg={}
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k,v=line.split("=",1); cfg[k.strip()]=v.strip()
        cfg["sync_folder"]=folder
        with open(p,"w") as f:
            for k,v in cfg.items(): f.write(f"{k}={v}\n")

    def show_folder_sync(self):
        cur_folder=self.get_sync_folder()
        dlg=Adw.MessageDialog(transient_for=self, heading="Folder Sync — Knowledge OS", body=f"Carpeta actual:\n{cur_folder}\n\n1 .md por nota con frontmatter id/title.\nSync bidireccional: exporta notas → .md e importa .md → notas.\nCompatible con Syncthing/Nextcloud/Git.")
        dlg.add_response("cancel","Cerrar", appearance=Adw.ResponseAppearance.DEFAULT)
        dlg.add_response("choose","Elegir carpeta", appearance=Adw.ResponseAppearance.DEFAULT)
        dlg.add_response("sync","Sincronizar ahora", appearance=Adw.ResponseAppearance.SUGGESTED)
        dlg.connect("response", lambda d,r: self._folder_sync_response(d,r, cur_folder))
        dlg.present()

    def _folder_sync_response(self, dlg, resp, cur_folder):
        if resp=="choose":
            fd=Gtk.FileDialog(title="Elegir carpeta sync")
            fd.select_folder(self, None, lambda d,res: self._folder_choose_cb(d,res))
        elif resp=="sync":
            folder=self.get_sync_folder()
            if os.path.exists(BIN_PATH):
                r=subprocess.run([BIN_PATH, "sync", "--folder", folder], capture_output=True, text=True)
                body=(r.stdout+r.stderr).strip() or "Sincronizado"
            else:
                # fallback python sync
                body=self._python_sync(folder)
            msg=Adw.MessageDialog(transient_for=self, heading="Sync", body=body)
            msg.add_response("ok","OK", appearance=Adw.ResponseAppearance.SUGGESTED)
            msg.connect("response", lambda *_: (self.refresh_notes(), self.refresh_tag_cloud(), self.refresh_tasks()))
            msg.present()

    def _folder_choose_cb(self, dlg, res):
        try: f=dlg.select_folder_finish(res)
        except: return
        path=f.get_path()
        self.set_sync_folder(path)
        self.status_label.set_label(f"Folder sync → {path}")
        dlg2=Adw.MessageDialog(transient_for=self, heading="Carpeta actualizada", body=f"Nueva carpeta:\n{path}\nUsa 'Sincronizar ahora' para exportar.")
        dlg2.add_response("ok","OK", appearance=Adw.ResponseAppearance.SUGGESTED); dlg2.present()

    def _python_sync(self, folder):
        # fallback sin binario: export/import simple
        import pathlib
        os.makedirs(folder, exist_ok=True)
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body,created_at,updated_at FROM notes")
        exp=0
        for r in cur.fetchall():
            nid=r["id"]; title=r["title"]
            # sanitize
            safe="".join(c if c.isalnum() or c in "-_" else "-" if c==" " else "" for c in title)[:40] or "nota"
            path=os.path.join(folder, f"{nid:04d}-{safe}.md")
            front=f"---\nid: {nid}\ntitle: \"{title}\"\n---\n\n{r['body']}\n"
            # escribir solo si distinto
            if not os.path.exists(path) or open(path).read()!=front:
                open(path,"w",encoding="utf-8").write(front); exp+=1
        con.close()
        return f"Exportados {exp} (fallback python). Usa el binario para import."

    def auto_folder_sync(self):
        # poll cada 5s, solo si carpeta existe y hay binario
        folder=self.get_sync_folder()
        if os.path.isdir(folder) and os.path.exists(BIN_PATH):
            # solo si han pasado 5s desde último sync y hay cambios: simplificado siempre sync silencioso
            try:
                r=subprocess.run([BIN_PATH, "sync", "--folder", folder], capture_output=True, text=True, timeout=3)
                if "Importados" in r.stdout or "Exportados" in r.stdout:
                    # refrescar si hubo cambios (heurística: stdout contiene números >0)
                    if any(c.isdigit() and int(c)>0 for c in r.stdout if c.isdigit()):
                        self.refresh_notes(); self.refresh_tasks()
            except: pass
        return True

    def open_pomodoro(self):
        if self.pomodoro_win and self.pomodoro_win.is_visible(): self.pomodoro_win.present(); return
        self.pomodoro_win=PomodoroWindow(self)
        self.pomodoro_win.present()

    def show_stats(self):
        con=db(); cur=con.cursor()
        cur.execute("SELECT COUNT(*) FROM notes"); n_notes=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM events"); n_ev=cur.fetchone()[0]
        cur.execute("SELECT body FROM notes"); bodies=[r[0] for r in cur.fetchall()]
        tasks=sum(b.count("- [ ]")+b.count("- [x]") for b in bodies)
        pend=sum(b.count("- [ ]") for b in bodies)
        tags=set(re.findall(r"#(\w+)", "".join(bodies)))
        con.close()
        dlg=Adw.MessageDialog(transient_for=self, heading="Estadísticas", body=f"📝 Notas: {n_notes}\n📅 Eventos: {n_ev}\n✅ Tareas: {pend}/{tasks}\n🏷️ Tags: {len(tags)}")
        dlg.add_response("ok","OK", appearance=Adw.ResponseAppearance.SUGGESTED); dlg.present()

    def show_graph(self):
        win=Adw.Window(transient_for=self, title="Grafo Knowledge OS — fuerza dirigida", default_width=720, default_height=520)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header=Gtk.Label(label="Grafo de [[enlaces]] — arrastra nodos • click navega a nota", css_classes=["dim-label"])
        box.append(header)
        area=Gtk.DrawingArea(vexpand=True, hexpand=True)
        area.set_content_width(720); area.set_content_height(460)
        box.append(area)
        win.set_content(box)

        # Cargar datos
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title FROM notes"); nodes_data=cur.fetchall()
        cur.execute("SELECT src_id, dst_title FROM backlinks"); links_raw=cur.fetchall()
        con.close()
        if not nodes_data:
            area.set_draw_func(lambda a,cr,w,h: (cr.set_source_rgb(0.5,0.5,0.5), cr.move_to(w/2-80,h/2), cr.show_text("Sin notas. Usa [[enlace]]")))
            win.present(); return

        # Mapear títulos -> id
        title_to_id={r["title"].strip().lower(): r["id"] for r in nodes_data}
        id_to_title={r["id"]: r["title"][:18] for r in nodes_data}
        # Nodos con posiciones circulares + velocidad
        import math, random
        N=len(nodes_data)
        nodes=[]
        for i,r in enumerate(nodes_data):
            ang=2*math.pi*i/max(1,N)
            nodes.append({"id":r["id"], "title":id_to_title[r["id"]], "x":360+150*math.cos(ang)+random.uniform(-10,10), "y":240+150*math.sin(ang)+random.uniform(-10,10), "vx":0, "vy":0})
        id_to_idx={n["id"]:i for i,n in enumerate(nodes)}
        edges=[]
        for src,dst_title in links_raw:
            did=title_to_id.get(dst_title.strip().lower())
            if did and src in id_to_idx and did in id_to_idx:
                edges.append((id_to_idx[src], id_to_idx[did]))

        # Estado drag
        state={"drag":-1, "offset":(0,0)}
        def on_press(ctrl, n_press, x, y):
            for i,n in enumerate(nodes):
                if (n["x"]-x)**2 + (n["y"]-y)**2 < 1600:
                    state["drag"]=i; state["offset"]=(n["x"]-x, n["y"]-y); break
        def on_drag(ctrl, x, y):
            if state["drag"]>=0:
                n=nodes[state["drag"]]; n["x"]=x+state["offset"][0]; n["y"]=y+state["offset"][1]; n["vx"]=n["vy"]=0; area.queue_draw()
        def on_release(ctrl, n_press, x, y):
            if state["drag"]>=0:
                # click navega
                nid=nodes[state["drag"]]["id"]
                # seleccionar nota en main window
                for row in self.notes_list:
                    if hasattr(row, 'note_id') and row.note_id==nid:
                        self.notes_list.select_row(row); break
                state["drag"]=-1

        drag=Gtk.GestureDrag(); drag.connect("drag-begin", on_press); drag.connect("drag-update", on_drag); drag.connect("drag-end", on_release)
        area.add_controller(drag)
        click=Gtk.GestureClick(); click.connect("pressed", lambda c,n,x,y: (setattr(c, 'x', x), setattr(c, 'y', y)))
        area.add_controller(click)

        def draw(area, cr, w, h):
            # física simple: repulsión + atracción edges + centro
            for _ in range(5): # iteraciones por frame para estabilidad
                for i,a in enumerate(nodes):
                    if i==state["drag"]: continue
                    # centro gravitatorio
                    a["vx"] += (360 - a["x"])*0.005
                    a["vy"] += (240 - a["y"])*0.005
                    for j,b in enumerate(nodes):
                        if i==j: continue
                        dx=a["x"]-b["x"]; dy=a["y"]-b["y"]; d2=dx*dx+dy*dy
                        if d2<1: d2=1
                        if d2<90000:
                            f=1200/(d2)
                            d=math.sqrt(d2)
                            a["vx"] += dx/d*f*0.08; a["vy"] += dy/d*f*0.08
                    # fricción
                    a["vx"]*=0.85; a["vy"]*=0.85
                for (i,j) in edges:
                    a=nodes[i]; b=nodes[j]
                    dx=b["x"]-a["x"]; dy=b["y"]-a["y"]; d=math.sqrt(dx*dx+dy*dy)
                    if d>1:
                        f=(d-90)*0.02
                        a["vx"] += dx/d*f; a["vy"] += dy/d*f
                        b["vx"] -= dx/d*f; b["vy"] -= dy/d*f
                for n in nodes:
                    if nodes.index(n)==state["drag"]: continue
                    n["x"]+=n["vx"]; n["y"]+=n["vy"]
                    n["x"]=max(50,min(w-50,n["x"])); n["y"]=max(30,min(h-30,n["y"]))

            # dibujar aristas
            cr.set_source_rgb(0.6,0.6,0.6); cr.set_line_width(1)
            for (i,j) in edges:
                a=nodes[i]; b=nodes[j]
                cr.move_to(a["x"], a["y"]); cr.line_to(b["x"], b["y"]); cr.stroke()
                # flecha simple
                ang=math.atan2(b["y"]-a["y"], b["x"]-a["x"])
                cr.move_to(b["x"]-12*math.cos(ang), b["y"]-12*math.sin(ang))
                cr.line_to(b["x"]-8*math.cos(ang+0.3), b["y"]-8*math.sin(ang+0.3)); cr.line_to(b["x"]-8*math.cos(ang-0.3), b["y"]-8*math.sin(ang-0.3)); cr.close_path(); cr.fill()
            # nodos
            for n in nodes:
                # sombra
                cr.set_source_rgba(0,0,0,0.15); cr.arc(n["x"]+2, n["y"]+2, 32, 0, 2*math.pi); cr.fill()
                # nodo
                is_current = (self.current_note_id==n["id"])
                if is_current: cr.set_source_rgb(0.29,0.56,0.88)
                else: cr.set_source_rgb(0.89,0.94,0.98)
                cr.arc(n["x"], n["y"], 30, 0, 2*math.pi); cr.fill_preserve()
                cr.set_source_rgb(0.29,0.56,0.88); cr.set_line_width(1.5); cr.stroke()
                cr.set_source_rgb(0.2,0.2,0.2); cr.select_font_face("Sans", 0, 0); cr.set_font_size(7)
                # texto centrado simple
                te=cr.text_extents(n["title"]); cr.move_to(n["x"]-te.width/2, n["y"]+3); cr.show_text(n["title"])
                # id badge
                cr.set_source_rgb(0.5,0.5,0.5); cr.set_font_size(6); cr.move_to(n["x"]-8, n["y"]+18); cr.show_text(f"#{n['id']}")

        area.set_draw_func(draw)
        # animar 30fps
        GLib.timeout_add(33, lambda: (area.queue_draw(), True)[1])
        win.present()
        # auto-refresh stats en status
        self.status_label.set_label(f"Grafo: {len(nodes)} nodos, {len(edges)} enlaces — arrastra para organizar")

    def check_upcoming(self):
        try:
            con=db(); cur=con.cursor(); now=int(time.time())
            cur.execute("SELECT title,start_ts FROM events WHERE start_ts>=? AND start_ts<=? LIMIT 3", (now, now+900))
            for r in cur.fetchall():
                try: subprocess.run(["notify-send", f"⏰ {r['title']}", f"{datetime.fromtimestamp(r['start_ts']).strftime('%H:%M')}"], timeout=1)
                except: pass
            con.close()
        except: pass
        return True

class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.gerardoarias.gnote-calendar", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)
    def on_activate(self, app):
        win = MainWindow(app)
        win.present()

if __name__=="__main__":
    ensure_db()
    app = App()
    app.run(sys.argv)
