#!/usr/bin/env python3
# gnote-calendar GUI Qt6 (PySide6) v2.1 - Knowledge OS Obsidian + Proyectos
# RAM <60MB · Notas Obsidian con vault/proyectos, markdown toolbar, modos separados
# Fallback: PySide6 -> PySide2 -> PyQt5 (apt). Offline-first, WAL.
import os, sys, re, subprocess, time, calendar, sqlite3, json
from datetime import datetime, timedelta, date
try:
    import markdown as md_lib
    HAS_MARKDOWN = True
except: 
    md_lib = None
    HAS_MARKDOWN = False

# --- Design Tokens v2.1: separación visual ---
THEME = {
    "bg_app": "#f5f7f9",
    "bg_surface": "#ffffff",
    "bg_alt": "#fbfcfe",
    "border": "#e1e4e8",
    "border_strong": "#c9d2dc",
    "accent": "#4a90e2",
    "accent_light": "#e3f2fd",
    "text": "#1a1a1a",
    "muted": "#6b7280",
    "radius": 10,
    "gap": 14,
    "gap_sm": 8,
    "shadow": "0 1px 3px rgba(0,0,0,0.06)",
}
EDITOR_MODE_SOURCE = 0
EDITOR_MODE_PREVIEW = 1
EDITOR_MODE_SPLIT = 2

PROJECT_COLORS = ["#4a90e2","#7c4dff","#00bfa5","#ff7043","#ab47bc","#26c6da","#66bb6a","#ffa726"]
PROJECT_ICONS = ["📁","📘","🚀","💡","📐","🎯","🔬","📊"]


# Compat layer Qt
QT_LIB = None
QT_AVAILABLE = False
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
        QCalendarWidget, QTabWidget, QListWidget, QListWidgetItem, QTextEdit, QTextBrowser,
        QLineEdit, QComboBox, QPushButton, QLabel, QToolBar, QStatusBar,
        QMenuBar, QMenu, QFileDialog, QMessageBox, QInputDialog, QDialog,
        QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem,
        QGraphicsLineItem, QHeaderView, QTableWidget, QTableWidgetItem, QFrame,
        QStackedWidget, QScrollArea, QSizePolicy, QButtonGroup, QToolButton, QSystemTrayIcon
    )
    from PySide6.QtCore import Qt, QTimer, QDate, QFileSystemWatcher, Signal, Slot, QRectF, QPointF, QSettings, QSize
    from PySide6.QtGui import QAction, QTextCharFormat, QColor, QBrush, QPen, QFont, QPainter, QTextCursor, QSyntaxHighlighter, QKeySequence, QIcon
    QT_LIB = "PySide6"
    QT_AVAILABLE = True
except ImportError as _e1:
    try:
        from PySide2.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
            QCalendarWidget, QTabWidget, QListWidget, QListWidgetItem, QTextEdit, QTextBrowser,
            QLineEdit, QComboBox, QPushButton, QLabel, QToolBar, QStatusBar,
            QMenuBar, QMenu, QFileDialog, QMessageBox, QInputDialog, QDialog,
            QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem,
            QGraphicsLineItem, QHeaderView, QTableWidget, QTableWidgetItem, QFrame,
            QStackedWidget, QScrollArea, QSizePolicy, QButtonGroup, QToolButton, QSystemTrayIcon
        )
        from PySide2.QtCore import Qt, QTimer, QDate, QFileSystemWatcher, Signal, Slot, QRectF, QPointF, QSettings, QSize
        from PySide2.QtGui import QTextCharFormat, QColor, QBrush, QPen, QFont, QPainter, QTextCursor, QSyntaxHighlighter, QKeySequence, QIcon
        from PySide2.QtWidgets import QAction
        QT_LIB = "PySide2"
        QT_AVAILABLE = True
    except ImportError as _e2:
        try:
            from PyQt5.QtWidgets import (
                QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                QCalendarWidget, QTabWidget, QListWidget, QListWidgetItem, QTextEdit, QTextBrowser,
                QLineEdit, QComboBox, QPushButton, QLabel, QToolBar, QStatusBar,
                QMenuBar, QMenu, QFileDialog, QMessageBox, QInputDialog, QDialog,
                QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem,
                QGraphicsLineItem, QHeaderView, QTableWidget, QTableWidgetItem, QFrame, QAction,
                QStackedWidget, QScrollArea, QSizePolicy, QButtonGroup, QToolButton, QSystemTrayIcon
            )
            from PyQt5.QtCore import Qt, QTimer, QDate, QFileSystemWatcher, QRectF, QPointF, QSettings, QSize, pyqtSignal as Signal, pyqtSlot as Slot
            from PyQt5.QtGui import QTextCharFormat, QColor, QBrush, QPen, QFont, QPainter, QTextCursor, QSyntaxHighlighter, QKeySequence, QIcon
            QT_LIB = "PyQt5"
            QT_AVAILABLE = True
        except ImportError as _e3:
            QT_AVAILABLE = False
            QT_LIB = None
            # Dummies para que el módulo cargue sin Qt (tests headless)
            class _Dummy: pass
            QApplication = QMainWindow = QWidget = QVBoxLayout = QHBoxLayout = QSplitter = _Dummy
            QCalendarWidget = QTabWidget = QListWidget = QListWidgetItem = QTextEdit = QTextBrowser = _Dummy
            QLineEdit = QComboBox = QPushButton = QLabel = QToolBar = QStatusBar = _Dummy
            QMenuBar = QMenu = QFileDialog = QMessageBox = QInputDialog = QDialog = _Dummy
            QGraphicsView = QGraphicsScene = QGraphicsEllipseItem = QGraphicsTextItem = QGraphicsItem = _Dummy
            QGraphicsLineItem = QHeaderView = QTableWidget = QTableWidgetItem = QFrame = _Dummy
            QStackedWidget = QScrollArea = QSizePolicy = QButtonGroup = QToolButton = QSystemTrayIcon = _Dummy
            QAction = _Dummy
            Qt = QTimer = QDate = QFileSystemWatcher = Signal = Slot = QRectF = QPointF = QSettings = _Dummy
            QSize = _Dummy
            QTextCharFormat = QColor = QBrush = QPen = QFont = QPainter = QTextCursor = QSyntaxHighlighter = QKeySequence = QIcon = _Dummy

