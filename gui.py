#!/usr/bin/env python3
# gnote-calendar GUI ligera v2 - Tkinter, sin dependencias extra
# Frontend para core C++ SQLite (~/.local/share/gnote-calendar/notes.db)
# Doble-click compatible, <25MB RAM, 2015+  •  Features: checklist, plantillas, pomodoro, tags, export md, grafo, stats

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3, os, re, subprocess, time, calendar, json
from datetime import datetime, timedelta

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
            CREATE TABLE IF NOT EXISTS tags(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
            CREATE TABLE IF NOT EXISTS note_tags(note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE, tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE, PRIMARY KEY(note_id, tag_id));
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
        for m in re.findall(r"\[\[([^\]]+)\]\]", body or ""):
            cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (note_id, m.strip()))
        con.commit(); con.close()
    except: pass

def ensure_daily_note():
    today = datetime.now().strftime("%Y-%m-%d")
    con = db(); cur = con.cursor()
    cur.execute("SELECT id FROM notes WHERE title=?", (today,))
    row = cur.fetchone()
    if row: con.close(); return row[0]
    body = TEMPLATES["Diario"].format(date=today, title=today)
    start = int(datetime.now().replace(hour=0, minute=0, second=0).timestamp())
    end = int(datetime.now().replace(hour=23, minute=59, second=59).timestamp())
    cur.execute("SELECT title, start_ts FROM events WHERE start_ts>=? AND start_ts<=? ORDER BY start_ts LIMIT 5", (start, end))
    evs = cur.fetchall()
    if evs:
        body += "\n## 📅 Hoy\n"
        for e in evs:
            body += f"- {datetime.fromtimestamp(e['start_ts']).strftime('%H:%M')} {e['title']}\n"
    now = int(time.time())
    cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (today, body, now, now))
    nid = cur.lastrowid
    update_backlinks(nid, body)
    con.commit(); con.close()
    return nid

def get_sync_folder():
    for p in [os.path.expanduser("~/.config/gnote-calendar/config.ini")]:
        if os.path.exists(p):
            try:
                with open(p) as f:
                    for line in f:
                        if line.strip().startswith("sync_folder"):
                            return line.split("=",1)[1].strip()
            except: pass
    return os.path.expanduser("~/Notas")

def set_sync_folder(folder):
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

def extract_tasks(text):
    return re.findall(r"^- \[[ xX]\] (.+)$", text, flags=re.MULTILINE)

def toggle_task_line(line):
    if re.match(r"^- \[ \]", line): return re.sub(r"^- \[ \]", "- [x]", line, count=1)
    if re.match(r"^- \[[xX]\]", line): return re.sub(r"^- \[[xX]\]", "- [ ]", line, count=1)
    return line

class Pomodoro(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Pomodoro — 25:00")
        self.geometry("260x160")
        self.resizable(False, False)
        self.remaining = 25*60
        self.running = False
        self.mode = "work" # work / break
        self.label = tk.Label(self, text="25:00", font=("TkDefaultFont", 36, "bold"))
        self.label.pack(pady=10)
        self.mode_label = ttk.Label(self, text="🍅 Trabajo — enfócate en la nota actual")
        self.mode_label.pack()
        btns = ttk.Frame(self); btns.pack(pady=8)
        ttk.Button(btns, text="Iniciar", command=self.start).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Pausa", command=self.pause).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Reset", command=self.reset).pack(side=tk.LEFT, padx=4)
        self.after(1000, self.tick)
    def start(self): self.running=True
    def pause(self): self.running=False
    def reset(self):
        self.running=False
        self.mode="work"; self.remaining=25*60
        self.label.config(text="25:00"); self.mode_label.config(text="🍅 Trabajo")
        self.title("Pomodoro — 25:00")
    def tick(self):
        if self.running and self.remaining>0:
            self.remaining-=1
            m,s = divmod(self.remaining,60)
            self.label.config(text=f"{m:02d}:{s:02d}")
            self.title(f"Pomodoro — {m:02d}:{s:02d} {'🍅' if self.mode=='work' else '☕'}")
            if self.remaining==0:
                self.running=False
                # notify
                try: subprocess.run(["notify-send","Pomodoro", "¡Tiempo terminado!" if self.mode=="work" else "Descanso terminado"], timeout=2)
                except: pass
                messagebox.showinfo("Pomodoro", "¡Tiempo terminado! " + ("Toca descanso 5 min" if self.mode=="work" else "Vuelve al trabajo"), parent=self)
                if self.mode=="work":
                    self.mode="break"; self.remaining=5*60; self.mode_label.config(text="☕ Descanso 5 min")
                else:
                    self.mode="work"; self.remaining=25*60; self.mode_label.config(text="🍅 Trabajo")
        self.after(1000, self.tick)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("gnote-calendar — Notas y Calendario")
        self.geometry("1180x680")
        try: self.iconname("gnote-calendar")
        except: pass
        self.current_note_id = None
        self.selected_date = datetime.now()
        self.pomodoro_win = None
        self.build_ui()
        try: ensure_daily_note()
        except: pass
        self.refresh_notes()
        self.refresh_calendar()
        self.refresh_events()
        self.refresh_tasks()
        self.refresh_tag_cloud()
        self.check_upcoming() # notificaciones
        self.after(5000, self.auto_folder_sync)

    def build_ui(self):
        # Top bar
        top = ttk.Frame(self); top.pack(fill=tk.X, padx=6, pady=4)
        ttk.Label(top, text="Buscar:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_notes())
        self.search_entry = ttk.Entry(top, textvariable=self.search_var, width=28)
        self.search_entry.pack(side=tk.LEFT, padx=6)
        self.search_entry.bind("<Escape>", lambda e: self.search_var.set(""))
        # Plantillas dropdown
        ttk.Label(top, text="Plantilla:").pack(side=tk.LEFT, padx=(8,2))
        self.template_var = tk.StringVar(value="Diario")
        tmpl = ttk.Combobox(top, textvariable=self.template_var, values=list(TEMPLATES.keys()), width=10, state="readonly")
        tmpl.pack(side=tk.LEFT)
        ttk.Button(top, text="Nueva nota", command=self.new_note).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Guardar", command=self.save_note).pack(side=tk.LEFT, padx=1)
        ttk.Button(top, text="Borrar", command=self.delete_note).pack(side=tk.LEFT, padx=1)
        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Button(top, text="🍅 Pomodoro", command=self.open_pomodoro).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="📊 Stats", command=self.show_stats).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="🕸️ Grafo", command=self.show_graph).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="📁 Sync", command=self.show_folder_sync).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Export .ics", command=self.export_ics).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top, text="Import .ics", command=self.import_ics).pack(side=tk.RIGHT, padx=2)

        # Paned main
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL); paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        left = ttk.Frame(paned); paned.add(left, weight=1)

        # Calendar
        cal_head = ttk.Frame(left); cal_head.pack(fill=tk.X, pady=2)
        self.cal_label = ttk.Label(cal_head, text="", font=("TkDefaultFont", 10, "bold")); self.cal_label.pack(side=tk.LEFT)
        ttk.Button(cal_head, text="◀", width=2, command=lambda: self.shift_month(-1)).pack(side=tk.RIGHT)
        ttk.Button(cal_head, text="▶", width=2, command=lambda: self.shift_month(1)).pack(side=tk.RIGHT)
        ttk.Button(cal_head, text="Hoy", width=4, command=self.go_today).pack(side=tk.RIGHT, padx=2)
        self.cal_frame = ttk.Frame(left); self.cal_frame.pack(fill=tk.X)
        for i, d in enumerate(["Lu","Ma","Mi","Ju","Vi","Sá","Do"]):
            ttk.Label(self.cal_frame, text=d, width=4, anchor="center", foreground="#666").grid(row=0, column=i, padx=1)
        self.cal_buttons = []
        for r in range(6):
            row=[]
            for c in range(7):
                b = tk.Button(self.cal_frame, text="", width=4, relief=tk.FLAT, bg="#f0f0f0", command=lambda r=r,c=c: self.on_cal_click(r,c))
                b.grid(row=r+1, column=c, padx=1, pady=1)
                row.append(b)
            self.cal_buttons.append(row)

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        # Tag cloud
        tag_frame = ttk.Frame(left); tag_frame.pack(fill=tk.X)
        ttk.Label(tag_frame, text="Tags:", font=("TkDefaultFont", 8)).pack(side=tk.LEFT)
        self.tag_cloud = ttk.Frame(tag_frame); self.tag_cloud.pack(side=tk.LEFT, padx=4)
        ttk.Button(tag_frame, text="✕ filtro", width=6, command=lambda: self.search_var.set("")).pack(side=tk.RIGHT)

        # Notebook left tabs: Notas / Tareas
        self.left_nb = ttk.Notebook(left); self.left_nb.pack(fill=tk.BOTH, expand=True, pady=4)
        tab_notes = ttk.Frame(self.left_nb); tab_tasks = ttk.Frame(self.left_nb)
        self.left_nb.add(tab_notes, text="📝 Notas")
        self.left_nb.add(tab_tasks, text="✅ Tareas")

        # Notas list
        cols = ("id","title","updated")
        self.tree = ttk.Treeview(tab_notes, columns=cols, show="headings", height=10)
        self.tree.heading("id", text="#"); self.tree.heading("title", text="Título"); self.tree.heading("updated", text="Actualizado")
        self.tree.column("id", width=40, anchor="center"); self.tree.column("title", width=200); self.tree.column("updated", width=85)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_note)
        sb = ttk.Scrollbar(tab_notes, orient=tk.VERTICAL, command=self.tree.yview); sb.pack(side=tk.RIGHT, fill=tk.Y); self.tree.configure(yscrollcommand=sb.set)

        # Tareas panel
        self.task_list = tk.Listbox(tab_tasks, height=12, font=("TkDefaultFont", 9))
        self.task_list.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.task_list.bind("<Double-Button-1>", self.on_toggle_task_global)
        tsb = ttk.Scrollbar(tab_tasks, orient=tk.VERTICAL, command=self.task_list.yview); tsb.pack(side=tk.RIGHT, fill=tk.Y); self.task_list.configure(yscrollcommand=tsb.set)
        ttk.Button(tab_tasks, text="Actualizar tareas", command=self.refresh_tasks).pack(fill=tk.X)
        ttk.Label(tab_tasks, text="Doble click = completar  •  Sintaxis: - [ ] tarea", font=("TkDefaultFont", 7), foreground="#666").pack()

        ttk.Label(left, text="Eventos del mes", font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(6,0))
        self.event_list = tk.Listbox(left, height=5); self.event_list.pack(fill=tk.X, pady=2)
        self.event_list.bind("<Double-Button-1>", self.on_edit_event)
        ef = ttk.Frame(left); ef.pack(fill=tk.X)
        ttk.Button(ef, text="Nuevo evento", command=self.new_event).pack(side=tk.LEFT, padx=2)
        ttk.Button(ef, text="Borrar evento", command=self.delete_event).pack(side=tk.LEFT, padx=2)
        ttk.Button(ef, text="Vincular nota", command=self.link_event_note).pack(side=tk.LEFT, padx=2)

        # Right editor
        right = ttk.Frame(paned); paned.add(right, weight=2)
        hdr = ttk.Frame(right); hdr.pack(fill=tk.X)
        ttk.Label(hdr, text="Título:").pack(side=tk.LEFT)
        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(hdr, textvariable=self.title_var, font=("TkDefaultFont", 11, "bold"))
        self.title_entry.pack(fill=tk.X, padx=6, side=tk.LEFT, expand=True)
        self.title_entry.bind("<KeyRelease>", lambda e: self.auto_tag_hint())
        # toolbar editor
        tb = ttk.Frame(right); tb.pack(fill=tk.X, pady=2)
        ttk.Button(tb, text="☐ Tarea", width=7, command=self.insert_task).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="✓ Toggle", width=7, command=self.toggle_task_in_editor).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="🔗 [[link]]", width=8, command=self.insert_link).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="#tag", width=5, command=self.insert_tag).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Export .md", width=9, command=self.export_markdown).pack(side=tk.RIGHT, padx=2)

        self.text = tk.Text(right, wrap=tk.WORD, undo=True, font=("TkDefaultFont", 10), bg="#fffef8", padx=8, pady=8)
        self.text.pack(fill=tk.BOTH, expand=True, pady=4)
        self.text.bind("<Control-s>", lambda e: self.save_note())
        self.text.bind("<Control-S>", lambda e: self.save_note())
        self.text.bind("<Control-Return>", lambda e: self.toggle_task_in_editor())
        self.text.bind("<KeyRelease>", lambda e: self.auto_tag_hint())

        self.status = tk.StringVar(value="Listo. Usa #tag y [[enlace]]  •  Ctrl+S guardar  •  Ctrl+Enter toggle tarea  •  Plantilla arriba")
        ttk.Label(right, textvariable=self.status, foreground="#555", font=("TkDefaultFont", 8)).pack(fill=tk.X)
        self.bind("<Control-s>", lambda e: self.save_note())
        self.bind("<Control-n>", lambda e: self.new_note())
        self.bind("<Control-p>", lambda e: self.open_pomodoro())

    # Calendar
    def refresh_calendar(self):
        dt = self.selected_date
        self.cal_label.config(text=f"{calendar.month_name[dt.month]} {dt.year}")
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
                if idx < first_wd or day>days: b.config(text="", state=tk.DISABLED, bg="#f0f0f0")
                else:
                    b.config(state=tk.NORMAL, text=str(day))
                    is_today = (day==today.day and dt.month==today.month and dt.year==today.year)
                    has_evt = day in counts
                    if is_today: b.config(bg="#4a90e2", fg="white", relief=tk.RAISED)
                    elif has_evt: b.config(bg="#d4edda", fg="#155724", relief=tk.RAISED)
                    elif self.selected_date.day==day: b.config(bg="#fff3cd", fg="black")
                    else: b.config(bg="white", fg="black", relief=tk.FLAT)
                    b.day = day; day+=1
        self.refresh_events()

    def on_cal_click(self, r,c):
        b=self.cal_buttons[r][c]
        if b["state"]==tk.DISABLED: return
        self.selected_date = self.selected_date.replace(day=b.day)
        self.refresh_calendar()
        self.status.set(f"Seleccionado {self.selected_date.date()} — crea nota con plantilla o evento")

    def shift_month(self, delta):
        y=self.selected_date.year; m=self.selected_date.month+delta
        if m<1: m=12; y-=1
        if m>12: m=1; y+=1
        self.selected_date = self.selected_date.replace(year=y, month=m, day=1)
        self.refresh_calendar()
    def go_today(self): self.selected_date=datetime.now(); self.refresh_calendar()

    # Tag cloud
    def refresh_tag_cloud(self):
        for w in self.tag_cloud.winfo_children(): w.destroy()
        con=db(); cur=con.cursor()
        try: cur.execute("SELECT name FROM tags ORDER BY name LIMIT 12")
        except: cur.execute("SELECT DISTINCT substr(title,0,0) FROM notes LIMIT 0")
        tags=[r[0] for r in cur.fetchall()]
        # fallback: extraer de notas si tabla vacía
        if not tags:
            cur.execute("SELECT title,body FROM notes")
            seen=set()
            for r in cur.fetchall():
                for t in re.findall(r"#(\w+)", r["title"]+" "+r["body"]): seen.add(t)
            tags=list(seen)[:12]
        con.close()
        for t in tags:
            b=tk.Button(self.tag_cloud, text=f"#{t}", font=("TkDefaultFont",7), bg="#eef", relief=tk.FLAT, command=lambda t=t: self.search_var.set(f"#{t}"))
            b.pack(side=tk.LEFT, padx=1)

    # Notes
    def refresh_notes(self):
        q=self.search_var.get().strip()
        # soporte tag: y texto
        tag=None; text_q=q
        m=re.search(r"tag:(\w+)", q)
        if m: tag=m.group(1); text_q=re.sub(r"tag:\w+", "", q).strip()
        con=db(); cur=con.cursor()
        if text_q and "#" in text_q: # buscar tag con #
            tag_from_hash=re.search(r"#(\w+)", text_q)
            if tag_from_hash and not tag: tag=tag_from_hash.group(1)
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
            if tag:
                rows=[r for r in rows if f"#{tag}" in (r["title"]+" "+r["body"]) or tag in re.findall(r"#(\w+)", r["title"]+" "+r["body"])]
        else:
            cur.execute("SELECT id,title,body,updated_at FROM notes ORDER BY updated_at DESC LIMIT 100"); rows=cur.fetchall()
        con.close()
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in rows:
            ts=datetime.fromtimestamp(r["updated_at"]).strftime("%m-%d %H:%M")
            # marcar si tiene tareas pendientes
            body=r["body"]; pend=body.count("- [ ]"); done=body.count("- [x]")
            suffix=f"  ☐{pend}" if pend else ""
            self.tree.insert("", tk.END, values=(r["id"], r["title"][:44]+suffix, ts))
        self.status.set(f"{len(rows)} notas" + (f" • filtro: {q}" if q else ""))

    def on_select_note(self, evt):
        sel=self.tree.selection()
        if not sel: return
        nid=int(self.tree.item(sel[0])["values"][0])
        con=db(); cur=con.cursor(); cur.execute("SELECT * FROM notes WHERE id=?", (nid,)); row=cur.fetchone(); con.close()
        if not row: return
        self.current_note_id=nid
        self.title_var.set(row["title"])
        self.text.delete("1.0", tk.END); self.text.insert("1.0", row["body"])
        self.auto_tag_hint()
        tasks=extract_tasks(row["body"]); pend=sum(1 for l in row["body"].splitlines() if l.startswith("- [ ]"))
        self.status.set(f"Nota #{nid} • {pend}/{len(tasks)} tareas • tags: {', '.join(re.findall(r'#(\\w+)', row['body']+row['title']))}")

    def new_note(self):
        tmpl_name=self.template_var.get()
        tmpl=TEMPLATES.get(tmpl_name, "")
        title_base=self.selected_date.strftime("%Y-%m-%d")
        body=tmpl.format(date=self.selected_date.strftime("%Y-%m-%d"), title=title_base)
        # si plantilla vacía, usar título según fecha
        title=title_base if tmpl_name=="Diario" else simpledialog.askstring("Nueva nota", f"Título ({tmpl_name}):", parent=self) or title_base
        if tmpl_name!="Diario" and "{title}" not in tmpl: body=body.replace("{title}", title)
        con=db(); cur=con.cursor(); now=int(time.time())
        cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (title, body, now, now))
        nid=cur.lastrowid
        update_backlinks(nid, body)
        con.commit(); con.close()
        self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
        for item in self.tree.get_children():
            if str(self.tree.item(item)["values"][0])==str(nid):
                self.tree.selection_set(item); self.tree.see(item); break
        self.on_select_note(None); self.title_entry.focus_set()

    def save_note(self):
        if not self.current_note_id:
            if not self.title_var.get().strip() and not self.text.get("1.0", tk.END).strip():
                messagebox.showinfo("Guardar", "Nada que guardar"); return
            con=db(); cur=con.cursor(); now=int(time.time())
            cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (self.title_var.get() or "Sin título", self.text.get("1.0", tk.END).strip(), now, now))
            self.current_note_id=cur.lastrowid
            update_backlinks(self.current_note_id, self.text.get("1.0", tk.END).strip())
            con.commit(); con.close()
            self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
            self.status.set(f"Nota creada #{self.current_note_id}"); return
        con=db(); cur=con.cursor(); now=int(time.time())
        cur.execute("UPDATE notes SET title=?, body=?, updated_at=? WHERE id=?", (self.title_var.get(), self.text.get("1.0", tk.END).strip(), now, self.current_note_id))
        body=self.text.get("1.0", tk.END)
        tags=re.findall(r"#(\w+)", self.title_var.get()+" "+body)
        cur.execute("DELETE FROM note_tags WHERE note_id=?", (self.current_note_id,))
        for t in tags:
            cur.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (t,))
            cur.execute("SELECT id FROM tags WHERE name=?", (t,)); tid=cur.fetchone()[0]
            cur.execute("INSERT OR IGNORE INTO note_tags(note_id,tag_id) VALUES(?,?)", (self.current_note_id, tid))
        update_backlinks(self.current_note_id, body)
        con.commit(); con.close()
        self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
        self.status.set(f"Guardado #{self.current_note_id} ✓ — {body.count('- [ ]')} pendientes")

    def delete_note(self):
        if not self.current_note_id: return
        if not messagebox.askyesno("Borrar", f"¿Borrar nota #{self.current_note_id}?"): return
        con=db(); con.execute("DELETE FROM notes WHERE id=?", (self.current_note_id,)); con.commit(); con.close()
        self.current_note_id=None; self.title_var.set(""); self.text.delete("1.0", tk.END)
        self.refresh_notes(); self.refresh_tasks(); self.refresh_tag_cloud()

    def auto_tag_hint(self):
        txt=self.title_var.get()+" "+self.text.get("1.0", tk.END)
        tags=re.findall(r"#(\w+)", txt); links=re.findall(r"\[\[([^\]]+)\]\]", txt)
        tasks=re.findall(r"^- \[[ xX]\]", txt, flags=re.MULTILINE)
        hint="Tags: "+",".join(tags) if tags else ""
        if links: hint += "  Enlaces: "+",".join(links)
        if tasks: hint += f"  Tareas: {len(tasks)}"
        if hint: self.status.set(hint)

    def insert_task(self): self.text.insert(tk.INSERT, "- [ ] "); self.text.focus_set()
    def insert_link(self):
        sel=simpledialog.askstring("Enlace", "Nombre del enlace [[...]]:", parent=self)
        if sel: self.text.insert(tk.INSERT, f"[[{sel}]]")
    def insert_tag(self):
        tag=simpledialog.askstring("Tag", "Tag sin #:", parent=self)
        if tag: self.text.insert(tk.INSERT, f"#{tag} ")

    def toggle_task_in_editor(self):
        try:
            # línea actual
            idx=self.text.index(tk.INSERT)
            line_no=int(idx.split(".")[0])
            start=f"{line_no}.0"; end=f"{line_no}.end"
            line=self.text.get(start,end)
            if re.match(r"^- \[[ xX]\]", line):
                new=toggle_task_line(line)
                self.text.delete(start,end); self.text.insert(start,new)
                self.status.set("Tarea toggled — Ctrl+S para guardar")
            else:
                # convertir línea actual a tarea
                if line.strip(): 
                    self.text.delete(start,end); self.text.insert(start, f"- [ ] {line}")
                else: self.text.insert(start, "- [ ] ")
        except Exception as e: messagebox.showerror("Toggle", str(e))

    # Tasks panel
    def refresh_tasks(self):
        self.task_list.delete(0, tk.END)
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body FROM notes"); rows=cur.fetchall(); con.close()
        self._task_map=[] # (nid, line_idx, text)
        for r in rows:
            for i,line in enumerate(r["body"].splitlines()):
                m=re.match(r"^- \[([ xX])\] (.+)", line)
                if m:
                    done=m.group(1).lower()=="x"
                    icon="☑" if done else "☐"
                    self.task_list.insert(tk.END, f"{icon} {m.group(2)[:48]}  — {r['title'][:20]} #{r['id']}")
                    self.task_list.itemconfig(tk.END, fg="#888" if done else "#000")
                    self._task_map.append((r["id"], i, line))
        # also pending count in title
        pend=sum(1 for _,_,l in self._task_map if l.startswith("- [ ]"))
        self.left_nb.tab(1, text=f"✅ Tareas ({pend})")

    def on_toggle_task_global(self, evt):
        sel=self.task_list.curselection()
        if not sel: return
        idx=sel[0]; nid, line_idx, _ = self._task_map[idx]
        con=db(); cur=con.cursor(); cur.execute("SELECT body FROM notes WHERE id=?", (nid,)); body=cur.fetchone()["body"]
        lines=body.splitlines()
        lines[line_idx]=toggle_task_line(lines[line_idx])
        new_body="\n".join(lines)
        cur.execute("UPDATE notes SET body=?, updated_at=? WHERE id=?", (new_body, int(time.time()), nid)); con.commit(); con.close()
        self.refresh_tasks()
        if self.current_note_id==nid:
            self.text.delete("1.0", tk.END); self.text.insert("1.0", new_body)

    # Events
    def refresh_events(self):
        self.event_list.delete(0, tk.END)
        con=db(); cur=con.cursor()
        dt=self.selected_date
        start=int(datetime(dt.year, dt.month, 1).timestamp())
        end=int(datetime(dt.year+1,1,1).timestamp()) if dt.month==12 else int(datetime(dt.year, dt.month+1,1).timestamp())
        cur.execute("SELECT id,title,start_ts,end_ts,note_id FROM events WHERE start_ts>=? AND start_ts<? ORDER BY start_ts", (start,end))
        self._event_ids=[]
        for r in cur.fetchall():
            d=datetime.fromtimestamp(r["start_ts"]).strftime("%d %H:%M")
            suffix=f" → nota #{r['note_id']}" if r["note_id"] else ""
            self.event_list.insert(tk.END, f"{d}  {r['title']}{suffix}"); self._event_ids.append(r["id"])
        con.close()

    def new_event(self):
        title=simpledialog.askstring("Nuevo evento", "Título del evento:", parent=self)
        if not title: return
        dt=self.selected_date.replace(hour=10, minute=0, second=0)
        start=int(dt.timestamp()); end=start+3600
        hora=simpledialog.askstring("Hora", "Hora inicio (HH:MM) o deja 10:00:", initialvalue="10:00", parent=self)
        if hora:
            try: h,m=map(int, hora.split(":")); dt=dt.replace(hour=h, minute=m); start=int(dt.timestamp()); end=start+3600
            except: pass
        desc=simpledialog.askstring("Descripción", "Descripción (opcional):", parent=self) or ""
        con=db(); cur=con.cursor(); uid=f"{int(time.time())}-{start}@gnote.local"
        cur.execute("INSERT INTO events(title,description,location,start_ts,end_ts,uid,source,created_at,note_id) VALUES(?,?,?,?,?,?,?,?,?)",
                    (title, desc, "", start, end, uid, "local", int(time.time()), self.current_note_id or None))
        con.commit(); con.close(); self.refresh_calendar()

    def delete_event(self):
        sel=self.event_list.curselection()
        if not sel: return
        eid=self._event_ids[sel[0]]
        if not messagebox.askyesno("Borrar", "¿Borrar evento?"): return
        con=db(); con.execute("DELETE FROM events WHERE id=?", (eid,)); con.commit(); con.close(); self.refresh_calendar()

    def link_event_note(self):
        sel=self.event_list.curselection()
        if not sel: messagebox.showinfo("Vincular", "Selecciona un evento del mes primero"); return
        if not self.current_note_id: messagebox.showinfo("Vincular", "Selecciona una nota a vincular"); return
        eid=self._event_ids[sel[0]]
        con=db(); con.execute("UPDATE events SET note_id=? WHERE id=?", (self.current_note_id, eid)); con.commit(); con.close()
        self.refresh_events(); self.status.set(f"Evento #{eid} vinculado a nota #{self.current_note_id}")

    def on_edit_event(self, evt):
        sel=self.event_list.curselection()
        if not sel: return
        eid=self._event_ids[sel[0]]
        con=db(); cur=con.cursor(); cur.execute("SELECT * FROM events WHERE id=?", (eid,)); row=cur.fetchone(); con.close()
        if row: messagebox.showinfo("Evento", f"{row['title']}\n{datetime.fromtimestamp(row['start_ts'])}\n→ {datetime.fromtimestamp(row['end_ts'])}\n{row['description']}\nNota vinculada: {row['note_id'] or 'ninguna'}")

    # Export / Import
    def export_ics(self):
        path=filedialog.asksaveasfilename(defaultextension=".ics", filetypes=[("Calendario", "*.ics")], initialfile="calendario.ics", parent=self)
        if not path: return
        if os.path.exists(BIN_PATH):
            r=subprocess.run([BIN_PATH, "ics", "export", "--output", path], capture_output=True, text=True)
            if r.returncode==0: messagebox.showinfo("Exportar", r.stdout.strip())
            else: messagebox.showerror("Error", r.stderr or r.stdout)
        else:
            con=db(); cur=con.cursor(); cur.execute("SELECT * FROM events"); rows=cur.fetchall(); con.close()
            with open(path,"w",encoding="utf-8") as f:
                f.write("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//gnote-calendar//ES\r\n")
                for r in rows:
                    f.write("BEGIN:VEVENT\r\n"); f.write(f"UID:{r['uid']}\r\n")
                    f.write(f"DTSTART:{datetime.fromtimestamp(r['start_ts']).strftime('%Y%m%dT%H%M%SZ')}\r\n")
                    f.write(f"DTEND:{datetime.fromtimestamp(r['end_ts']).strftime('%Y%m%dT%H%M%SZ')}\r\n")
                    f.write(f"SUMMARY:{r['title']}\r\n")
                    if r['description']: f.write(f"DESCRIPTION:{r['description']}\r\n")
                    f.write("END:VEVENT\r\n")
                f.write("END:VCALENDAR\r\n")
            messagebox.showinfo("Exportar", f"Exportados {len(rows)} eventos a {path}")

    def import_ics(self):
        path=filedialog.askopenfilename(filetypes=[("Calendario", "*.ics"), ("Todos", "*.*")], parent=self)
        if not path: return
        if os.path.exists(BIN_PATH):
            r=subprocess.run([BIN_PATH, "ics", "import", path], capture_output=True, text=True)
            messagebox.showinfo("Importar", (r.stdout+r.stderr).strip())
        else: messagebox.showinfo("Importar", "Usa el binario para importar")
        self.refresh_calendar()

    def export_markdown(self):
        if not self.current_note_id: messagebox.showinfo("Export", "Selecciona una nota"); return
        path=filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")], initialfile=f"nota-{self.current_note_id}.md", parent=self)
        if not path: return
        title=self.title_var.get(); body=self.text.get("1.0", tk.END)
        with open(path,"w",encoding="utf-8") as f: f.write(f"# {title}\n\n{body}\n")
        messagebox.showinfo("Export", f"Nota exportada a {path}")

    # Pomodoro
    def open_pomodoro(self):
        if self.pomodoro_win and self.pomodoro_win.winfo_exists(): self.pomodoro_win.lift(); return
        self.pomodoro_win=Pomodoro(self)

    # Stats
    def show_folder_sync(self):
        cur=get_sync_folder()
        win=tk.Toplevel(self); win.title("Folder Sync — Knowledge OS"); win.geometry("480x300")
        ttk.Label(win, text="Carpeta sync (1 .md por nota):", font=("TkDefaultFont",9,"bold")).pack(anchor="w", padx=12, pady=6)
        var=tk.StringVar(value=cur)
        ttk.Entry(win, textvariable=var).pack(fill=tk.X, padx=12)
        def choose():
            p=filedialog.askdirectory(parent=win, initialdir=cur)
            if p: var.set(p)
        ttk.Button(win, text="Elegir carpeta…", command=choose).pack(padx=12, pady=4)
        info=tk.Text(win, height=6, wrap=tk.WORD); info.pack(fill=tk.BOTH, padx=12, pady=6)
        info.insert("1.0", f"Actual: {cur}\n\n• Exporta notas → .md con frontmatter id/title\n• Importa .md → notas (bidireccional)\n• Compatible Syncthing/Nextcloud/Git\n• Usa CLI: gnote-calendar sync --folder ~/Notas")
        info.config(state=tk.DISABLED)
        def do_sync():
            folder=var.get().strip() or cur
            set_sync_folder(folder)
            if os.path.exists(BIN_PATH):
                import subprocess
                r=subprocess.run([BIN_PATH, "sync", "--folder", folder], capture_output=True, text=True)
                body=(r.stdout+r.stderr).strip() or "Sincronizado"
            else:
                # fallback python
                body=self._python_sync(folder)
            messagebox.showinfo("Sync", body, parent=win)
            self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
            self.status.set(f"Sync → {folder}")
            win.destroy()
        ttk.Button(win, text="Sincronizar ahora", command=do_sync).pack(pady=6)
        ttk.Button(win, text="Cerrar", command=win.destroy).pack()

    def _python_sync(self, folder):
        import pathlib
        os.makedirs(folder, exist_ok=True)
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body FROM notes")
        exp=0
        for r in cur.fetchall():
            safe="".join(c if c.isalnum() or c in "-_" else "-" if c==" " else "" for c in r["title"])[:40] or "nota"
            path=os.path.join(folder, f"{r['id']:04d}-{safe}.md")
            front=f"---\nid: {r['id']}\ntitle: \"{r['title']}\"\n---\n\n{r['body']}\n"
            if not os.path.exists(path) or open(path).read()!=front:
                open(path,"w",encoding="utf-8").write(front); exp+=1
        con.close()
        return f"Exportados {exp} (fallback)"

    def show_stats(self):
        con=db(); cur=con.cursor()
        cur.execute("SELECT COUNT(*) FROM notes"); n_notes=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM events"); n_ev=cur.fetchone()[0]
        cur.execute("SELECT body FROM notes"); bodies=[r[0] for r in cur.fetchall()]
        tasks=sum(b.count("- [ ]")+b.count("- [x]") for b in bodies)
        pend=sum(b.count("- [ ]") for b in bodies)
        tags=set(re.findall(r"#(\w+)", "".join(bodies)))
        cur.execute("SELECT COUNT(*) FROM backlinks"); n_links=cur.fetchone()[0] if cur else 0
        con.close()
        messagebox.showinfo("Estadísticas", f"📝 Notas: {n_notes}\n📅 Eventos: {n_ev}\n✅ Tareas: {pend}/{tasks} pendientes\n🏷️ Tags: {len(tags)}\n🔗 Enlaces: {n_links}\n📁 Sync: {get_sync_folder()}\n\nDB: {DB_PATH}\nBinario: {BIN_PATH if os.path.exists(BIN_PATH) else 'no compilado'}")

    # Graph
    def show_graph(self):
        win=tk.Toplevel(self); win.title("Grafo de enlaces [[...]]"); win.geometry("600x400")
        canvas=tk.Canvas(win, bg="white"); canvas.pack(fill=tk.BOTH, expand=True)
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body FROM notes"); rows=cur.fetchall(); con.close()
        # nodos
        nodes=[(r["id"], r["title"][:18]) for r in rows]
        if not nodes: canvas.create_text(300,200, text="Sin notas para grafo\nUsa [[enlace]] en tus notas", justify=tk.CENTER); return
        # layout circular
        import math
        cx,cy=300,200; R=130
        pos={}
        for i,(nid,title) in enumerate(nodes):
            ang=2*math.pi*i/max(1,len(nodes)); x=cx+R*math.cos(ang); y=cy+R*math.sin(ang); pos[nid]=(x,y)
            canvas.create_oval(x-40,y-18,x+40,y+18, fill="#e3f2fd", outline="#4a90e2")
            canvas.create_text(x,y, text=title, font=("TkDefaultFont",7), width=75, justify=tk.CENTER)
        # aristas
        for r in rows:
            for link in re.findall(r"\[\[([^\]]+)\]\]", r["body"]):
                # buscar id por título
                target=None
                for nid,title in nodes:
                    if title.strip().lower() in link.lower() or link.lower() in title.lower():
                        target=nid; break
                if target and target in pos and r["id"] in pos:
                    x1,y1=pos[r["id"]]; x2,y2=pos[target]
                    canvas.create_line(x1,y1,x2,y2, fill="#999", arrow=tk.LAST, width=1)

    def check_upcoming(self):
        # cada 60s revisa eventos próximos 15min
        try:
            con=db(); cur=con.cursor()
            now=int(time.time())
            cur.execute("SELECT title,start_ts FROM events WHERE start_ts>=? AND start_ts<=? ORDER BY start_ts LIMIT 3", (now, now+900))
            for r in cur.fetchall():
                try: subprocess.run(["notify-send", f"⏰ {r['title']}", f"Empieza {datetime.fromtimestamp(r['start_ts']).strftime('%H:%M')}"], timeout=1)
                except: pass
            con.close()
        except: pass
        self.after(60000, self.check_upcoming)

    def auto_folder_sync(self):
        folder=get_sync_folder()
        if os.path.isdir(folder) and os.path.exists(BIN_PATH):
            try:
                import subprocess
                r=subprocess.run([BIN_PATH, "sync", "--folder", folder], capture_output=True, text=True, timeout=3)
                if "Importados" in r.stdout or "Exportados" in r.stdout:
                    # heuristic refresh
                    self.refresh_notes(); self.refresh_tasks()
            except: pass
        self.after(5000, self.auto_folder_sync)

if __name__=="__main__":
    ensure_db()
    app=App()
    app.mainloop()