DB_PATH = os.path.expanduser("~/.local/share/gnote-calendar/notes.db")
BIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build/gnote-calendar")
TEMPLATES = {
    "Diario": "#diario {date}\n## Mañana \u2600\ufe0f\n- [ ] Revisar agenda\n\n## Tarde\n- [ ] \n\n## Notas del d\u00eda\n\n## Gratitud\n- \n",
    "Reuni\u00f3n": "#reuni\u00f3n #{date} {title}\n**Fecha:** {date}  **Lugar:** \n\n## Asistentes\n- \n\n## Agenda\n1. \n2. \n\n## Acuerdos\n- [ ] \n\n## Notas\n",
    "Proyecto": "#proyecto {title}\n## \U0001f3af Objetivo\n\n\n## \U0001f4cb Tareas\n- [ ] Definir alcance\n- [ ] \n\n## \U0001f517 Enlaces\n[[Nota relacionada]]\n\n## \U0001f4dd Log\n",
    "Idea r\u00e1pida": "#idea {title}\n> {date}\n\n**Idea:** \n\n**Pasos:**\n- [ ] \n",
    "Vac\u00eda": ""
}

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(BIN_PATH):
        subprocess.run([BIN_PATH, "note", "list"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        cur.execute("SELECT count(*) FROM notes")
    except:
        schema_path = os.path.join(os.path.dirname(__file__), "data/schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path) as f:
                cur.executescript(f.read())
        else:
            cur.executescript("""
            CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '', location TEXT DEFAULT '', start_ts INTEGER NOT NULL, end_ts INTEGER NOT NULL, rrule TEXT DEFAULT '', note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL, uid TEXT UNIQUE, source TEXT DEFAULT 'local', created_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_ts);
            """)
        con.commit()
    # --- Migracion v2.1: projects + notes.project_id/vault_path ---
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        if not cur.fetchone():
            cur.executescript("""
            CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL UNIQUE, icon TEXT DEFAULT '📁', color TEXT DEFAULT '#4a90e2', description TEXT DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_projects_title ON projects(title);
            """)
            con.commit()
    except: pass
    for col, ddl in [("project_id","ALTER TABLE notes ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL DEFAULT NULL"), ("vault_path","ALTER TABLE notes ADD COLUMN vault_path TEXT DEFAULT ''")]:
        try:
            cur.execute(f"SELECT {col} FROM notes LIMIT 1")
        except:
            try:
                cur.execute(ddl); con.commit()
            except: pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_notes_project ON notes(project_id)")
        con.commit()
    except: pass
    try: backup_db()
    except: pass
    con.close()

def get_projects():
    try:
        con=db(); cur=con.cursor()
        cur.execute("SELECT id,title,icon,color,description FROM projects ORDER BY title COLLATE NOCASE")
        rows=cur.fetchall(); con.close()
        return rows
    except: return []

def create_project(title, icon="📁", color="#4a90e2", description=""):
    if not title or not title.strip():
        return None
    title=title.strip()
    try:
        con=db(); cur=con.cursor()
        now=int(time.time())
        cur.execute("INSERT INTO projects(title,icon,color,description,created_at,updated_at) VALUES(?,?,?,?,?,?)",(title,icon,color,description,now,now))
        pid=cur.lastrowid; con.commit(); con.close(); return pid
    except:
        try: con.close()
        except: pass
        return None

def parse_frontmatter_project(body):
    try:
        if body.startswith("---"):
            end=body.find("\n---",3)
            if end>0:
                fm=body[3:end]
                m=re.search(r"project:\s*[\"\']?([^\"\'\n]+)[\"\']?", fm)
                if m: return m.group(1).strip()
    except: pass
    return None

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
    except:
        pass

def ensure_daily_note():
    today = datetime.now().strftime("%Y-%m-%d")
    con = db(); cur = con.cursor()
    cur.execute("SELECT id FROM notes WHERE title=?", (today,))
    row = cur.fetchone()
    if row:
        con.close(); return row[0]
    body = TEMPLATES["Diario"].format(date=today, title=today)
    start = int(datetime.now().replace(hour=0, minute=0, second=0).timestamp())
    end = int(datetime.now().replace(hour=23, minute=59, second=59).timestamp())
    cur.execute("SELECT title, start_ts FROM events WHERE start_ts>=? AND start_ts<=? ORDER BY start_ts LIMIT 5", (start, end))
    evs = cur.fetchall()
    if evs:
        body += "\n## \U0001f4c5 Hoy\n"
        for e in evs:
            body += f"- {datetime.fromtimestamp(e['start_ts']).strftime('%H:%M')} {e['title']}\n"
    cur.execute("SELECT title, body FROM notes WHERE body LIKE '%- [ ]%'")
    pend = []
    for r in cur.fetchall():
        for line in r["body"].splitlines():
            if line.startswith("- [ ]"):
                pend.append(f"- [ ] {line[4:][:40]} \u2014 {r['title'][:16]}")
            if len(pend) >= 3:
                break
    if pend:
        body += "\n## \u26a0\ufe0f Pendientes\n" + "\n".join(pend[:5]) + "\n"
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
            except:
                pass
    return os.path.expanduser("~/Notas")

def set_sync_folder(folder):
    p = os.path.expanduser("~/.config/gnote-calendar/config.ini")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    cfg = {}
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k,v = line.split("=",1); cfg[k.strip()] = v.strip()
    cfg["sync_folder"] = folder
    with open(p,"w") as f:
        for k,v in cfg.items():
            f.write(f"{k}={v}\n")

def toggle_task_line(line):
    if re.match(r"^- \[ \]", line):
        return re.sub(r"^- \[ \]", "- [x]", line, count=1)
    if re.match(r"^- \[[xX]\]", line):
        return re.sub(r"^- \[[xX]\]", "- [ ]", line, count=1)
    return line

def backup_db():
    # Fase 5: backup auto rotativo notes.db.bak-YYYYMMDD al iniciar, si no existe hoy
    try:
        db_path = DB_PATH
        if not os.path.exists(db_path):
            return
        bak = f"{db_path}.bak-{date.today().isoformat()}"
        if os.path.exists(bak):
            return
        # copiar solo si db >0
        if os.path.getsize(db_path) > 0:
            import shutil
            shutil.copy2(db_path, bak)
            # rotar: mantener solo últimos 7
            import glob
            for old in sorted(glob.glob(f"{db_path}.bak-*"))[:-7]:
                try: os.remove(old)
                except: pass
    except: pass

# Placeholders definidos arriba si QT_AVAILABLE==False. Solo definir clases Qt si disponible.
if QT_AVAILABLE:
    class SearchHighlighter(QSyntaxHighlighter):
        def __init__(self, parent):
            super().__init__(parent)
            self.query = ""
            self.fmt = QTextCharFormat()
            self.fmt.setBackground(QColor("#fff176"))
        def setQuery(self, q):
            qs = re.sub(r"tag:\w+|#\w+", "", q).strip()
            qs = re.sub(r"fecha:\S+", "", qs).strip()
            qs = re.sub(r"project:\S+", "", qs).strip()
            self.query = qs
            self.rehighlight()
        def highlightBlock(self, text):
            if not self.query:
                return
            for m in re.finditer(re.escape(self.query), text, re.IGNORECASE):
                self.setFormat(m.start(), m.end()-m.start(), self.fmt)

    class MarkdownHighlighter(QSyntaxHighlighter):
        def __init__(self, parent):
            super().__init__(parent)
            self.fmt_tag = QTextCharFormat(); self.fmt_tag.setForeground(QColor("#1e88e5")); self.fmt_tag.setFontWeight(QFont.Bold)
            self.fmt_link = QTextCharFormat(); self.fmt_link.setForeground(QColor("#2e7d32")); self.fmt_link.setFontWeight(QFont.Bold)
            self.fmt_bold = QTextCharFormat(); self.fmt_bold.setFontWeight(QFont.Bold)
            self.fmt_italic = QTextCharFormat(); self.fmt_italic.setFontItalic(True)
            self.fmt_code = QTextCharFormat(); self.fmt_code.setBackground(QColor("#f6f8fa")); self.fmt_code.setForeground(QColor("#c7254e")); self.fmt_code.setFontFamily("Monospace")
            self.fmt_h = QTextCharFormat(); self.fmt_h.setForeground(QColor("#4a148c")); self.fmt_h.setFontWeight(QFont.Bold)
            self.fmt_quote = QTextCharFormat(); self.fmt_quote.setForeground(QColor("#6d4c41")); self.fmt_quote.setFontItalic(True)
            self.fmt_task = QTextCharFormat(); self.fmt_task.setForeground(QColor("#00695c"))
        def highlightBlock(self, text):
            for m in re.finditer(r"#\w+", text):
                self.setFormat(m.start(), m.end()-m.start(), self.fmt_tag)
            for m in re.finditer(r"\[\[[^\]]+\]\]", text):
                self.setFormat(m.start(), m.end()-m.start(), self.fmt_link)
            for m in re.finditer(r"\*\*[^*]+\*\*", text):
                self.setFormat(m.start(), m.end()-m.start(), self.fmt_bold)
            for m in re.finditer(r"(?<!\*)\*[^*]+\*(?!\*)", text):
                self.setFormat(m.start(), m.end()-m.start(), self.fmt_italic)
            for m in re.finditer(r"`[^`]+`", text):
                self.setFormat(m.start(), m.end()-m.start(), self.fmt_code)
            if re.match(r"^#{1,6}\s", text):
                self.setFormat(0, len(text), self.fmt_h)
            if re.match(r"^>\s", text):
                self.setFormat(0, len(text), self.fmt_quote)
            if re.match(r"^- \[[ xX]\]", text):
                self.setFormat(0, len(text), self.fmt_task)

    class FlowLayout(QHBoxLayout):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setContentsMargins(0,0,0,0); self.setSpacing(6)
            self._widgets=[]
        def addWidget(self, w):
            super().addWidget(w); self._widgets.append(w)
        def takeAt(self, idx):
            if self._widgets:
                w=self._widgets.pop(idx) if idx<len(self._widgets) else None
            return super().takeAt(idx)
        def count(self):
            return super().count()
else:
    class SearchHighlighter:
        pass
    class MarkdownHighlighter:
        pass
    class FlowLayout:
        pass
    class MainWindowStub:
        @staticmethod
        def _python_sync(folder):
            os.makedirs(folder, exist_ok=True)
            con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body FROM notes")
            exp=0
            for r in cur.fetchall():
                safe="".join(c if c.isalnum() or c in "-_" else "-" if c==" " else "" for c in r["title"])[:40] or "nota"
                path=os.path.join(folder, f"{r['id']:04d}-{safe}.md")
                front=f"---\nid: {r['id']}\ntitle: \"{r['title']}\"\n---\n\n{r['body']}\n"
                if not os.path.exists(path) or open(path, encoding="utf-8").read()!=front:
                    open(path,"w",encoding="utf-8").write(front); exp+=1
            con.close()
            return f"Exportados {exp} (fallback)"

class CalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.counts = {}  # day -> count
        # lightweight style
        self.setStyleSheet("QCalendarWidget QWidget { alternate-background-color: #f0f0f0; }")
    def _on_clicked(self, date):
        # handled by MainWindow via QCalendarWidget.clicked signal; stub
        pass
    def setCounts(self, counts):
        self.counts = counts
        self.updateCells()
    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        # puntos verdes para eventos, hoy azul ya lo hace QCalendar, añadimos indicador
        d = date.day()
        has_evt = d in self.counts and date.month() == self.monthShown() and date.year() == self.yearShown()
        is_today = date == QDate.currentDate()
        if has_evt and not is_today:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#4caf50"))
            # punto abajo centro
            r = 3
            cx = rect.center().x()
            cy = rect.bottom() - 5
            painter.drawEllipse(QPointF(cx, cy), r, r)
            # número pequeño count si >1
            if self.counts[d] > 1:
                painter.setPen(QColor("#2e7d32"))
                painter.setFont(QFont("Sans", 6))
                painter.drawText(rect, Qt.AlignRight|Qt.AlignBottom, str(self.counts[d]))
            painter.restore()
        # highlight seleccionado con fondo ya lo hace calendar

class PomodoroDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pomodoro \u2014 25:00")
        self.setFixedSize(280, 180)
        self.remaining = 25*60
        self.running = False
        self.mode = "work"
        layout = QVBoxLayout(self)
        self.label = QLabel("25:00", self)
        self.label.setAlignment(Qt.AlignCenter)
        f = QFont(); f.setPointSize(36); f.setBold(True)
        self.label.setFont(f)
        layout.addWidget(self.label)
        self.mode_label = QLabel("\U0001f345 Trabajo \u2014 enf\u00f3cate", self)
        self.mode_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mode_label)
        btns = QHBoxLayout()
        b1 = QPushButton("Iniciar", self); b1.clicked.connect(self.start); b1.setStyleSheet("background:#4a90e2; color:white;")
        b2 = QPushButton("Pausa", self); b2.clicked.connect(self.pause)
        b3 = QPushButton("Reset", self); b3.clicked.connect(self.reset)
        btns.addWidget(b1); btns.addWidget(b2); btns.addWidget(b3)
        layout.addLayout(btns)
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(1000)
    def start(self): self.running = True
    def pause(self): self.running = False
    def reset(self):
        self.running=False; self.mode="work"; self.remaining=25*60
        self.label.setText("25:00"); self.mode_label.setText("\U0001f345 Trabajo"); self.setWindowTitle("Pomodoro \u2014 25:00")
    def tick(self):
        if self.running and self.remaining>0:
            self.remaining-=1
            m,s=divmod(self.remaining,60)
            self.label.setText(f"{m:02d}:{s:02d}")
            self.setWindowTitle(f"Pomodoro \u2014 {m:02d}:{s:02d}")
            if self.remaining==0:
                self.running=False
                try: subprocess.run(["notify-send","Pomodoro","\u00a1Tiempo terminado!"], timeout=2)
                except: pass
                QMessageBox.information(self, "Pomodoro", "\u00a1Tiempo terminado! " + ("Descanso 5 min" if self.mode=="work" else "Vuelve al trabajo"))
                if self.mode=="work": self.mode="break"; self.remaining=5*60; self.mode_label.setText("\u2615 Descanso 5 min")
                else: self.mode="work"; self.remaining=25*60; self.mode_label.setText("\U0001f345 Trabajo")

class GraphView(QGraphicsView):
    def __init__(self, nodes, edges, current_id, on_navigate, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.nodes = nodes  # list dict {id,title,x,y}
        self.edges = edges
        self.current_id = current_id
        self.on_navigate = on_navigate
        self.items = {}  # id -> (ellipse, text)
        self._build()
        # physics timer
        self.timer = QTimer(self); self.timer.timeout.connect(self._physics); self.timer.start(33)
        self.dragging = None
    def _build(self):
        self.scene.clear()
        # edges
        self.edge_items = []
        for (src_idx, dst_idx) in self.edges:
            a = self.nodes[src_idx]; b = self.nodes[dst_idx]
            line = QGraphicsLineItem(a["x"], a["y"], b["x"], b["y"])
            line.setPen(QPen(QColor("#999"), 1))
            self.scene.addItem(line)
            self.edge_items.append(line)
        # nodes
        for n in self.nodes:
            is_cur = (n["id"] == self.current_id)
            color = QColor("#4a90e2") if is_cur else QColor("#e3f2fd")
            ell = self.scene.addEllipse(n["x"]-30, n["y"]-20, 60, 40, QPen(QColor("#4a90e2"), 1.2), QBrush(color))
            try:
                ell.setFlag(QGraphicsItem.ItemIsMovable, True)
            except:
                try: ell.setFlag(ell.GraphicsItemFlag.ItemIsMovable, True)
                except: pass
            ell.setData(0, n["id"])
            txt = self.scene.addText(n["title"][:18])
            txt.setDefaultTextColor(QColor("#222"))
            f = QFont("Sans", 7); txt.setFont(f)
            br = txt.boundingRect()
            txt.setPos(n["x"]-br.width()/2, n["y"]-br.height()/2)
            try:
                txt.setFlag(QGraphicsItem.ItemIsMovable, False)
            except:
                try: txt.setFlag(txt.GraphicsItemFlag.ItemIsMovable, False)
                except: pass
            self.items[n["id"]] = (ell, txt, n)
        self.setSceneRect(-50,-50,800,600)
    def mousePressEvent(self, e):
        item = self.itemAt(e.pos())
        if item and item.data(0):
            nid = int(item.data(0))
            if self.on_navigate:
                self.on_navigate(nid)
        super().mousePressEvent(e)
    def _physics(self):
        # simple repulsion + attraction, update positions
        import math, random
        moved = False
        for i,a in enumerate(self.nodes):
            # centre
            a.setdefault("vx",0); a.setdefault("vy",0)
            a["vx"] += (360 - a["x"])*0.004
            a["vy"] += (260 - a["y"])*0.004
            for j,b in enumerate(self.nodes):
                if i==j: continue
                dx=a["x"]-b["x"]; dy=a["y"]-b["y"]; d2=dx*dx+dy*dy
                if d2<1: d2=1
                if d2<90000:
                    f=900/(d2)
                    d=math.sqrt(d2)
                    a["vx"] += dx/d*f*0.06; a["vy"] += dy/d*f*0.06
            a["vx"]*=0.85; a["vy"]*=0.85
        for (i,j) in self.edges:
            a=self.nodes[i]; b=self.nodes[j]
            dx=b["x"]-a["x"]; dy=b["y"]-a["y"]; d=math.sqrt(dx*dx+dy*dy)
            if d>1:
                f=(d-100)*0.015
                a["vx"] += dx/d*f; a["vy"] += dy/d*f
                b["vx"] -= dx/d*f; b["vy"] -= dy/d*f
        for n in self.nodes:
            # check if being dragged: skip
            ell = self.items[n["id"]][0]
            if ell.isSelected():
                n["x"]=ell.scenePos().x()+30; n["y"]=ell.scenePos().y()+20
                n["vx"]=n["vy"]=0
                continue
            n["x"]+=n["vx"]; n["y"]+=n["vy"]
            n["x"]=max(40,min(680,n["x"])); n["y"]=max(30,min(520,n["y"]))
            # update graphics
            ell.setPos(n["x"]-30 - ell.rect().x() if hasattr(ell,'rect') else 0, n["y"]-20 - ell.rect().y() if hasattr(ell,'rect') else 0)
            # Actually use setPos delta: simpler rebuild edge positions each frame
            moved=True
        if moved:
            # update edges
            for idx,(src_idx,dst_idx) in enumerate(self.edges):
                a=self.nodes[src_idx]; b=self.nodes[dst_idx]
                self.edge_items[idx].setLine(a["x"],a["y"],b["x"],b["y"])
            # update texts
            for n in self.nodes:
                _, txt, _ = self.items[n["id"]]
                br = txt.boundingRect()
                txt.setPos(n["x"]-br.width()/2, n["y"]-br.height()/2)
            self.scene.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("gnote-calendar — Notas y Calendario (Qt)")
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.setMinimumSize(1100, 650)
        self.resize(1380, 840)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.current_note_id = None
        self.current_project_id = None
        self.selected_date = datetime.now()
        self.pomodoro_win = None
        self._event_ids = []
        self._task_map = []
        self.watcher = None
        self._current_section = 0
        self.editor_mode = EDITOR_MODE_SPLIT
        self._zen = False
        self._prev_splitter_sizes = None
        self._build_ui()
        try:
            ensure_db()
            backup_db()
            ensure_daily_note()
        except: pass
        self.refresh_projects()
        self.refresh_notes()
        self.refresh_calendar()
        self.refresh_tasks()
        self.refresh_tag_cloud()
        self.check_upcoming()
        QTimer.singleShot(5000, self.auto_folder_sync)
        self._setup_watcher()
        self._setup_tray()
        self._setup_accessibility()
        QTimer.singleShot(1000, lambda: self.statusBar().showMessage(f"Qt {QT_LIB} • Vault listo • #tag [[enlace]] • Ctrl+S guardar • Ctrl+B negrita • F9 preview • F11 zen", 5000))
        try: self._load_settings()
        except: pass

    def _build_ui(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&Archivo")
        act_export_md = QAction("Exportar .md", self); act_export_md.triggered.connect(self.export_markdown); file_menu.addAction(act_export_md)
        act_export_ics = QAction("Exportar .ics → Gmail", self); act_export_ics.triggered.connect(self.export_ics); file_menu.addAction(act_export_ics)
        act_import_ics = QAction("Importar .ics", self); act_import_ics.triggered.connect(self.import_ics); file_menu.addAction(act_import_ics)
        file_menu.addSeparator()
        act_quit = QAction("Salir", self); act_quit.triggered.connect(self.close); file_menu.addAction(act_quit)
        view_menu = menubar.addMenu("&Ver")
        act_stats = QAction("📊 Estadísticas", self); act_stats.triggered.connect(self.show_stats); view_menu.addAction(act_stats)
        act_graph = QAction("🕸️ Grafo", self); act_graph.triggered.connect(self.show_graph); view_menu.addAction(act_graph)
        act_full = QAction("Pantalla completa (F11)", self); act_full.setShortcut(QKeySequence("F11")); act_full.triggered.connect(self.toggle_maximize); view_menu.addAction(act_full)
        act_zen = QAction("Modo enfoque (F11 Zen)", self); act_zen.triggered.connect(self.toggle_zen); view_menu.addAction(act_zen)
        tool_menu = menubar.addMenu("&Herramientas")
        act_sync = QAction("📁 Folder Sync", self); act_sync.triggered.connect(self.show_folder_sync); tool_menu.addAction(act_sync)
        act_pomodoro = QAction("🍅 Pomodoro", self); act_pomodoro.triggered.connect(self.open_pomodoro); tool_menu.addAction(act_pomodoro)
        project_menu = menubar.addMenu("&Proyecto")
        act_new_proj = QAction("Nuevo proyecto", self); act_new_proj.triggered.connect(self.new_project_dialog); project_menu.addAction(act_new_proj)

        toolbar = QToolBar("Principal", self)
        toolbar.setObjectName("Principal")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16,16))
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.template_combo = QComboBox(self); self.template_combo.addItems(list(TEMPLATES.keys())); self.template_combo.setFixedWidth(128)
        self.template_combo.setToolTip("Plantilla para nueva nota")
        toolbar.addWidget(QLabel(" Plantilla: ")); toolbar.addWidget(self.template_combo)
        btn_new = QPushButton("➕ Nueva nota", self); btn_new.clicked.connect(self.new_note); btn_new.setStyleSheet("background:%s; color:white; font-weight:bold; padding:6px 12px; border-radius:8px;"%THEME["accent"]); btn_new.setToolTip("Ctrl+N")
        toolbar.addWidget(btn_new)
        btn_save = QPushButton("💾 Guardar", self); btn_save.clicked.connect(self.save_note); btn_save.setToolTip("Ctrl+S"); toolbar.addWidget(btn_save)
        btn_del = QPushButton("🗑 Borrar", self); btn_del.clicked.connect(self.delete_note); toolbar.addWidget(btn_del)
        toolbar.addSeparator()
        self.project_combo_toolbar = QComboBox(self); self.project_combo_toolbar.setFixedWidth(150); self.project_combo_toolbar.setToolTip("Filtrar por proyecto"); self.project_combo_toolbar.currentIndexChanged.connect(self.on_project_filter_changed)
        toolbar.addWidget(QLabel(" Proyecto:")); toolbar.addWidget(self.project_combo_toolbar)
        toolbar.addSeparator()
        btn_zen = QPushButton("⛶ Enfoque", self); btn_zen.clicked.connect(self.toggle_zen); btn_zen.setToolTip("F11 alterna zen"); toolbar.addWidget(btn_zen)
        btn_max = QPushButton("⛶ Maximizar", self); btn_max.clicked.connect(self.toggle_maximize); btn_max.setToolTip("F11"); toolbar.addWidget(btn_max)

        central = QWidget(self); central_layout = QHBoxLayout(central); central_layout.setContentsMargins(0,0,0,0); central_layout.setSpacing(0)
        self.setCentralWidget(central)

        sidebar = QFrame(self); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(102); sidebar.setFrameShape(QFrame.StyledPanel)
        self.sidebar = sidebar
        side_l = QVBoxLayout(sidebar); side_l.setContentsMargins(8,14,8,14); side_l.setSpacing(10)
        hdr = QLabel("SECCIONES", sidebar, alignment=Qt.AlignCenter); hdr.setStyleSheet("font-size:7.5pt; color:%s; font-weight:800; letter-spacing:1px;"%THEME["muted"]); side_l.addWidget(hdr)
        line = QFrame(sidebar); line.setFrameShape(QFrame.HLine); line.setStyleSheet("color:%s; max-height:1px;"%THEME["border"]); side_l.addWidget(line)
        self.nav_group = QButtonGroup(self); self.nav_group.setExclusive(True)
        sections = [("📝","Notas",0), ("📅","Calendario",1), ("✅","Tareas",2), ("🕸️","Grafo",3)]
        self.nav_buttons = {}
        for icon, name, idx in sections:
            btn = QToolButton(sidebar); btn.setText(f"{icon}\n{name}"); btn.setCheckable(True); btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setFixedSize(88, 68)
            btn.setIconSize(QSize(24,24))
            if idx==0: btn.setChecked(True)
            btn.clicked.connect(lambda _, i=idx: self.switch_section(i))
            side_l.addWidget(btn, alignment=Qt.AlignCenter); self.nav_group.addButton(btn, idx); self.nav_buttons[idx]=btn
        side_l.addSpacing(6)
        line2 = QFrame(sidebar); line2.setFrameShape(QFrame.HLine); line2.setStyleSheet("color:%s; max-height:1px;"%THEME["border"]); side_l.addWidget(line2)
        for icon, tip, cb in [("🍅","Pomodoro", self.open_pomodoro), ("📊","Stats", self.show_stats), ("📁","Sync", self.show_folder_sync)]:
            b = QToolButton(sidebar); b.setText(icon); b.setToolTip(tip); b.setFixedSize(88,36); b.clicked.connect(cb); side_l.addWidget(b, alignment=Qt.AlignCenter)
        side_l.addStretch()
        foot = QLabel(f"Qt {QT_LIB}", sidebar, alignment=Qt.AlignCenter); foot.setStyleSheet("font-size:7.5pt; color:%s;"%THEME["muted"]); side_l.addWidget(foot)
        central_layout.addWidget(sidebar)

        # === LAYOUT PRINCIPAL: sidebar + stacked FULL SCREEN por sección ===
        self.stacked = QStackedWidget(self)
        self.stacked.setStyleSheet("QStackedWidget { background: %s; }" % THEME["bg_app"])
        central_layout.addWidget(self.stacked)
        self.main_splitter = self.stacked
        self.central_splitter = self.stacked
        page_notas = QWidget(self); page_notas.setObjectName("PageNotas")
        page_notas.setStyleSheet("QWidget#PageNotas { background: %s; }" % THEME["bg_app"])
        pn_outer = QVBoxLayout(page_notas); pn_outer.setContentsMargins(0,0,0,0); pn_outer.setSpacing(0)
        self.notas_splitter = QSplitter(Qt.Horizontal, page_notas)
        self.notas_splitter.setHandleWidth(8)
        self.notas_splitter.setChildrenCollapsible(False)
        self.notas_splitter.setObjectName("NotasSplitter")
        pn_outer.addWidget(self.notas_splitter)
        left_panel = QWidget(page_notas); left_panel.setObjectName("NotasLeft")
        left_panel.setMinimumWidth(380); left_panel.setMaximumWidth(540)
        left_l = QVBoxLayout(left_panel); left_l.setContentsMargins(10,10,10,10); left_l.setSpacing(12)
        left_panel.setStyleSheet("QWidget#NotasLeft { background: %s; border-right: 1px solid %s; }" % (THEME["bg_surface"], THEME["border"]))
        # Vault filtros — siempre visible arriba (subsección 1)
        vault_card = QFrame(left_panel); vault_card.setObjectName("VaultCard"); vault_card.setStyleSheet("QFrame#VaultCard { background:%s; border:1px solid %s; border-radius:%dpx; }" % (THEME["bg_surface"], THEME["border"], THEME["radius"]))
        vault_layout = QVBoxLayout(vault_card); vault_layout.setContentsMargins(14,12,14,12); vault_layout.setSpacing(8)
        vault_head = QHBoxLayout(); vault_head.addWidget(QLabel("🗂️ Vault / Filtros", vault_card)); vault_head.addStretch()
        self.vault_path_label = QLabel(get_sync_folder(), vault_card); self.vault_path_label.setStyleSheet("color:%s; font-size:8px;" % THEME["muted"]); self.vault_path_label.setWordWrap(True); vault_head.addWidget(self.vault_path_label)
        btn_vault_open = QPushButton("Abrir", vault_card); btn_vault_open.setFixedHeight(26); btn_vault_open.setToolTip("Abrir carpeta vault"); btn_vault_open.clicked.connect(self.open_vault_folder); vault_head.addWidget(btn_vault_open)
        vault_layout.addLayout(vault_head)
        proj_row = QHBoxLayout(); proj_row.addWidget(QLabel("Proyecto:", vault_card))
        self.project_filter_combo = QComboBox(vault_card); self.project_filter_combo.setMinimumWidth(140); self.project_filter_combo.currentIndexChanged.connect(self.on_project_filter_changed); proj_row.addWidget(self.project_filter_combo)
        btn_new_proj = QPushButton("＋", vault_card); btn_new_proj.setFixedWidth(28); btn_new_proj.setToolTip("Nuevo proyecto"); btn_new_proj.clicked.connect(self.new_project_dialog); proj_row.addWidget(btn_new_proj)
        proj_row.addStretch()
        vault_layout.addLayout(proj_row)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Filtrar:", vault_card))
        self.search_entry = QLineEdit(vault_card); self.search_entry.setPlaceholderText("Buscar #tag texto…  fecha:hoy/semana  project:Nombre"); self.search_entry.setClearButtonEnabled(True)
        self.search_entry.textChanged.connect(self.refresh_notes)
        search_row.addWidget(self.search_entry, 1)
        btn_clear = QPushButton("✕", vault_card); btn_clear.setFixedWidth(28); btn_clear.setToolTip("Limpiar filtro Esc"); btn_clear.clicked.connect(lambda: self.search_entry.clear())
        search_row.addWidget(btn_clear)
        vault_layout.addLayout(search_row)
        hint = QLabel("Tip: tag:casa  fecha:hoy  project:MiProyecto  #tag  [[enlace]]  - [ ] tarea", vault_card); hint.setStyleSheet("color:#777; font-size:9px;"); hint.setWordWrap(True); vault_layout.addWidget(hint)
        tag_row = QHBoxLayout(); tag_row.addWidget(QLabel("Tags:", vault_card))
        self.tag_cloud = QHBoxLayout(); self.tag_cloud.setSpacing(5)
        tag_container = QWidget(vault_card); tag_container.setLayout(self.tag_cloud)
        tag_row.addWidget(tag_container, 1); tag_row.addStretch()
        btn_filter_clear = QPushButton("✕", vault_card); btn_filter_clear.setFixedWidth(28); btn_filter_clear.setToolTip("Limpiar filtro"); btn_filter_clear.clicked.connect(lambda: self.search_entry.clear()); tag_row.addWidget(btn_filter_clear)
        vault_layout.addLayout(tag_row)
        left_l.addWidget(vault_card)

        # Subsecciones con BOTONES — organización Notas (Pestañas con botones, no todo visible)
        sub_nav = QHBoxLayout(); sub_nav.setSpacing(6)
        sub_nav.addWidget(QLabel("Sección:", left_panel))
        self.left_nav_group = QButtonGroup(left_panel); self.left_nav_group.setExclusive(True)
        self.btn_sub_notas = QPushButton("📝 Notas", left_panel); self.btn_sub_notas.setCheckable(True); self.btn_sub_notas.setChecked(True); self.btn_sub_notas.setMinimumHeight(32); self.btn_sub_notas.setStyleSheet("QPushButton:checked { background:%s; color:white; font-weight:600; border:1px solid %s; border-radius:8px; } QPushButton { background:%s; border:1px solid %s; border-radius:8px; padding:6px 10px; }" % (THEME["accent"], THEME["accent"], THEME["bg_surface"], THEME["border"]))
        self.btn_sub_expl = QPushButton("📂 Explorador", left_panel); self.btn_sub_expl.setCheckable(True); self.btn_sub_expl.setMinimumHeight(32); self.btn_sub_expl.setStyleSheet("QPushButton:checked { background:%s; color:white; font-weight:600; border:1px solid %s; border-radius:8px; } QPushButton { background:%s; border:1px solid %s; border-radius:8px; padding:6px 10px; }" % (THEME["accent"], THEME["accent"], THEME["bg_surface"], THEME["border"]))
        self.btn_sub_evt = QPushButton("📅 Eventos", left_panel); self.btn_sub_evt.setCheckable(True); self.btn_sub_evt.setMinimumHeight(32); self.btn_sub_evt.setStyleSheet("QPushButton:checked { background:%s; color:white; font-weight:600; border:1px solid %s; border-radius:8px; } QPushButton { background:%s; border:1px solid %s; border-radius:8px; padding:6px 10px; }" % (THEME["accent"], THEME["accent"], THEME["bg_surface"], THEME["border"]))
        self.left_nav_group.addButton(self.btn_sub_notas, 0); self.left_nav_group.addButton(self.btn_sub_expl, 1); self.left_nav_group.addButton(self.btn_sub_evt, 2)
        sub_nav.addWidget(self.btn_sub_notas); sub_nav.addWidget(self.btn_sub_expl); sub_nav.addWidget(self.btn_sub_evt); sub_nav.addStretch()
        left_l.addLayout(sub_nav)

        self.left_substack = QStackedWidget(left_panel)
        self.left_substack.setStyleSheet("QStackedWidget { background: transparent; }")
        left_l.addWidget(self.left_substack, 1)

        # Sub-pagina 0: Notas
        notas_group = QWidget(self.left_substack); notas_l = QVBoxLayout(notas_group); notas_l.setContentsMargins(0,6,0,0); notas_l.setSpacing(8)
        notas_card = QFrame(notas_group); notas_card.setObjectName("NotasCard"); notas_card.setStyleSheet("QFrame#NotasCard { background:%s; border:1px solid %s; border-radius:8px; }" % (THEME["bg_surface"], THEME["border"]))
        notas_card_l = QVBoxLayout(notas_card); notas_card_l.setContentsMargins(8,8,8,8); notas_card_l.setSpacing(8)
        notas_card_l.addWidget(QLabel("📝 Notas — click abre en editor →", notas_card))
        self.notes_list = QListWidget(notas_card); self.notes_list.setAlternatingRowColors(True); self.notes_list.itemClicked.connect(self.on_select_note)
        self.notes_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        notas_card_l.addWidget(self.notes_list, 1)
        assign_row = QHBoxLayout(); assign_row.addWidget(QLabel("Mover:", notas_card))
        self.assign_project_combo = QComboBox(notas_card); assign_row.addWidget(self.assign_project_combo, 1)
        btn_assign = QPushButton("Asignar", notas_card); btn_assign.setFixedWidth(64); btn_assign.clicked.connect(self.assign_selected_to_project); assign_row.addWidget(btn_assign)
        btn_unassign = QPushButton("Quitar", notas_card); btn_unassign.setFixedWidth(56); btn_unassign.clicked.connect(self.unassign_selected_project); assign_row.addWidget(btn_unassign)
        notas_card_l.addLayout(assign_row)
        notas_l.addWidget(notas_card, 1)
        self.left_substack.addWidget(notas_group)

        # Sub-pagina 1: Explorador
        expl_group = QWidget(self.left_substack); expl_l = QVBoxLayout(expl_group); expl_l.setContentsMargins(0,6,0,0); expl_l.setSpacing(10)
        expl_card = QFrame(expl_group); expl_card.setObjectName("ExplCard"); expl_card.setStyleSheet("QFrame#ExplCard { background:%s; border:1px solid %s; border-radius:8px; }" % (THEME["bg_surface"], THEME["border"]))
        expl_card_l = QVBoxLayout(expl_card); expl_card_l.setContentsMargins(8,8,8,8); expl_card_l.setSpacing(8)
        expl_head = QHBoxLayout(); expl_head.addWidget(QLabel("📂 Explorador vault & proyectos", expl_card)); expl_head.addStretch()
        btn_refresh_expl = QPushButton("↻", expl_card); btn_refresh_expl.setFixedWidth(28); btn_refresh_expl.setToolTip("Actualizar"); btn_refresh_expl.clicked.connect(self.refresh_vault_explorer); expl_head.addWidget(btn_refresh_expl)
        expl_card_l.addLayout(expl_head)
        self.project_list = QListWidget(expl_card); self.project_list.setAlternatingRowColors(True); self.project_list.itemClicked.connect(self.on_project_selected); expl_card_l.addWidget(self.project_list, 1)
        proj_btns = QHBoxLayout(); b_new = QPushButton("＋ Nuevo", expl_card); b_new.clicked.connect(self.new_project_dialog); proj_btns.addWidget(b_new)
        b_del = QPushButton("Borrar", expl_card); b_del.clicked.connect(self.delete_project_dialog); proj_btns.addWidget(b_del)
        expl_card_l.addLayout(proj_btns)
        expl_card_l.addWidget(QLabel("Archivos .md", expl_card))
        self.vault_file_list = QListWidget(expl_card); self.vault_file_list.itemDoubleClicked.connect(self.on_vault_file_open); expl_card_l.addWidget(self.vault_file_list, 1)
        expl_l.addWidget(expl_card, 1)
        self.left_substack.addWidget(expl_group)

        # Sub-pagina 2: Eventos
        evt_group = QWidget(self.left_substack); evt_l = QVBoxLayout(evt_group); evt_l.setContentsMargins(0,6,0,0); evt_l.setSpacing(8)
        evt_card = QFrame(evt_group); evt_card.setObjectName("EvtCard"); evt_card.setStyleSheet("QFrame#EvtCard { background:%s; border:1px solid %s; border-radius:8px; }" % (THEME["bg_surface"], THEME["border"]))
        evt_card_l = QVBoxLayout(evt_card); evt_card_l.setContentsMargins(8,8,8,8); evt_card_l.setSpacing(8)
        evt_card_l.addWidget(QLabel("📅 Eventos del mes", evt_card))
        self.event_list = QListWidget(evt_card); self.event_list.itemDoubleClicked.connect(self.on_edit_event); evt_card_l.addWidget(self.event_list, 1)
        ev_btns = QHBoxLayout()
        b_ne = QPushButton("Nuevo", evt_card); b_ne.clicked.connect(self.new_event); ev_btns.addWidget(b_ne)
        b_de = QPushButton("Borrar", evt_card); b_de.clicked.connect(self.delete_event); ev_btns.addWidget(b_de)
        b_ln = QPushButton("Vincular", evt_card); b_ln.clicked.connect(self.link_event_note); ev_btns.addWidget(b_ln)
        evt_card_l.addLayout(ev_btns)
        evt_l.addWidget(evt_card, 1)
        self.left_substack.addWidget(evt_group)

        # Conexión botones → stacked
        self.btn_sub_notas.clicked.connect(lambda: self.left_substack.setCurrentIndex(0))
        self.btn_sub_expl.clicked.connect(lambda: self.left_substack.setCurrentIndex(1))
        self.btn_sub_evt.clicked.connect(lambda: self.left_substack.setCurrentIndex(2))
        self.left_substack.setCurrentIndex(0)
        # Compat alias
        self.left_splitter = self.left_substack
        self.left_tabs = self.left_substack
        right = QWidget(page_notas); right.setObjectName("RightEditor"); right.setMinimumWidth(540)
        right_layout = QVBoxLayout(right); right_layout.setContentsMargins(20,18,20,18); right_layout.setSpacing(14)
        right.setStyleSheet("QWidget#RightEditor { background:%s; }" % THEME["bg_alt"])
        crumb_row = QHBoxLayout(); crumb_row.setSpacing(8)
        self.breadcrumb_label = QLabel("Vault / Sin proyecto", right); self.breadcrumb_label.setStyleSheet("color:%s; font-size:10px;" % THEME["muted"])
        crumb_row.addWidget(self.breadcrumb_label); crumb_row.addStretch()
        self.project_badge = QLabel("", right); self.project_badge.setStyleSheet("padding:4px 8px; border-radius:10px; font-size:10px; background:%s; color:white;" % THEME["accent"]); self.project_badge.setVisible(False)
        crumb_row.addWidget(self.project_badge)
        right_layout.addLayout(crumb_row)
        hdr = QHBoxLayout(); hdr.setSpacing(8)
        hdr.addWidget(QLabel("Título:", right))
        self.title_entry = QLineEdit(right); self.title_entry.setPlaceholderText("Título de la nota…"); self.title_entry.setMinimumHeight(36)
        hdr.addWidget(self.title_entry)
        self.title_entry.textChanged.connect(self.auto_tag_hint)
        right_layout.addLayout(hdr)
        proj_edit_row = QHBoxLayout(); proj_edit_row.addWidget(QLabel("Proyecto:", right))
        self.note_project_combo = QComboBox(right); self.note_project_combo.setPlaceholderText("Sin proyecto"); proj_edit_row.addWidget(self.note_project_combo)
        proj_edit_row.addStretch()
        right_layout.addLayout(proj_edit_row)
        tb = QHBoxLayout(); tb.setSpacing(4)
        self._fmt_buttons = []
        fmt_actions = [
            ("B", self.fmt_bold, "Negrita Ctrl+B → **texto**"),
            ("I", self.fmt_italic, "Cursiva Ctrl+I → *texto*"),
            ("S", self.fmt_strike, "Tachado → ~~texto~~"),
            ("H1", lambda: self.fmt_heading(1), "Encabezado 1"),
            ("H2", lambda: self.fmt_heading(2), "Encabezado 2"),
            ("H3", lambda: self.fmt_heading(3), "Encabezado 3"),
            ('"', self.fmt_quote, "Cita → > "),
            ("</>", self.fmt_code_block, "Bloque código"),
            ("`", self.fmt_inline_code, "Código inline"),
            ("•", self.fmt_bullet, "Lista viñetas"),
            ("1.", self.fmt_numbered, "Lista numerada"),
            ("☐", self.insert_task, "Tarea - [ ]"),
            ("✓", self.toggle_task_in_editor, "Toggle tarea"),
            ("🔗", self.insert_link, "[[enlace]]"),
            ("#", self.insert_tag, "#tag"),
            ("📷", self.fmt_image, "Imagen ![alt](url)"),
            ("—", self.fmt_hr, "Línea horizontal"),
            ("▦", self.fmt_table, "Tabla"),
            ("📅", self.fmt_due, "due: YYYY-MM-DD"),
            ("⚡", self.fmt_prio, "prio: alta/media/baja"),
        ]
        for label, cb, tip in fmt_actions:
            b = QPushButton(label, right); b.setFixedHeight(30); b.setMinimumWidth(28); b.setToolTip(tip); b.setStyleSheet("QPushButton { padding:2px 6px; font-size:10pt; border:1px solid %s; border-radius:6px; background:%s; } QPushButton:hover { background:%s; }" % (THEME["border"], THEME["bg_surface"], THEME["accent_light"]))
            b.clicked.connect(cb); tb.addWidget(b); self._fmt_buttons.append(b)
        tb.addStretch()
        tb_container = QWidget(right); tb_container.setLayout(tb)
        right_layout.addWidget(tb_container)
        mode_row = QHBoxLayout(); mode_row.setSpacing(6)
        mode_row.addWidget(QLabel("Modo:", right))
        self.btn_mode_source = QPushButton("📝 Editar", right); self.btn_mode_source.setCheckable(True); self.btn_mode_source.setChecked(True); self.btn_mode_source.clicked.connect(lambda: self.set_editor_mode(EDITOR_MODE_SOURCE))
        self.btn_mode_preview = QPushButton("👁 Preview", right); self.btn_mode_preview.setCheckable(True); self.btn_mode_preview.clicked.connect(lambda: self.set_editor_mode(EDITOR_MODE_PREVIEW))
        self.btn_mode_split = QPushButton("◑ Dividido", right); self.btn_mode_split.setCheckable(True); self.btn_mode_split.setChecked(False); self.btn_mode_split.clicked.connect(lambda: self.set_editor_mode(EDITOR_MODE_SPLIT))
        self.btn_preview = self.btn_mode_preview
        mode_group = QButtonGroup(right); mode_group.setExclusive(True); mode_group.addButton(self.btn_mode_source,0); mode_group.addButton(self.btn_mode_preview,1); mode_group.addButton(self.btn_mode_split,2); self.mode_group = mode_group
        mode_row.addWidget(self.btn_mode_source); mode_row.addWidget(self.btn_mode_preview); mode_row.addWidget(self.btn_mode_split)
        mode_row.addStretch()
        b_exp = QPushButton("Export .md", right); b_exp.setFixedHeight(28); b_exp.clicked.connect(self.export_markdown); mode_row.addWidget(b_exp)
        right_layout.addLayout(mode_row)
        self.editor_split = QSplitter(Qt.Vertical, right)
        self.editor_split.setHandleWidth(6)
        self.text_edit = QTextEdit(right); self.text_edit.setPlaceholderText("Escribe markdown, #tag, [[enlace]], - [ ] tarea…  (Ctrl+S guarda) — usa la barra superior para dar formato sin memorizar markdown"); self.text_edit.textChanged.connect(self.on_editor_changed)
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        doc_font = QFont("Sans", 11); doc_font.setStyleHint(QFont.SansSerif); self.text_edit.setFont(doc_font)
        self.editor_split.addWidget(self.text_edit)
        self.preview_browser = QTextBrowser(right); self.preview_browser.setOpenExternalLinks(True)
        self.preview_browser.setStyleSheet("QTextBrowser { background:%s; padding:16px; border:1px solid %s; border-radius:%dpx; }" % (THEME["bg_surface"], THEME["border"], THEME["radius"]))
        self.editor_split.addWidget(self.preview_browser)
        self.editor_split.setSizes([420, 260])
        right_layout.addWidget(self.editor_split, 1)
        self.highlighter = SearchHighlighter(self.text_edit.document())
        self.md_highlighter = MarkdownHighlighter(self.text_edit.document())
        self.notas_splitter.addWidget(left_panel)
        self.notas_splitter.addWidget(right)
        self.notas_splitter.setSizes([440, 760])
        self.notas_splitter.setStretchFactor(0, 0); self.notas_splitter.setStretchFactor(1, 1)
        self.right_panel = right
        self.stacked.addWidget(page_notas)

        # Page 1: Calendario — pantalla completa
        page_cal = QWidget(self); page_cal.setObjectName("PageCal")
        page_cal.setStyleSheet("QWidget#PageCal { background: %s; }" % THEME["bg_app"])
        pc_l = QVBoxLayout(page_cal); pc_l.setContentsMargins(18,18,18,18); pc_l.setSpacing(16)
        cal_card = QFrame(page_cal); cal_card.setObjectName("CalCard"); cal_card.setStyleSheet("QFrame#CalCard { background:%s; border:1px solid %s; border-radius:%dpx; }" % (THEME["bg_surface"], THEME["border"], THEME["radius"]))
        cal_card_l = QVBoxLayout(cal_card); cal_card_l.setContentsMargins(18,16,18,16); cal_card_l.setSpacing(14)
        cal_head = QHBoxLayout()
        self.cal_label = QLabel("", cal_card); self.cal_label.setStyleSheet("font-weight:bold; font-size:16px; color:%s;" % THEME["text"])
        cal_head.addWidget(self.cal_label); cal_head.addStretch()
        btn_today = QPushButton("Hoy", cal_card); btn_today.setMinimumHeight(32); btn_today.clicked.connect(self.go_today); cal_head.addWidget(btn_today)
        btn_prev = QPushButton("◀", cal_card); btn_prev.setFixedWidth(38); btn_prev.setFixedHeight(32); btn_prev.clicked.connect(lambda: self.shift_month(-1)); cal_head.addWidget(btn_prev)
        btn_next = QPushButton("▶", cal_card); btn_next.setFixedWidth(38); btn_next.setFixedHeight(32); btn_next.clicked.connect(lambda: self.shift_month(1)); cal_head.addWidget(btn_next)
        cal_card_l.addLayout(cal_head)
        toggle_cal = QHBoxLayout()
        self.btn_view_month = QPushButton("📅 Mes", cal_card); self.btn_view_month.setCheckable(True); self.btn_view_month.setChecked(True); self.btn_view_month.setMinimumHeight(32); self.btn_view_month.clicked.connect(lambda: self.switch_cal_view(0))
        self.btn_view_week = QPushButton("🗓️ Semana", cal_card); self.btn_view_week.setCheckable(True); self.btn_view_week.setMinimumHeight(32); self.btn_view_week.clicked.connect(lambda: self.switch_cal_view(1))
        grp_cal = QButtonGroup(self); grp_cal.addButton(self.btn_view_month,0); grp_cal.addButton(self.btn_view_week,1); grp_cal.setExclusive(True)
        toggle_cal.addWidget(self.btn_view_month); toggle_cal.addWidget(self.btn_view_week); toggle_cal.addStretch()
        cal_card_l.addLayout(toggle_cal)
        self.cal_stack = QStackedWidget(cal_card)
        mes_w = QWidget(cal_card); mes_l = QVBoxLayout(mes_w); mes_l.setContentsMargins(0,0,0,0); mes_l.setSpacing(12)
        self.calendar = CalendarWidget(mes_w)
        self.calendar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mes_l.addWidget(self.calendar, 1)
        mes_l.addWidget(QLabel("Leyenda: • verde = evento  • azul = hoy  • click día selecciona", mes_w))
        self.cal_stack.addWidget(mes_w)
        semana_w = QWidget(cal_card); sw_l = QVBoxLayout(semana_w); sw_l.setContentsMargins(0,0,0,0); sw_l.setSpacing(12)
        self.week_table = QTableWidget(24, 7, semana_w)
        self.week_table.setHorizontalHeaderLabels(["Lu","Ma","Mi","Ju","Vi","Sá","Do"])
        self.week_table.verticalHeader().setDefaultSectionSize(28)
        self.week_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.week_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.week_table.setSelectionMode(QTableWidget.NoSelection)
        self.week_table.cellDoubleClicked.connect(self.on_week_cell)
        sw_l.addWidget(QLabel("Semana - doble click crea evento 10:00", semana_w))
        sw_l.addWidget(self.week_table, 1)
        self.cal_stack.addWidget(semana_w)
        cal_card_l.addWidget(self.cal_stack, 1)
        pc_l.addWidget(cal_card, 1)
        pc_l.addWidget(QLabel("Eventos del mes (abajo) - doble click detalle", page_cal))
        self.event_list_cal = QListWidget(page_cal); self.event_list_cal.setMaximumHeight(130); self.event_list_cal.itemDoubleClicked.connect(self.on_edit_event); pc_l.addWidget(self.event_list_cal)
        self._event_list_notes = self.event_list
        self._event_list_cal = self.event_list_cal
        pc_ev_btns = QHBoxLayout(); pc_ev_btns.setSpacing(10)
        b_ne2 = QPushButton("Nuevo evento", page_cal); b_ne2.setMinimumHeight(34); b_ne2.clicked.connect(self.new_event); pc_ev_btns.addWidget(b_ne2)
        b_de2 = QPushButton("Borrar", page_cal); b_de2.setMinimumHeight(34); b_de2.clicked.connect(self.delete_event_cal); pc_ev_btns.addWidget(b_de2)
        b_ln2 = QPushButton("Vincular nota", page_cal); b_ln2.setMinimumHeight(34); b_ln2.clicked.connect(self.link_event_note); pc_ev_btns.addWidget(b_ln2)
        pc_l.addLayout(pc_ev_btns)
        self.stacked.addWidget(page_cal)

        # Page 2: Tareas — pantalla completa
        page_tasks = QWidget(self); page_tasks.setObjectName("PageTasks")
        page_tasks.setStyleSheet("QWidget#PageTasks { background: %s; }" % THEME["bg_app"])
        pt_l = QVBoxLayout(page_tasks); pt_l.setContentsMargins(18,18,18,18); pt_l.setSpacing(16)
        tasks_card = QFrame(page_tasks); tasks_card.setObjectName("TasksCard"); tasks_card.setStyleSheet("QFrame#TasksCard { background:%s; border:1px solid %s; border-radius:%dpx; }" % (THEME["bg_surface"], THEME["border"], THEME["radius"]))
        tasks_card_l = QVBoxLayout(tasks_card); tasks_card_l.setContentsMargins(18,16,18,16); tasks_card_l.setSpacing(14)
        tasks_card_l.addWidget(QLabel("Tareas globales — doble click completa  • due:YYYY-MM-DD prio:alta/media/baja", tasks_card))
        filt = QHBoxLayout()
        filt.addWidget(QLabel("Filtrar prio:", tasks_card))
        self.task_filter = QComboBox(tasks_card); self.task_filter.addItems(["Todas","alta","media","baja"]); self.task_filter.setMinimumHeight(32); self.task_filter.currentTextChanged.connect(self.refresh_tasks)
        filt.addWidget(self.task_filter)
        filt.addStretch()
        btn_upd = QPushButton("Actualizar", tasks_card); btn_upd.setMinimumHeight(32); btn_upd.clicked.connect(self.refresh_tasks); filt.addWidget(btn_upd)
        tasks_card_l.addLayout(filt)
        self.task_list = QListWidget(tasks_card); self.task_list.itemDoubleClicked.connect(self.on_toggle_task_global)
        self.task_list.setAlternatingRowColors(True)
        tasks_card_l.addWidget(self.task_list, 1)
        tasks_card_l.addWidget(QLabel("Sintaxis: - [ ] texto due:2026-08-24 prio:alta", tasks_card))
        pt_l.addWidget(tasks_card, 1)
        self.stacked.addWidget(page_tasks)

        # Page 3: Grafo — pantalla completa
        page_graph = QWidget(self); page_graph.setObjectName("PageGraph")
        page_graph.setStyleSheet("QWidget#PageGraph { background: %s; }" % THEME["bg_app"])
        pg_l = QVBoxLayout(page_graph); pg_l.setContentsMargins(18,18,18,18); pg_l.setSpacing(16)
        graph_card = QFrame(page_graph); graph_card.setObjectName("GraphCard"); graph_card.setStyleSheet("QFrame#GraphCard { background:%s; border:1px solid %s; border-radius:%dpx; }" % (THEME["bg_surface"], THEME["border"], THEME["radius"]))
        graph_card_l = QVBoxLayout(graph_card); graph_card_l.setContentsMargins(18,16,18,16); graph_card_l.setSpacing(14)
        graph_card_l.addWidget(QLabel("🕸️ Grafo Knowledge OS — arrastra nodos, click navega", graph_card))
        filt_g = QHBoxLayout()
        filt_g.addWidget(QLabel("Filtrar tag:", graph_card))
        self.graph_filter = QLineEdit(graph_card); self.graph_filter.setPlaceholderText("ej: trabajo, deja vacío para todos"); self.graph_filter.setMaximumWidth(260); self.graph_filter.setMinimumHeight(32)
        filt_g.addWidget(self.graph_filter)
        btn_gf = QPushButton("Filtrar", graph_card); btn_gf.setMinimumHeight(32); btn_gf.clicked.connect(self.refresh_graph_page); filt_g.addWidget(btn_gf)
        btn_gr = QPushButton("Actualizar", graph_card); btn_gr.setMinimumHeight(32); btn_gr.clicked.connect(self.refresh_graph_page); filt_g.addWidget(btn_gr)
        btn_go = QPushButton("Ventana grande", graph_card); btn_go.setMinimumHeight(32); btn_go.clicked.connect(self.show_graph); filt_g.addWidget(btn_go)
        filt_g.addStretch()
        graph_card_l.addLayout(filt_g)
        self.graph_container = QVBoxLayout()
        self.graph_placeholder = QLabel("Cargando grafo…", graph_card, alignment=Qt.AlignCenter)
        self.graph_placeholder.setStyleSheet("color:#888; padding:20px;")
        graph_card_l.addWidget(self.graph_placeholder)
        graph_card_l.addLayout(self.graph_container, 1)
        pg_l.addWidget(graph_card, 1)
        self.stacked.addWidget(page_graph)

        for seq, cb in [("Ctrl+S", self.save_note), ("Ctrl+N", self.new_note), ("Ctrl+P", self.open_pomodoro), ("F11", self.toggle_zen), ("F9", self.toggle_preview), ("Ctrl+B", self.fmt_bold), ("Ctrl+I", self.fmt_italic), ("Ctrl+K", self.insert_link)]:
            act = QAction(self); act.setShortcut(QKeySequence(seq)); act.triggered.connect(cb if seq!="F9" else lambda: self.btn_preview.setChecked(not self.btn_preview.isChecked())); self.addAction(act)
        act_toggle = QAction(self); act_toggle.setShortcut(QKeySequence("Ctrl+Return")); act_toggle.triggered.connect(self.toggle_task_in_editor); self.addAction(act_toggle)
        act_esc = QAction(self); act_esc.setShortcut(QKeySequence("Escape")); act_esc.triggered.connect(lambda: self.search_entry.clear() if self.stacked.currentIndex()==0 else None); self.addAction(act_esc)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Listo. Usa #tag y [[enlace]] • Ctrl+B negrita • Ctrl+S guardar • F9 preview • F11 enfoque")
        self._apply_theme()
        self.set_editor_mode(EDITOR_MODE_SPLIT)


    def set_editor_mode(self, mode):
        self.editor_mode = mode
        for btn, m in [(self.btn_mode_source, EDITOR_MODE_SOURCE),(self.btn_mode_preview, EDITOR_MODE_PREVIEW),(self.btn_mode_split, EDITOR_MODE_SPLIT)]:
            btn.setChecked(mode==m)
        if mode == EDITOR_MODE_SOURCE:
            self.text_edit.setVisible(True); self.preview_browser.setVisible(False)
            self.editor_split.setSizes([600,0])
        elif mode == EDITOR_MODE_PREVIEW:
            self.text_edit.setVisible(False); self.preview_browser.setVisible(True)
            self.update_preview()
        else:
            self.text_edit.setVisible(True); self.preview_browser.setVisible(True)
            self.editor_split.setSizes([380,260]); self.update_preview()
        try:
            s=QSettings("gnote-calendar","gnote-qt"); s.setValue("editorMode", int(mode))
        except: pass

    def toggle_preview(self, checked=None):
        if checked is None:
            checked = self.btn_preview.isChecked()
        else:
            self.btn_preview.setChecked(checked)
        if checked:
            self.set_editor_mode(EDITOR_MODE_PREVIEW)
            self.statusBar().showMessage("Vista previa markdown activa (F9 para editar)", 3000)
        else:
            self.set_editor_mode(EDITOR_MODE_SOURCE)
            self.statusBar().showMessage("Modo edición", 2000)

    def toggle_zen(self):
        if self._zen:
            self._zen=False
            self.sidebar.setVisible(True)
            if hasattr(self,'notas_splitter') and self.stacked.currentIndex()==0 and self._prev_splitter_sizes:
                try: self.notas_splitter.setSizes(self._prev_splitter_sizes)
                except: pass
            self.statusBar().showMessage("Zen desactivado",2000)
        else:
            self._zen=True
            if hasattr(self,'notas_splitter') and self.stacked.currentIndex()==0:
                try: self._prev_splitter_sizes=self.notas_splitter.sizes()
                except: self._prev_splitter_sizes=None
            else:
                self._prev_splitter_sizes=None
            self.sidebar.setVisible(False)
            self.statusBar().showMessage("Modo enfoque — F11 para salir",3000)

    def _wrap_selection(self, prefix, suffix, placeholder="texto"):
        cursor=self.text_edit.textCursor()
        if cursor.hasSelection():
            sel=cursor.selectedText()
            cursor.insertText(f"{prefix}{sel}{suffix}")
        else:
            cursor.insertText(f"{prefix}{placeholder}{suffix}")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(suffix)+len(placeholder)//2)
            self.text_edit.setTextCursor(cursor)
        self.text_edit.setFocus()

    def _prefix_lines(self, prefix):
        cursor=self.text_edit.textCursor()
        if cursor.hasSelection():
            start=cursor.selectionStart(); end=cursor.selectionEnd()
            cursor.setPosition(start); cursor.movePosition(QTextCursor.StartOfLine)
            while cursor.position() < end:
                cursor.insertText(prefix)
                if not cursor.movePosition(QTextCursor.Down): break
                end+=len(prefix)
        else:
            cursor.movePosition(QTextCursor.StartOfLine); cursor.insertText(prefix)
        self.text_edit.setFocus()

    def fmt_bold(self): self._wrap_selection("**","**","texto en negrita")
    def fmt_italic(self): self._wrap_selection("*","*","texto en cursiva")
    def fmt_strike(self): self._wrap_selection("~~","~~","tachado")
    def fmt_heading(self, level):
        prefix="# "*level
        cursor=self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine); cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        line=cursor.selectedText()
        stripped=re.sub(r"^#{1,6}\s*","",line)
        cursor.insertText(f"{prefix}{stripped}")
        self.text_edit.setFocus()
    def fmt_quote(self): self._prefix_lines("> ")
    def fmt_code_block(self): 
        cursor=self.text_edit.textCursor()
        if cursor.hasSelection():
            sel=cursor.selectedText().replace('\u2029','\n')
            cursor.insertText(f"```\n{sel}\n```")
        else:
            self._wrap_selection("```\n"," \n```","código")
    def fmt_inline_code(self): self._wrap_selection("`","`","código")
    def fmt_bullet(self): self._prefix_lines("- ")
    def fmt_numbered(self): self._prefix_lines("1. ")
    def fmt_image(self):
        url, ok = QInputDialog.getText(self, "Imagen", "URL o ruta de imagen:")
        if ok and url: self.text_edit.insertPlainText(f"![alt]({url})")
    def fmt_hr(self): self.text_edit.insertPlainText("\n---\n")
    def fmt_table(self): self.text_edit.insertPlainText("\n| Col1 | Col2 |\n|------|------|\n|      |      |\n")
    def fmt_due(self):
        d, ok = QInputDialog.getText(self, "Vencimiento", "due: YYYY-MM-DD", text=date.today().isoformat())
        if ok and d: self.text_edit.insertPlainText(f" due:{d}")
    def fmt_prio(self):
        prio, ok = QInputDialog.getItem(self, "Prioridad", "prio:", ["alta","media","baja"], 0, False)
        if ok: self.text_edit.insertPlainText(f" prio:{prio}")

    def on_editor_changed(self):
        self.auto_tag_hint()
        if hasattr(self, 'preview_browser') and self.preview_browser.isVisible():
            self.update_preview()

    def update_preview(self):
        body = self.text_edit.toPlainText()
        title = self.title_entry.text()
        if HAS_MARKDOWN and md_lib:
            try:
                html = md_lib.markdown(f"# {title}\n\n{body}", extensions=['extra', 'codehilite', 'toc', 'tables', 'sane_lists'])
                html = re.sub(r"#(\w+)", r"<span style='color:#1e88e5; font-weight:600;'>#\1</span>", html)
                html = re.sub(r"\[\[([^\]]+)\]\]", r"<span style='color:#2e7d32; font-weight:600;'>[[\1]]</span>", html)
                self.preview_browser.setHtml(html)
                return
            except: pass
        esc = body.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        esc = re.sub(r"#(\w+)", r"<b style='color:#1e88e5;'>#\1</b>", esc)
        esc = re.sub(r"\[\[([^\]]+)\]\]", r"<b style='color:#2e7d32;'>[[\1]]</b>", esc)
        esc = esc.replace("\n","<br>")
        self.preview_browser.setHtml(f"<h2>{title}</h2><div style='line-height:1.7; font-size:11pt;'>{esc}</div>")

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def switch_section(self, idx):
        self.stacked.setCurrentIndex(idx)
        self._current_section = idx
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == idx)
        if idx == 0:
            self.statusBar().showMessage("Sección Notas • vault + proyectos • F11 enfoque", 3000)
        elif idx == 1:
            self.statusBar().showMessage("Sección Calendario • Mes/Semana • doble click crea evento", 3000)
            self.refresh_calendar()
            if hasattr(self, 'week_table'):
                self.refresh_week()
        elif idx == 2:
            self.statusBar().showMessage("Sección Tareas • due/prio • doble click completa", 3000)
            self.refresh_tasks()
        elif idx == 3:
            self.statusBar().showMessage("Sección Grafo • arrastra nodos, click navega", 3000)
            self.refresh_graph_page()

    def switch_cal_view(self, idx):
        self.cal_stack.setCurrentIndex(idx)
        self.btn_view_month.setChecked(idx==0)
        self.btn_view_week.setChecked(idx==1)
        if idx==1:
            self.refresh_week()

    def refresh_week(self):
        if not hasattr(self, 'week_table'):
            return
        dt = self.selected_date
        wd = dt.weekday()
        mon = dt - timedelta(days=wd)
        for r in range(24):
            for c in range(7):
                self.week_table.setItem(r,c, QTableWidgetItem(""))
        con=db(); cur=con.cursor()
        for col in range(7):
            day = mon + timedelta(days=col)
            start = int(day.replace(hour=0,minute=0,second=0).timestamp())
            end = int(day.replace(hour=23,minute=59,second=59).timestamp())
            cur.execute("SELECT title, start_ts FROM events WHERE start_ts>=? AND start_ts<=? ORDER BY start_ts", (start,end))
            for r in cur.fetchall():
                h = datetime.fromtimestamp(r["start_ts"]).hour
                item = self.week_table.item(h, col)
                txt = (item.text() + "\n" if item and item.text() else "") + r["title"][:14]
                self.week_table.setItem(h, col, QTableWidgetItem(txt))
                it = self.week_table.item(h,col)
                it.setBackground(QColor("#e3f2fd"))
        con.close()
        for c in range(7):
            d = mon + timedelta(days=c)
            self.week_table.horizontalHeaderItem(c).setText(d.strftime("%a %d"))

    def on_week_cell(self, row, col):
        dt = self.selected_date
        wd = dt.weekday()
        mon = dt - timedelta(days=wd)
        day = mon + timedelta(days=col)
        hora = f"{row:02d}:00"
        ok = QMessageBox.question(self, "Nuevo evento", f"¿Crear evento el {day.strftime('%Y-%m-%d')} a las {hora}?")
        if ok != QMessageBox.Yes:
            return
        title, ok2 = QInputDialog.getText(self, "Título", "Título del evento:")
        if not ok2 or not title:
            return
        start = int(day.replace(hour=row, minute=0, second=0).timestamp())
        end = start + 3600
        con=db(); cur=con.cursor(); uid=f"{int(time.time())}-{start}@gnote.local"
        cur.execute("INSERT INTO events(title,description,location,start_ts,end_ts,uid,source,created_at,note_id) VALUES(?,?,?,?,?,?,?,?,?)",
                    (title, "", "", start, end, uid, "local", int(time.time()), self.current_note_id or None))
        con.commit(); con.close()
        self.refresh_calendar(); self.refresh_week(); self.refresh_events()

    def refresh_graph_page(self):
        if not hasattr(self, 'graph_placeholder'):
            return
        filt = self.graph_filter.text().strip().lower() if hasattr(self, 'graph_filter') else ""
        while self.graph_container.count():
            item=self.graph_container.takeAt(0)
            w=item.widget()
            if w: w.deleteLater()
        self.graph_placeholder.setVisible(False)
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body FROM notes"); rows=cur.fetchall()
        if filt:
            rows=[r for r in rows if filt in r["title"].lower() or filt in r["body"].lower() or f"#{filt}" in r["body"].lower()]
        cur.execute("SELECT src_id, dst_title FROM backlinks"); links_raw=cur.fetchall()
        con.close()
        if not rows:
            lab=QLabel("Sin notas para el filtro.\nUsa [[enlace]] y #tag", self, alignment=Qt.AlignCenter); lab.setStyleSheet("color:#888; padding:20px;")
            self.graph_container.addWidget(lab)
            return
        title_to_id={r["title"].strip().lower(): r["id"] for r in rows}
        id_to_title={r["id"]: r["title"][:18] for r in rows}
        import math, random
        N=len(rows)
        nodes=[]
        for i,r in enumerate(rows):
            ang=2*math.pi*i/max(1,N)
            nodes.append({"id":r["id"], "title":id_to_title[r["id"]], "x":360+150*math.cos(ang)+random.uniform(-10,10), "y":260+150*math.sin(ang)+random.uniform(-10,10), "vx":0, "vy":0})
        id_to_idx={n["id"]:i for i,n in enumerate(nodes)}
        edges=[]
        for src,dst_title in links_raw:
            did=title_to_id.get(dst_title.strip().lower())
            if did and src in id_to_idx and did in id_to_idx:
                edges.append((id_to_idx[src], id_to_idx[did]))
        def on_nav(nid):
            self.switch_section(0)
            for i in range(self.notes_list.count()):
                if self.notes_list.item(i).data(Qt.UserRole)==nid:
                    self.notes_list.setCurrentRow(i)
                    self.on_select_note(self.notes_list.item(i))
                    break
        view=GraphView(nodes, edges, self.current_note_id, on_nav, self)
        view.setMinimumHeight(420)
        self.graph_container.addWidget(view)
        hint=QLabel(f"Grafo filtrado: {len(nodes)} nodos, {len(edges)} enlaces — filtro '{filt}'" if filt else f"Grafo: {len(nodes)} nodos, {len(edges)} enlaces", self); hint.setStyleSheet("color:#666; font-size:11px;")
        self.graph_container.addWidget(hint)

    def _apply_theme(self):
        try:
            bg = self.palette().color(self.palette().Window).lightness()
        except:
            try: bg = self.palette().color(QPalette.Window).lightness()
            except: bg = 255
        is_dark = bg < 128
        if is_dark:
            editor_bg = "#1e1e1e"; editor_fg = "#e0e0e0"; surface="#252525"; border="#3a3a3a"; card_bg="#1e1e1e"
        else:
            editor_bg = "#fffef8"; editor_fg = "#1a1a1a"; surface=THEME["bg_surface"]; border=THEME["border"]; card_bg=THEME["bg_surface"]
        self.setStyleSheet(f"""
            QMainWindow {{ background:{THEME["bg_app"]}; font-size: 11pt; }}
            QLabel {{ padding: 4px 6px; font-size: 10.5pt; color:{THEME["text"]}; }}
            QLineEdit {{ padding: 8px 12px; font-size: 11pt; border: 1px solid {border}; border-radius: 9px; background:{surface}; }}
            QLineEdit:focus {{ border: 1.6px solid {THEME["accent"]}; }}
            QPushButton {{ padding: 7px 12px; font-size: 10.5pt; border-radius: 8px; margin: 2px; background:{surface}; border:1px solid {border}; }}
            QPushButton:hover {{ background: {THEME["accent_light"]}; border-color:{THEME["accent"]}; }}
            QListWidget {{ font-size: 10.8pt; border: 1px solid {border}; border-radius: 10px; padding: 6px; background:{surface}; }}
            QListWidget::item {{ padding: 11px 14px; margin: 4px 4px; border-radius: 8px; line-height: 1.5; border-left:3px solid transparent; }}
            QListWidget::item:selected {{ background: {THEME["accent_light"]}; color: #0d47a1; border-left:3px solid {THEME["accent"]}; }}
            QListWidget::item:alternate {{ background: #f6f8fa; }}
            QComboBox {{ padding:6px 10px; border:1px solid {border}; border-radius:8px; background:{surface}; }}
            QFrame#Sidebar {{ background:#f8f9fb; border-right:1px solid {border}; }}
            QToolButton {{ border:none; padding:6px; font-size:9.5pt; border-radius:9px; }}
            QToolButton:checked {{ background:{THEME["accent_light"]}; border:1px solid #c2d8f0; }}
            QToolButton:hover {{ background:#eef2ff; }}
            QCalendarWidget QToolButton {{ padding: 8px; margin: 2px; }}
            QCalendarWidget QWidget {{ alternate-background-color: #f6f8fa; }}
            QTextEdit {{ background: {editor_bg}; color: {editor_fg}; padding: 16px; font-size: 11pt; line-height: 1.65; border: 1px solid {border}; border-radius: 10px; }}
            QTextBrowser {{ padding: 14px; font-size: 11pt; background:{card_bg}; border:1px solid {border}; border-radius:10px; }}
            QToolBar {{ spacing: 8px; padding: 6px; background:{surface}; border-bottom:1px solid {border}; }}
            QTableWidget {{ gridline-color: {border}; selection-background-color: {THEME["accent_light"]}; border:1px solid {border}; border-radius:8px; }}
            QTableWidget::item {{ padding: 6px; }}
            QHeaderView::section {{ padding: 7px 8px; background: #f6f8fa; border: none; border-bottom: 1px solid {border}; font-weight:600; }}
            QSplitter::handle {{ background:{border}; }}
            QSplitter::handle:horizontal {{ width:6px; }}
            QSplitter::handle:vertical {{ height:6px; }}
        """)
        self.text_edit.setStyleSheet(self.text_edit.styleSheet() + f"QTextEdit {{ background:{editor_bg}; color:{editor_fg}; padding:16px; }}")
        self.preview_browser.setStyleSheet(f"QTextBrowser {{ background:{card_bg}; padding:14px; border:1px solid {border}; border-radius:10px; }}")
        if hasattr(self, 'sidebar'):
            self.sidebar.setStyleSheet(f"QFrame#Sidebar {{ background:{'#1e1e1e' if is_dark else '#f8f9fb'}; border-right:1px solid {border}; }} QToolButton {{ border:none; padding:6px; }} QToolButton:checked {{ background:{THEME['accent_light']}; border-radius:9px; }}")


    def _load_settings(self):
        s = QSettings("gnote-calendar", "gnote-qt")
        geom = s.value("geometry")
        if geom: self.restoreGeometry(geom)
        state = s.value("windowState")
        if state: self.restoreState(state)
        idx = s.value("section", 0)
        try: self.switch_section(int(idx))
        except: pass
        preview = s.value("preview", False)
        edmode = s.value("editorMode", EDITOR_MODE_SPLIT)
        try:
            edmode=int(edmode)
            self.set_editor_mode(edmode)
        except:
            if preview in (True, "true", 1, "1"): self.set_editor_mode(EDITOR_MODE_PREVIEW)

    def closeEvent(self, e):
        s = QSettings("gnote-calendar", "gnote-qt")
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())
        s.setValue("section", self._current_section)
        s.setValue("preview", self.btn_preview.isChecked() if hasattr(self, 'btn_preview') else False)
        s.setValue("editorMode", int(self.editor_mode))
        super().closeEvent(e)

    def _setup_tray(self):
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray = QSystemTrayIcon(self)
                try: self.tray.setIcon(QIcon.fromTheme("gnote-calendar"))
                except: pass
                if self.tray.icon().isNull():
                    from PySide6.QtGui import QPixmap
                    pm = QPixmap(16,16); pm.fill(QColor(THEME["accent"]))
                    self.tray.setIcon(QIcon(pm))
                menu = QMenu(self)
                for txt, cb in [("Mostrar", self.show), ("Nueva nota", self.new_note), ("Pomodoro", self.open_pomodoro), ("Salir", self.close)]:
                    a = QAction(txt, self); a.triggered.connect(cb); menu.addAction(a)
                self.tray.setContextMenu(menu)
                self.tray.setToolTip("gnote-calendar - Knowledge OS")
                self.tray.show()
                self.tray.activated.connect(lambda r: self.show() if r==QSystemTrayIcon.DoubleClick else None)
            else: self.tray = None
        except: self.tray = None

    def _setup_accessibility(self):
        try:
            self.search_entry.setAccessibleName("Buscar notas")
            self.search_entry.setAccessibleDescription("Filtra por tag:, fecha:hoy/semana, project:, texto. Esc para limpiar")
            self.title_entry.setAccessibleName("Título de la nota")
            self.text_edit.setAccessibleName("Editor de nota markdown")
            self.text_edit.setAccessibleDescription("Markdown, #tag, [[enlace]], - [ ] tarea. Ctrl+B negrita, Ctrl+S guarda")
            self.notes_list.setAccessibleName("Lista de notas")
            self.task_list.setAccessibleName("Lista de tareas")
            self.calendar.setAccessibleName("Calendario mensual")
            self.week_table.setAccessibleName("Vista semanal")
            act_hc = QAction("Alto contraste", self); act_hc.setCheckable(True)
            act_hc.setShortcut(QKeySequence("Ctrl+H"))
            act_hc.toggled.connect(self.toggle_high_contrast)
            self.addAction(act_hc)
            for m in self.menuBar().findChildren(QMenu):
                if m.title()=="&Ver":
                    m.addAction(act_hc); break
        except: pass

    def toggle_high_contrast(self, checked):
        if checked:
            self.setStyleSheet(self.styleSheet() + """
                QMainWindow { background: #000; color: #fff; }
                QListWidget::item:selected { background: #ffff00; color: #000; border: 2px solid #000; }
                QTextEdit { background: #000; color: #fff; border: 2px solid #fff; }
                QPushButton { background: #fff; color: #000; border: 2px solid #000; }
            """)
            self.statusBar().showMessage("Alto contraste activado (Ctrl+H)", 3000)
        else:
            self._apply_theme()
            self.statusBar().showMessage("Alto contraste desactivado", 2000)

    def notify_event(self, title, body):
        try:
            if hasattr(self, 'tray') and self.tray and self.tray.isVisible():
                self.tray.showMessage(title, body, QSystemTrayIcon.Information, 5000)
                return
        except: pass
        try: subprocess.run(["notify-send", title, body], timeout=1)
        except: pass

    def _setup_watcher(self):
        folder = get_sync_folder()
        if os.path.isdir(folder):
            self.watcher = QFileSystemWatcher([folder], self)
            self.watcher.directoryChanged.connect(lambda _: self._on_fs_changed())
            self.watcher.fileChanged.connect(lambda _: self._on_fs_changed())
        self._fs_timer = QTimer(self); self._fs_timer.timeout.connect(self.auto_folder_sync); self._fs_timer.start(5000)

    def _on_fs_changed(self):
        QTimer.singleShot(800, self._do_sync_and_refresh)

    def _do_sync_and_refresh(self):
        folder = get_sync_folder()
        if os.path.isdir(folder) and os.path.exists(BIN_PATH):
            try:
                r = subprocess.run([BIN_PATH, "sync", "--folder", folder], capture_output=True, text=True, timeout=4)
                if r.stdout and ("Importados" in r.stdout or "Exportados" in r.stdout):
                    if any(c.isdigit() and int(c)>0 for c in r.stdout if c.isdigit()):
                        self.refresh_notes(); self.refresh_tasks(); self.refresh_tag_cloud(); self.refresh_vault_explorer()
            except: pass

    def refresh_calendar(self):
        dt = self.selected_date
        self.cal_label.setText(f"{calendar.month_name[dt.month]} {dt.year}")
        self.calendar.setCurrentPage(dt.year, dt.month)
        self.calendar.setSelectedDate(QDate(dt.year, dt.month, dt.day))
        con = db(); cur = con.cursor()
        start = int(datetime(dt.year, dt.month, 1).timestamp())
        if dt.month==12: end = int(datetime(dt.year+1,1,1).timestamp())
        else: end = int(datetime(dt.year, dt.month+1,1).timestamp())
        cur.execute("SELECT start_ts FROM events WHERE start_ts>=? AND start_ts<?", (start,end))
        counts={}
        for r in cur.fetchall(): counts[datetime.fromtimestamp(r[0]).day] = counts.get(datetime.fromtimestamp(r[0]).day,0)+1
        con.close()
        self.calendar.setCounts(counts)
        self.refresh_events()

    def shift_month(self, delta):
        y=self.selected_date.year; m=self.selected_date.month+delta
        if m<1: m=12; y-=1
        if m>12: m=1; y+=1
        last = calendar.monthrange(y,m)[1]
        d=min(self.selected_date.day, last)
        self.selected_date = self.selected_date.replace(year=y, month=m, day=d)
        self.refresh_calendar()
    def go_today(self): self.selected_date=datetime.now(); self.refresh_calendar()

    def refresh_tag_cloud(self):
        while self.tag_cloud.count():
            item=self.tag_cloud.takeAt(0)
            w=item.widget()
            if w: w.deleteLater()
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
            b=QPushButton(f"#{t}", self); b.setFlat(True); b.setStyleSheet("color:%s; font-size:11px; padding:4px 8px; border:1px solid %s; border-radius:12px; background:%s;" % (THEME["accent"], THEME["border"], THEME["bg_surface"]))
            b.clicked.connect(lambda _, t=t: self.search_entry.setText(f"#{t}"))
            self.tag_cloud.addWidget(b)
        self.tag_cloud.addStretch()

    def refresh_projects(self):
        try: ensure_db()
        except: pass
        # toolbar + vault combos
        projects = get_projects()
        for combo in [self.project_filter_combo, self.project_combo_toolbar, self.assign_project_combo, self.note_project_combo]:
            if not hasattr(self, combo.objectName() if hasattr(combo,'objectName') else 'x'): pass
        # clear and fill
        for cb in [self.project_filter_combo, self.project_combo_toolbar, self.assign_project_combo, self.note_project_combo]:
            if not hasattr(self, '_checked_projects'): pass
            try: cb.blockSignals(True); cb.clear(); cb.addItem("Todos / Sin filtro", None); cb.addItem("Sin proyecto", -1)
            except: continue
        for cb in [self.project_filter_combo, self.project_combo_toolbar, self.assign_project_combo, self.note_project_combo]:
            try:
                for r in projects:
                    icon = r["icon"] if isinstance(r, sqlite3.Row) else r[2] if len(r)>2 else "📁"
                    title = r["title"] if isinstance(r, sqlite3.Row) else r[1]
                    pid = r["id"] if isinstance(r, sqlite3.Row) else r[0]
                    cb.addItem(f"{icon} {title}", pid)
                cb.blockSignals(False)
            except: 
                try: cb.blockSignals(False)
                except: pass
        # project list widget
        if hasattr(self, 'project_list'):
            self.project_list.clear()
            # add Sin proyecto pseudo
            item0 = QListWidgetItem("📂 Sin proyecto"); item0.setData(Qt.UserRole, -1); self.project_list.addItem(item0)
            for r in projects:
                pid = r["id"] if isinstance(r, sqlite3.Row) else r[0]
                title = r["title"] if isinstance(r, sqlite3.Row) else r[1]
                icon = r["icon"] if isinstance(r, sqlite3.Row) else r[2]
                color = r["color"] if isinstance(r, sqlite3.Row) else r[3]
                it = QListWidgetItem(f"{icon} {title}"); it.setData(Qt.UserRole, pid)
                it.setBackground(QColor(color)); it.setForeground(QColor("white"))
                self.project_list.addItem(it)
        self.refresh_vault_explorer()

    def refresh_vault_explorer(self):
        if not hasattr(self, 'vault_file_list'): return
        self.vault_file_list.clear()
        folder = get_sync_folder()
        if os.path.isdir(folder):
            try:
                for fname in sorted(os.listdir(folder)):
                    if fname.endswith(".md"):
                        self.vault_file_list.addItem(fname)
                self.vault_path_label.setText(folder)
            except: pass

    def open_vault_folder(self):
        folder = get_sync_folder()
        if os.path.isdir(folder):
            try: subprocess.run(["xdg-open", folder], timeout=2)
            except: QMessageBox.information(self, "Vault", f"Carpeta vault:\n{folder}")
        else: QMessageBox.information(self, "Vault", f"No existe:\n{folder}\nCrea con Folder Sync")

    def on_vault_file_open(self, item):
        fname = item.text()
        folder = get_sync_folder()
        path = os.path.join(folder, fname)
        try:
            txt = open(path, encoding="utf-8").read()
            # try parse frontmatter
            m = re.search(r"title:\s*[\"']?([^\"'\n]+)", txt)
            title = m.group(1).strip() if m else fname[:-3]
            self.title_entry.setText(title)
            body = re.sub(r"^---.*?---\s*", "", txt, flags=re.DOTALL)
            self.text_edit.setPlainText(body.strip())
            self.statusBar().showMessage(f"Archivo vault cargado: {fname}", 3000)
        except Exception as e: QMessageBox.warning(self, "Error", str(e))

    def on_project_filter_changed(self, idx):
        # Determine which combo triggered - use current_project_id
        combo = self.sender()
        if combo is None: combo = self.project_filter_combo if hasattr(self, 'project_filter_combo') else None
        if combo is None: return
        pid = combo.currentData()
        # sync other combos without recursion
        for cb in [self.project_filter_combo, self.project_combo_toolbar]:
            if cb != combo:
                cb.blockSignals(True)
                for i in range(cb.count()):
                    if cb.itemData(i)==pid:
                        cb.setCurrentIndex(i); break
                cb.blockSignals(False)
        self.current_project_id = pid if pid not in (None, -1) else (None if pid is None else -1)
        self.refresh_notes()

    def on_project_selected(self, item):
        pid = item.data(Qt.UserRole)
        # set filter combos to this project
        for cb in [self.project_filter_combo, self.project_combo_toolbar]:
            for i in range(cb.count()):
                if cb.itemData(i)==pid:
                    cb.blockSignals(True); cb.setCurrentIndex(i); cb.blockSignals(False); break
        self.current_project_id = pid
        self.refresh_notes()

    def new_project_dialog(self):
        title, ok = QInputDialog.getText(self, "Nuevo proyecto", "Nombre del proyecto:")
        if not ok or not title.strip(): return
        # duplicate check
        exists = [r for r in get_projects() if r["title"].lower()==title.strip().lower()]
        if exists:
            QMessageBox.warning(self, "Proyecto", "Ya existe un proyecto con ese nombre"); return
        icon, ok2 = QInputDialog.getText(self, "Icono", "Icono (emoji):", text="📁")
        if not ok2: icon="📁"
        color = PROJECT_COLORS[len(get_projects())%len(PROJECT_COLORS)]
        pid = create_project(title.strip(), icon.strip() or "📁", color, "")
        if pid:
            self.refresh_projects()
            self.statusBar().showMessage(f"Proyecto '{title}' creado", 3000)
        else: QMessageBox.warning(self, "Error", "No se pudo crear proyecto")

    def delete_project_dialog(self):
        if not hasattr(self, 'project_list') or self.project_list.currentRow()<0:
            QMessageBox.information(self, "Proyecto", "Selecciona un proyecto en la lista"); return
        item=self.project_list.currentItem(); pid=item.data(Qt.UserRole)
        if pid in (None, -1): QMessageBox.information(self, "Proyecto", "No se puede borrar 'Sin proyecto'"); return
        if QMessageBox.question(self, "Borrar proyecto", f"¿Borrar proyecto y dejar sus notas sin proyecto?") != QMessageBox.Yes: return
        try:
            con=db(); cur=con.cursor()
            cur.execute("UPDATE notes SET project_id=NULL WHERE project_id=?", (pid,))
            cur.execute("DELETE FROM projects WHERE id=?", (pid,))
            con.commit(); con.close()
            self.refresh_projects(); self.refresh_notes()
            self.statusBar().showMessage("Proyecto borrado", 2000)
        except Exception as e: QMessageBox.warning(self, "Error", str(e))

    def assign_selected_to_project(self):
        if not self.current_note_id:
            QMessageBox.information(self, "Asignar", "Selecciona una nota primero"); return
        pid = self.assign_project_combo.currentData() if hasattr(self, 'assign_project_combo') else None
        if pid==-1: pid=None
        try:
            con=db(); con.execute("UPDATE notes SET project_id=? WHERE id=?", (pid, self.current_note_id)); con.commit(); con.close()
            self.refresh_notes(); self.refresh_projects()
            self.statusBar().showMessage(f"Nota #{self.current_note_id} asignada", 2000)
        except Exception as e: QMessageBox.warning(self,"Error",str(e))

    def unassign_selected_project(self):
        if not self.current_note_id: return
        try:
            con=db(); con.execute("UPDATE notes SET project_id=NULL WHERE id=?", (self.current_note_id,)); con.commit(); con.close()
            self.refresh_projects(); self.refresh_notes()
        except: pass

    def refresh_notes(self):
        try: ensure_db()
        except: pass
        q=self.search_entry.text().strip() if hasattr(self,'search_entry') else ""
        tag=None; fecha=None; text_q=q; project_q=None
        m=re.search(r"tag:(\w+)", q)
        if m: tag=m.group(1); text_q=re.sub(r"tag:\w+", "", text_q).strip()
        mf=re.search(r"fecha:(\S+)", q)
        if mf: fecha=mf.group(1); text_q=re.sub(r"fecha:\S+", "", text_q).strip()
        mp=re.search(r"project:([^\s]+)", q)
        if mp:
            project_q=mp.group(1); text_q=re.sub(r"project:\S+", "", text_q).strip()
            text_q=re.sub(r"project:[\"'][^\"']+[\"']", "", q).strip()
        # project filter from combobox (if not in q)
        if not project_q:
            if self.current_project_id is not None:
                if self.current_project_id==-1: project_q="__none__"
                else:
                    # lookup title
                    for r in get_projects():
                        pid = r["id"] if isinstance(r, sqlite3.Row) else r[0]
                        if pid==self.current_project_id:
                            project_q = r["title"] if isinstance(r, sqlite3.Row) else r[1]
                            break
                    if project_q: pass
                    else: project_q=None
        con=db(); cur=con.cursor()
        # handle project filtering via DB
        base_query = "SELECT n.id,n.title,n.body,n.updated_at,n.project_id FROM notes n "
        params=[]
        where=[]
        if text_q and "#" in text_q:
            mf2=re.search(r"#(\w+)", text_q)
            if mf2 and not tag: tag=mf2.group(1)
        # try FTS if text_q
        rows=[]
        use_fts=False
        if q or text_q:
            try:
                if text_q:
                    # Need to detect project filter via SQL
                    if project_q and project_q!="__none__":
                        # get project id by title
                        cur.execute("SELECT id FROM projects WHERE title=? COLLATE NOCASE", (project_q,))
                        prow=cur.fetchone()
                        if prow:
                            pid=prow[0]
                            cur.execute("SELECT n.id,n.title,n.body,n.updated_at,n.project_id FROM notes n JOIN notes_fts f ON n.id=f.rowid WHERE notes_fts MATCH ? AND n.project_id=? ORDER BY n.updated_at DESC LIMIT 100", (text_q,pid))
                        else:
                            cur.execute("SELECT n.id,n.title,n.body,n.updated_at,n.project_id FROM notes n JOIN notes_fts f ON n.id=f.rowid WHERE notes_fts MATCH ? ORDER BY n.updated_at DESC LIMIT 100", (text_q,))
                    elif project_q=="__none__":
                        cur.execute("SELECT n.id,n.title,n.body,n.updated_at,n.project_id FROM notes n JOIN notes_fts f ON n.id=f.rowid WHERE notes_fts MATCH ? AND n.project_id IS NULL ORDER BY n.updated_at DESC LIMIT 100", (text_q,))
                    else:
                        cur.execute("SELECT n.id,n.title,n.body,n.updated_at,n.project_id FROM notes n JOIN notes_fts f ON n.id=f.rowid WHERE notes_fts MATCH ? ORDER BY n.updated_at DESC LIMIT 100", (text_q,))
                    rows=cur.fetchall()
                    if not rows: raise Exception("no fts")
                    use_fts=True
                else: rows=[]
            except:
                like=f"%{text_q}%"
                if text_q:
                    if project_q and project_q!="__none__" and project_q is not None:
                        cur.execute("SELECT id,title,body,updated_at,project_id FROM notes WHERE (title LIKE ? OR body LIKE ?) AND project_id=(SELECT id FROM projects WHERE title=? COLLATE NOCASE) ORDER BY updated_at DESC LIMIT 100", (like,like,project_q))
                    elif project_q=="__none__":
                        cur.execute("SELECT id,title,body,updated_at,project_id FROM notes WHERE (title LIKE ? OR body LIKE ?) AND project_id IS NULL ORDER BY updated_at DESC LIMIT 100", (like,like))
                    else:
                        cur.execute("SELECT id,title,body,updated_at,project_id FROM notes WHERE title LIKE ? OR body LIKE ? ORDER BY updated_at DESC LIMIT 100", (like,like))
                else:
                    if project_q and project_q!="__none__" and project_q is not None:
                        cur.execute("SELECT id,title,body,updated_at,project_id FROM notes WHERE project_id=(SELECT id FROM projects WHERE title=? COLLATE NOCASE) ORDER BY updated_at DESC LIMIT 100", (project_q,))
                    elif project_q=="__none__":
                        cur.execute("SELECT id,title,body,updated_at,project_id FROM notes WHERE project_id IS NULL ORDER BY updated_at DESC LIMIT 100")
                    else: cur.execute("SELECT id,title,body,updated_at,project_id FROM notes ORDER BY updated_at DESC LIMIT 100")
                rows=cur.fetchall()
            if tag: rows=[r for r in rows if f"#{tag}" in (r["title"]+" "+r["body"])]
            if fecha:
                target=None; is_week=False
                if fecha=="hoy": target=date.today()
                elif fecha=="ayer": target=date.today()-timedelta(days=1)
                elif fecha=="semana": is_week=True
                else:
                    try: target=datetime.strptime(fecha, "%Y-%m-%d").date()
                    except: target=None
                if is_week:
                    cutoff=date.today()-timedelta(days=7)
                    rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date() >= cutoff]
                elif target:
                    rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date()==target]
            # project filter for FTS case without DB filter fallback
            if project_q and not use_fts and project_q not in (None,):
                pass
            elif project_q and use_fts and project_q=="__none__":
                rows=[r for r in rows if r["project_id"] is None]
        else:
            # no text filter
            if project_q and project_q!="__none__" and project_q is not None:
                cur.execute("SELECT id,title,body,updated_at,project_id FROM notes WHERE project_id=(SELECT id FROM projects WHERE title=? COLLATE NOCASE) ORDER BY updated_at DESC LIMIT 100", (project_q,))
            elif project_q=="__none__":
                cur.execute("SELECT id,title,body,updated_at,project_id FROM notes WHERE project_id IS NULL ORDER BY updated_at DESC LIMIT 100")
            else:
                cur.execute("SELECT id,title,body,updated_at,project_id FROM notes ORDER BY updated_at DESC LIMIT 100")
            rows=cur.fetchall()
            if fecha:
                if fecha=="hoy": rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date()==date.today()]
                elif fecha=="semana":
                    cutoff=date.today()-timedelta(days=7)
                    rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date() >= cutoff]
        con.close()
        self.notes_list.clear()
        self._note_rows = rows
        # project lookup for badge
        proj_map={}
        for r in get_projects():
            pid = r["id"] if isinstance(r, sqlite3.Row) else r[0]
            title = r["title"] if isinstance(r, sqlite3.Row) else r[1]
            color = r["color"] if isinstance(r, sqlite3.Row) else r[3]
            icon = r["icon"] if isinstance(r, sqlite3.Row) else r[2]
            proj_map[pid]=(title, color, icon)
        for r in rows:
            ts=datetime.fromtimestamp(r["updated_at"]).strftime("%m-%d %H:%M")
            pend=r["body"].count("- [ ]")
            suffix=f"  ☐{pend}" if pend else ""
            proj_id = r["project_id"] if "project_id" in r.keys() else None
            proj_suffix=""
            if proj_id in proj_map:
                proj_suffix=f" [{proj_map[proj_id][2]} {proj_map[proj_id][0]}]"
            item = QListWidgetItem(f"{r['id']:>3}  {r['title'][:38]}{suffix}{proj_suffix}  · {ts}")
            item.setData(Qt.UserRole, r["id"])
            # subtle left border via background if project
            if proj_id in proj_map:
                try: item.setBackground(QColor(proj_map[proj_id][1])); item.setForeground(QColor("white"))
                except: pass
            self.notes_list.addItem(item)
        self.statusBar().showMessage(f"{len(rows)} notas" + (f" • filtro: {q}" if q else "") + (f" • proyecto:{project_q}" if project_q else ""), 3000)
        self.highlighter.setQuery(q)

    def on_select_note(self, item):
        nid = item.data(Qt.UserRole)
        con=db(); cur=con.cursor(); cur.execute("SELECT * FROM notes WHERE id=?", (nid,)); r=cur.fetchone()
        if not r: con.close(); return
        cur.execute("SELECT src_id FROM backlinks WHERE dst_title=?", (r["title"],))
        linked=[str(x[0]) for x in cur.fetchall()]
        con.close()
        self.current_note_id=nid
        self.title_entry.setText(r["title"])
        self.text_edit.setPlainText(r["body"])
        # project combobox sync
        pid = r["project_id"] if "project_id" in r.keys() else None
        if hasattr(self, 'note_project_combo'):
            self.note_project_combo.blockSignals(True)
            found=False
            for i in range(self.note_project_combo.count()):
                data=self.note_project_combo.itemData(i)
                if data==pid or (data is None and pid is None) or (data==-1 and pid is None):
                    self.note_project_combo.setCurrentIndex(i); found=True; break
            if not found: self.note_project_combo.setCurrentIndex(0)
            self.note_project_combo.blockSignals(False)
        # breadcrumb
        proj_name="Sin proyecto"
        color=THEME["accent"]
        if pid is not None:
            for pr in get_projects():
                ppid = pr["id"] if isinstance(pr, sqlite3.Row) else pr[0]
                if ppid==pid:
                    proj_name = f"{pr['icon'] if isinstance(pr, sqlite3.Row) else pr[2]} {pr['title'] if isinstance(pr, sqlite3.Row) else pr[1]}"
                    color = pr["color"] if isinstance(pr, sqlite3.Row) else pr[3]
                    break
        self.breadcrumb_label.setText(f"Vault / {proj_name} / {r['title'][:40]}")
        if pid is not None:
            self.project_badge.setText(proj_name); self.project_badge.setStyleSheet(f"padding:4px 10px; border-radius:10px; font-size:10px; background:{color}; color:white; font-weight:600;")
            self.project_badge.setVisible(True)
        else: self.project_badge.setVisible(False)
        self.highlighter.setQuery(self.search_entry.text())
        back = f" • enlazada por #{', #'.join(linked)}" if linked else ""
        self.statusBar().showMessage(f"Nota #{nid} • {len(re.findall(r'#(\w+)', r['body']+r['title']))} tags{back}", 4000)

    def new_note(self):
        idx=self.template_combo.currentIndex()
        keys=list(TEMPLATES.keys())
        tmpl_key=keys[idx] if 0 <= idx < len(keys) else "Diario"
        tmpl=TEMPLATES.get(tmpl_key, "")
        title_base=self.selected_date.strftime("%Y-%m-%d")
        body=tmpl.format(date=self.selected_date.strftime("%Y-%m-%d"), title=title_base)
        title=title_base
        if tmpl_key!="Diario":
            title, ok = QInputDialog.getText(self, "Nueva nota", f"Título ({tmpl_key}):", text=title_base)
            if not ok or not title.strip(): title=title_base
            if "{title}" not in tmpl:
                body = tmpl.format(date=self.selected_date.strftime("%Y-%m-%d"), title=title) if "{title}" in tmpl else body
            else:
                body = body.replace("{title}", title)
        con=db(); cur=con.cursor(); now=int(time.time())
        # project for new note
        pid = self.note_project_combo.currentData() if hasattr(self, 'note_project_combo') else None
        if pid==-1: pid=None
        if pid in (None,):
            # also check toolbar filter
            if self.current_project_id not in (None, -1):
                pid=self.current_project_id
        try:
            cur.execute("INSERT INTO notes(title,body,created_at,updated_at,project_id) VALUES(?,?,?,?,?)", (title, body, now, now, pid))
        except:
            cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (title, body, now, now))
        nid=cur.lastrowid
        try:
            for m in re.findall(r"\[\[([^\]]+)\]\]", body):
                cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (nid, m.strip()))
        except: pass
        con.commit(); con.close()
        self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
        for i in range(self.notes_list.count()):
            if self.notes_list.item(i).data(Qt.UserRole)==nid:
                self.notes_list.setCurrentRow(i)
                self.on_select_note(self.notes_list.item(i))
                break
        self.statusBar().showMessage(f"Nota creada #{nid} en {pid or 'sin proyecto'}", 3000)

    def save_note(self):
        title=self.title_entry.text()
        body=self.text_edit.toPlainText().strip()
        pid = self.note_project_combo.currentData() if hasattr(self, 'note_project_combo') else None
        if pid==-1: pid=None
        if not self.current_note_id:
            if not title.strip() and not body:
                QMessageBox.information(self, "Guardar", "Nada que guardar"); return
            con=db(); cur=con.cursor(); now=int(time.time())
            try: cur.execute("INSERT INTO notes(title,body,created_at,updated_at,project_id) VALUES(?,?,?,?,?)", (title or "Sin título", body, now, now, pid))
            except: cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (title or "Sin título", body, now, now))
            self.current_note_id=cur.lastrowid
            try:
                for m in re.findall(r"\[\[([^\]]+)\]\]", body):
                    cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (self.current_note_id, m.strip()))
            except: pass
            con.commit(); con.close()
            self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
            self.statusBar().showMessage(f"Nota creada #{self.current_note_id}", 3000); return
        con=db(); cur=con.cursor(); now=int(time.time())
        try: cur.execute("UPDATE notes SET title=?, body=?, updated_at=?, project_id=? WHERE id=?", (title, body, now, pid, self.current_note_id))
        except: cur.execute("UPDATE notes SET title=?, body=?, updated_at=? WHERE id=?", (title, body, now, self.current_note_id))
        tags=re.findall(r"#(\w+)", title+" "+body)
        try: cur.execute("DELETE FROM note_tags WHERE note_id=?", (self.current_note_id,))
        except: pass
        for t in tags:
            try:
                cur.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (t,))
                cur.execute("SELECT id FROM tags WHERE name=?", (t,)); tid=cur.fetchone()[0]
                cur.execute("INSERT OR IGNORE INTO note_tags(note_id,tag_id) VALUES(?,?)", (self.current_note_id, tid))
            except: pass
        cur.execute("DELETE FROM backlinks WHERE src_id=?", (self.current_note_id,))
        for m in re.findall(r"\[\[([^\]]+)\]\]", body):
            try: cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (self.current_note_id, m.strip()))
            except: pass
        con.commit(); con.close()
        self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
        self.statusBar().showMessage(f"Guardado #{self.current_note_id} ✓", 3000)

    def delete_note(self):
        if not self.current_note_id: return
        if QMessageBox.question(self, "Borrar", f"¿Borrar nota #{self.current_note_id}?") != QMessageBox.Yes: return
        con=db(); con.execute("DELETE FROM notes WHERE id=?", (self.current_note_id,)); con.commit(); con.close()
        self.current_note_id=None; self.title_entry.clear(); self.text_edit.clear()
        self.refresh_notes(); self.refresh_tasks(); self.refresh_tag_cloud()

    def insert_task(self): self.text_edit.insertPlainText("- [ ] "); self.text_edit.setFocus()
    def insert_link(self):
        txt, ok = QInputDialog.getText(self, "Enlace", "Nombre del enlace [[...]]:")
        if ok and txt: self.text_edit.insertPlainText(f"[[{txt}]]")
    def insert_tag(self):
        tag, ok = QInputDialog.getText(self, "Tag", "Tag sin #:")
        if ok and tag: self.text_edit.insertPlainText(f"#{tag} ")
    def toggle_task_in_editor(self):
        cursor=self.text_edit.textCursor()
        cursor.select(QTextCursor.LineUnderCursor)
        line=cursor.selectedText()
        if re.match(r"^- \[[ xX]\]", line):
            new=toggle_task_line(line)
            cursor.insertText(new)
            self.statusBar().showMessage("Tarea toggled — Ctrl+S para guardar", 3000)
        else:
            if line.strip():
                cursor.insertText(f"- [ ] {line}")
            else:
                cursor.insertText("- [ ] ")

    def auto_tag_hint(self):
        txt=self.title_entry.text()+" "+self.text_edit.toPlainText()
        tags=re.findall(r"#(\w+)", txt); links=re.findall(r"\[\[([^\]]+)\]\]", txt)
        tasks=re.findall(r"^- \[[ xX]\]", txt, flags=re.MULTILINE)
        hint="Tags: "+",".join(tags) if tags else ""
        if links: hint += "  Enlaces: "+",".join(links)
        if tasks: hint += f"  Tareas: {len(tasks)}"
        if hint: self.statusBar().showMessage(hint, 3000)


    def refresh_tasks(self):
        self.task_list.clear()
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body FROM notes"); rows=cur.fetchall(); con.close()
        self._task_map=[]
        pend=0
        # filtro prio
        filt = self.task_filter.currentText() if hasattr(self, 'task_filter') else "Todas"
        tasks = []
        for r in rows:
            for i,line in enumerate(r["body"].splitlines()):
                m=re.match(r"^- \[([ xX])\] (.+)", line)
                if m:
                    done=m.group(1).lower()=="x"
                    raw=m.group(2)
                    # parse due: y prio:
                    due = None; prio = None
                    mdue=re.search(r"due:(\S+)", raw)
                    if mdue: due=mdue.group(1); raw=re.sub(r"due:\S+","",raw).strip()
                    mprio=re.search(r"prio:(alta|media|baja)", raw, re.I)
                    if mprio: prio=mprio.group(1).lower(); raw=re.sub(r"prio:\S+","",raw, flags=re.I).strip()
                    if filt!="Todas" and (prio or "media") != filt and not (filt=="media" and not prio):
                        # si filtro alta/media/baja, solo mostrar coincidentes
                        if prio != filt:
                            continue
                    tasks.append((r["id"], i, line, done, raw[:44], r["title"][:16], due, prio))
        # ordenar: pendientes primero, luego por prio alta>media>baja, luego por due
        prio_order={"alta":0,"media":1,"baja":2, None:1}
        tasks.sort(key=lambda x: (x[3], prio_order.get(x[7],1), x[6] or "9999"))
        for nid, idx, line, done, txt, title, due, prio in tasks:
            if not done: pend+=1
            icon="\u2611" if done else "\u2610"
            suffix=""
            if due: suffix+=f" \U0001f4c5{due}"
            if prio: suffix+=f" \u26a1{prio}"
            item=QListWidgetItem(f"{icon} {txt}{suffix}  \u2014 {title} #{nid}")
            if done:
                item.setForeground(QColor("#888"))
            elif prio=="alta":
                item.setForeground(QColor("#c62828"))
            elif prio=="baja":
                item.setForeground(QColor("#2e7d32"))
            elif due:
                # vencida?
                try:
                    d=date.fromisoformat(due)
                    if d < date.today() and not done:
                        item.setBackground(QColor("#ffebee"))
                except: pass
            self.task_list.addItem(item)
            self._task_map.append((nid, idx, line))
        if hasattr(self, 'nav_buttons') and 2 in self.nav_buttons:
            self.nav_buttons[2].setText(f"\u2705\nTareas ({pend})")
    def on_toggle_task_global(self, item):
        idx=self.task_list.row(item)
        nid, line_idx, _ = self._task_map[idx]
        con=db(); cur=con.cursor(); cur.execute("SELECT body FROM notes WHERE id=?", (nid,)); body=cur.fetchone()["body"]
        lines=body.splitlines(); lines[line_idx]=toggle_task_line(lines[line_idx])
        new_body="\n".join(lines)
        cur.execute("UPDATE notes SET body=?, updated_at=? WHERE id=?", (new_body, int(time.time()), nid)); con.commit(); con.close()
        self.refresh_tasks()
        if self.current_note_id==nid:
            self.text_edit.setPlainText(new_body)

    def refresh_events(self):
        self.event_list.clear()
        con=db(); cur=con.cursor()
        dt=self.selected_date
        start=int(datetime(dt.year, dt.month, 1).timestamp())
        end=int(datetime(dt.year+1,1,1).timestamp()) if dt.month==12 else int(datetime(dt.year, dt.month+1,1).timestamp())
        cur.execute("SELECT id,title,start_ts,end_ts,note_id FROM events WHERE start_ts>=? AND start_ts<? ORDER BY start_ts", (start,end))
        self._event_ids=[]
        for r in cur.fetchall():
            d=datetime.fromtimestamp(r["start_ts"]).strftime("%d %H:%M")
            suffix=f" \u2192 nota #{r['note_id']}" if r["note_id"] else ""
            item=QListWidgetItem(f"{d}  {r['title']}{suffix}")
            self.event_list.addItem(item); self._event_ids.append(r["id"])
        con.close()
    def new_event(self):
        title, ok = QInputDialog.getText(self, "Nuevo evento", "T\u00edtulo del evento:")
        if not ok or not title: return
        hora, ok = QInputDialog.getText(self, "Hora", "Hora inicio (HH:MM):", text="10:00")
        dt=self.selected_date.replace(hour=10, minute=0, second=0)
        if ok and hora:
            try: h,m=map(int, hora.split(":")); dt=dt.replace(hour=h, minute=m)
            except: pass
        desc, _ = QInputDialog.getText(self, "Descripci\u00f3n", "Descripci\u00f3n (opcional):")
        start=int(dt.timestamp()); end=start+3600
        con=db(); cur=con.cursor(); uid=f"{int(time.time())}-{start}@gnote.local"
        cur.execute("INSERT INTO events(title,description,location,start_ts,end_ts,uid,source,created_at,note_id) VALUES(?,?,?,?,?,?,?,?,?)",
                    (title, desc or "", "", start, end, uid, "local", int(time.time()), self.current_note_id or None))
        con.commit(); con.close(); self.refresh_calendar()
    def delete_event(self):
        row=self.event_list.currentRow()
        if row<0: return
        if QMessageBox.question(self, "Borrar", "¿Borrar evento?") != QMessageBox.Yes: return
        eid=self._event_ids[row]
        con=db(); con.execute("DELETE FROM events WHERE id=?", (eid,)); con.commit(); con.close(); self.refresh_calendar()
    def link_event_note(self):
        row=self.event_list.currentRow()
        if row<0: QMessageBox.information(self, "Vincular", "Selecciona un evento del mes primero"); return
        if not self.current_note_id: QMessageBox.information(self, "Vincular", "Selecciona una nota a vincular"); return
        eid=self._event_ids[row]
        con=db(); con.execute("UPDATE events SET note_id=? WHERE id=?", (self.current_note_id, eid)); con.commit(); con.close()
        self.refresh_events(); self.statusBar().showMessage(f"Evento #{eid} vinculado a nota #{self.current_note_id}", 3000)
    def on_edit_event(self, item):
        row=self.event_list.row(item)
        eid=self._event_ids[row]
        con=db(); cur=con.cursor(); cur.execute("SELECT * FROM events WHERE id=?", (eid,)); r=cur.fetchone(); con.close()
        if r: QMessageBox.information(self, "Evento", f"{r['title']}\n{datetime.fromtimestamp(r['start_ts'])}\n\u2192 {datetime.fromtimestamp(r['end_ts'])}\n{r['description']}\nNota vinculada: {r['note_id'] or 'ninguna'}")

    def export_ics(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar .ics", "calendario.ics", "Calendario (*.ics)")
        if not path: return
        if os.path.exists(BIN_PATH):
            r=subprocess.run([BIN_PATH, "ics", "export", "--output", path], capture_output=True, text=True)
            QMessageBox.information(self, "Exportar", r.stdout.strip() if r.returncode==0 else r.stderr)
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
            QMessageBox.information(self, "Exportar", f"Exportados {len(rows)} eventos a {path}")
    def import_ics(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar .ics", "", "Calendario (*.ics)")
        if not path: return
        if os.path.exists(BIN_PATH):
            r=subprocess.run([BIN_PATH, "ics", "import", path], capture_output=True, text=True)
            QMessageBox.information(self, "Importar", (r.stdout+r.stderr).strip())
        else: QMessageBox.information(self, "Importar", "Usa el binario para importar")
        self.refresh_calendar()
    def export_markdown(self):
        if not self.current_note_id: QMessageBox.information(self, "Export", "Selecciona una nota"); return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar .md", f"nota-{self.current_note_id}.md", "Markdown (*.md)")
        if not path: return
        title=self.title_entry.text(); body=self.text_edit.toPlainText()
        open(path,"w",encoding="utf-8").write(f"# {title}\n\n{body}\n")
        QMessageBox.information(self, "Export", f"Nota exportada a {path}")

    def get_sync_folder(self): return get_sync_folder()
    def set_sync_folder(self, folder): set_sync_folder(folder)
    def show_folder_sync(self):
        cur = get_sync_folder()
        folder, ok = QFileDialog.getExistingDirectory(self, "Elegir carpeta sync", cur), True
        # getExistingDirectory returns str not tuple in PySide6; PyQt5 returns str
        if isinstance(folder, tuple): folder = folder[0]
        if folder:
            set_sync_folder(folder)
            self.statusBar().showMessage(f"Folder sync \u2192 {folder}", 3000)
            # ask sync now
            if QMessageBox.question(self, "Folder Sync", f"Nueva carpeta:\n{folder}\n\u00bfSincronizar ahora?", QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
                if os.path.exists(BIN_PATH):
                    r=subprocess.run([BIN_PATH, "sync", "--folder", folder], capture_output=True, text=True)
                    body=(r.stdout+r.stderr).strip() or "Sincronizado"
                else:
                    body=self._python_sync(folder)
                QMessageBox.information(self, "Sync", body)
                self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
                # update watcher
                if self.watcher:
                    try: self.watcher.removePaths(self.watcher.directories())
                    except: pass
                    self.watcher.addPath(folder)
        else:
            # show info dialog with current
            QMessageBox.information(self, "Folder Sync", f"Carpeta actual:\n{cur}\n\n1 .md por nota con frontmatter id/title.\nCLI: gnote-calendar sync --folder ~/Notas")
    def _python_sync(self, folder):
        os.makedirs(folder, exist_ok=True)
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body FROM notes")
        exp=0
        for r in cur.fetchall():
            safe="".join(c if c.isalnum() or c in "-_" else "-" if c==" " else "" for c in r["title"])[:40] or "nota"
            path=os.path.join(folder, f"{r['id']:04d}-{safe}.md")
            front=f"---\nid: {r['id']}\ntitle: \"{r['title']}\"\n---\n\n{r['body']}\n"
            if not os.path.exists(path) or open(path, encoding="utf-8").read()!=front:
                open(path,"w",encoding="utf-8").write(front); exp+=1
        con.close()
        return f"Exportados {exp} (fallback)"

    def auto_folder_sync(self):
        folder=get_sync_folder()
        if os.path.isdir(folder) and os.path.exists(BIN_PATH):
            try:
                r=subprocess.run([BIN_PATH, "sync", "--folder", folder], capture_output=True, text=True, timeout=3)
                if "Importados" in r.stdout or "Exportados" in r.stdout:
                    if any(c.isdigit() and int(c)>0 for c in r.stdout if c.isdigit()):
                        self.refresh_notes(); self.refresh_tasks()
            except: pass
        # reschedule via timer already

    def open_pomodoro(self):
        if self.pomodoro_win and self.pomodoro_win.isVisible(): self.pomodoro_win.raise_(); return
        self.pomodoro_win=PomodoroDialog(self); self.pomodoro_win.show()

    def show_stats(self):
        con=db(); cur=con.cursor()
        cur.execute("SELECT COUNT(*) FROM notes"); n_notes=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM events"); n_ev=cur.fetchone()[0]
        cur.execute("SELECT body FROM notes"); bodies=[r[0] for r in cur.fetchall()]
        tasks=sum(b.count("- [ ]")+b.count("- [x]") for b in bodies)
        pend=sum(b.count("- [ ]") for b in bodies)
        tags=set(re.findall(r"#(\w+)", "".join(bodies)))
        try: cur.execute("SELECT COUNT(*) FROM backlinks"); n_links=cur.fetchone()[0]
        except: n_links=0
        con.close()
        QMessageBox.information(self, "Estad\u00edsticas", f"\U0001f4dd Notas: {n_notes}\n\U0001f4c5 Eventos: {n_ev}\n\u2705 Tareas: {pend}/{tasks} pendientes\n\ud83c\udff7\ufe0f Tags: {len(tags)}\n\U0001f517 Enlaces: {n_links}\n\U0001f4c1 Sync: {get_sync_folder()}\n\nDB: {DB_PATH}\nQt: {QT_LIB}")

    def show_graph(self):
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title FROM notes"); nodes_data=cur.fetchall()
        cur.execute("SELECT src_id, dst_title FROM backlinks"); links_raw=cur.fetchall()
        con.close()
        if not nodes_data:
            QMessageBox.information(self, "Grafo", "Sin notas. Usa [[enlace]]"); return
        title_to_id={r["title"].strip().lower(): r["id"] for r in nodes_data}
        id_to_title={r["id"]: r["title"][:18] for r in nodes_data}
        import math, random
        N=len(nodes_data)
        nodes=[]
        for i,r in enumerate(nodes_data):
            ang=2*math.pi*i/max(1,N)
            nodes.append({"id":r["id"], "title":id_to_title[r["id"]], "x":360+150*math.cos(ang)+random.uniform(-10,10), "y":260+150*math.sin(ang)+random.uniform(-10,10), "vx":0, "vy":0})
        id_to_idx={n["id"]:i for i,n in enumerate(nodes)}
        edges=[]
        for src,dst_title in links_raw:
            did=title_to_id.get(dst_title.strip().lower())
            if did and src in id_to_idx and did in id_to_idx:
                edges.append((id_to_idx[src], id_to_idx[did]))
        def on_navigate(nid):
            for i in range(self.notes_list.count()):
                if self.notes_list.item(i).data(Qt.UserRole)==nid:
                    self.notes_list.setCurrentRow(i)
                    self.on_select_note(self.notes_list.item(i))
                    break
        dlg=QDialog(self); dlg.setWindowTitle("Grafo Knowledge OS \u2014 fuerza dirigida"); dlg.resize(720,560)
        lay=QVBoxLayout(dlg)
        lay.addWidget(QLabel("Grafo de [[enlaces]] \u2014 arrastra nodos \u2022 click navega a nota", dlg))
        view=GraphView(nodes, edges, self.current_note_id, on_navigate, dlg)
        lay.addWidget(view)
        hint=QLabel(f"Grafo: {len(nodes)} nodos, {len(edges)} enlaces \u2014 arrastra para organizar", dlg); hint.setStyleSheet("color:#666; font-size:11px;")
        lay.addWidget(hint)
        dlg.exec() if hasattr(dlg,'exec') else dlg.exec_()

    def check_upcoming(self):
        try:
            con=db(); cur=con.cursor(); now=int(time.time())
            cur.execute("SELECT title,start_ts FROM events WHERE start_ts>=? AND start_ts<=? LIMIT 3", (now, now+900))
            for r in cur.fetchall():
                self.notify_event(f"\u23f0 {r['title']}", f"{datetime.fromtimestamp(r['start_ts']).strftime('%H:%M')}")
            con.close()
        except: pass
        QTimer.singleShot(60000, self.check_upcoming)


    def delete_event_cal(self):
        # compat for calendario page
        row=self.event_list_cal.currentRow() if hasattr(self,'event_list_cal') else -1
        if row<0: return
        # need mapping from cal list
        # fallback to refresh_events logic: we sync both lists, so use _event_ids_cal? reuse _event_ids but they are same length for both months
        # For simplicity, delete via event_list_cal and refresh
        try:
            eid=self._event_ids[row]
            if QMessageBox.question(self, "Borrar", "¿Borrar evento?") != QMessageBox.Yes: return
            con=db(); con.execute("DELETE FROM events WHERE id=?", (eid,)); con.commit(); con.close(); self.refresh_calendar()
        except: pass

    def refresh_events(self):
        # dual sync: notas and calendario lists use same data
        for lst_name in ['event_list','event_list_cal']:
            if not hasattr(self, lst_name): continue
            lst=getattr(self, lst_name)
            lst.clear()
        con=db(); cur=con.cursor()
        dt=self.selected_date
        start=int(datetime(dt.year, dt.month, 1).timestamp())
        end=int(datetime(dt.year+1,1,1).timestamp()) if dt.month==12 else int(datetime(dt.year, dt.month+1,1).timestamp())
        cur.execute("SELECT id,title,start_ts,end_ts,note_id FROM events WHERE start_ts>=? AND start_ts<? ORDER BY start_ts", (start,end))
        self._event_ids=[]
        rows=cur.fetchall()
        for r in rows:
            d=datetime.fromtimestamp(r["start_ts"]).strftime("%d %H:%M")
            suffix=f" → nota #{r['note_id']}" if r["note_id"] else ""
            item_text=f"{d}  {r['title']}{suffix}"
            for lst_name in ['event_list','event_list_cal']:
                if hasattr(self, lst_name):
                    getattr(self, lst_name).addItem(item_text)
            self._event_ids.append(r["id"])
        con.close()


def main():
    if not QT_AVAILABLE:
        print(f"Qt no disponible (PySide6/PySide2/PyQt5 no instalado).", file=sys.stderr)
        print(f"Instala: pip install --break-system-packages PySide6==6.7.3", file=sys.stderr)
        print(f"Falling back a gui.py Tk...", file=sys.stderr)
        tk_path = os.path.join(os.path.dirname(__file__), "gui.py")
        if os.path.exists(tk_path):
            os.execv(sys.executable, [sys.executable, tk_path] + sys.argv[1:])
        sys.exit(1)
    ensure_db()
    app = QApplication(sys.argv)
    app.setApplicationName("gnote-calendar")
    # Smoke flag para bench
    if "--smoke" in sys.argv:
        w=MainWindow(); w.show()
        QTimer.singleShot(1200, app.quit)
        return app.exec() if hasattr(app,'exec') else app.exec_()
    win = MainWindow()
    win.show()
    sys.exit(app.exec() if hasattr(app,'exec') else app.exec_())

if __name__=="__main__":
    main()
