#!/usr/bin/env python3
# gnote-calendar GUI Qt6 (PySide6) - reemplazo de GTK4/Tk, RAM <60MB
# Paridad v1.4: notas FTS5, tags, backlinks, tareas, calendario, pomodoro, folder sync, grafo, ics
# Fallback: PySide6 -> PySide2 -> PyQt5 (apt). Offline-first, WAL.
import os, sys, re, subprocess, time, calendar, sqlite3, json
from datetime import datetime, timedelta, date
try:
    import markdown as md_lib
    HAS_MARKDOWN = True
except: 
    md_lib = None
    HAS_MARKDOWN = False

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
    try: backup_db()
    except: pass
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
            self.query = qs
            self.rehighlight()
        def highlightBlock(self, text):
            if not self.query:
                return
            for m in re.finditer(re.escape(self.query), text, re.IGNORECASE):
                self.setFormat(m.start(), m.end()-m.start(), self.fmt)
else:
    class SearchHighlighter:
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
        self.setWindowTitle("gnote-calendar \u2014 Notas y Calendario (Qt)")
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.setMinimumSize(1024, 620)
        self.resize(1320, 800)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.current_note_id = None
        self.selected_date = datetime.now()
        self.pomodoro_win = None
        self._event_ids = []
        self._task_map = []
        self.watcher = None
        self._current_section = 0  # 0 Notas, 1 Calendario, 2 Tareas
        self._build_ui()
        try:
            backup_db()
            ensure_daily_note()
        except: pass
        self.refresh_notes()
        self.refresh_calendar()
        self.refresh_tasks()
        self.refresh_tag_cloud()
        self.check_upcoming()
        QTimer.singleShot(5000, self.auto_folder_sync)
        self._setup_watcher()
        self._setup_tray()
        self._setup_accessibility()
        QTimer.singleShot(1000, lambda: self.statusBar().showMessage(f"Qt {QT_LIB} \u2022 Listo. Usa #tag y [[enlace]] \u2022 Ctrl+S guardar \u2022 F11 maximizar", 5000))
        try:
            self._load_settings()
        except: pass

    def _build_ui(self):
        # Menu minimalista
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&Archivo")
        act_export_md = QAction("Exportar .md", self); act_export_md.triggered.connect(self.export_markdown); file_menu.addAction(act_export_md)
        act_export_ics = QAction("Exportar .ics \u2192 Gmail", self); act_export_ics.triggered.connect(self.export_ics); file_menu.addAction(act_export_ics)
        act_import_ics = QAction("Importar .ics", self); act_import_ics.triggered.connect(self.import_ics); file_menu.addAction(act_import_ics)
        file_menu.addSeparator()
        act_quit = QAction("Salir", self); act_quit.triggered.connect(self.close); file_menu.addAction(act_quit)
        view_menu = menubar.addMenu("&Ver")
        act_stats = QAction("\U0001f4ca Estad\u00edsticas", self); act_stats.triggered.connect(self.show_stats); view_menu.addAction(act_stats)
        act_graph = QAction("\U0001f578\ufe0f Grafo", self); act_graph.triggered.connect(self.show_graph); view_menu.addAction(act_graph)
        act_full = QAction("Pantalla completa (F11)", self); act_full.setShortcut(QKeySequence("F11")); act_full.triggered.connect(self.toggle_maximize); view_menu.addAction(act_full)
        tool_menu = menubar.addMenu("&Herramientas")
        act_sync = QAction("\U0001f4c1 Folder Sync", self); act_sync.triggered.connect(self.show_folder_sync); tool_menu.addAction(act_sync)
        act_pomodoro = QAction("\U0001f345 Pomodoro", self); act_pomodoro.triggered.connect(self.open_pomodoro); tool_menu.addAction(act_pomodoro)

        # Top toolbar - solo acciones globales (descargada)
        toolbar = QToolBar("Principal", self)
        toolbar.setObjectName("Principal")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16,16))
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        toolbar.addWidget(QLabel(" Plantilla: "))
        self.template_combo = QComboBox(self); self.template_combo.addItems(list(TEMPLATES.keys())); self.template_combo.setFixedWidth(120)
        self.template_combo.setToolTip("Elige plantilla para nueva nota")
        toolbar.addWidget(self.template_combo)
        btn_new = QPushButton("Nueva nota", self); btn_new.clicked.connect(self.new_note); btn_new.setStyleSheet("background:#4a90e2; color:white; font-weight:bold; padding:4px 10px;"); btn_new.setToolTip("Ctrl+N")
        toolbar.addWidget(btn_new)
        btn_save = QPushButton("Guardar", self); btn_save.clicked.connect(self.save_note); btn_save.setToolTip("Ctrl+S"); toolbar.addWidget(btn_save)
        btn_del = QPushButton("Borrar", self); btn_del.clicked.connect(self.delete_note); toolbar.addWidget(btn_del)
        toolbar.addSeparator()
        btn_max = QPushButton("\u26f6 Maximizar (F11)", self); btn_max.clicked.connect(self.toggle_maximize); btn_max.setToolTip("F11 alterna maximizar"); toolbar.addWidget(btn_max)

        # Central: QHBox con sidebar + splitter (más aire)
        central = QWidget(self); central_layout = QHBoxLayout(central); central_layout.setContentsMargins(0,0,0,0); central_layout.setSpacing(8)
        self.setCentralWidget(central)

        # Sidebar navegación (94px) - con más respiración
        sidebar = QFrame(self); sidebar.setFrameShape(QFrame.StyledPanel); sidebar.setFixedWidth(94); sidebar.setStyleSheet("QFrame { background:#f8f9fb; border-right:1px solid #e1e4e8; } QToolButton { border:none; padding:6px; font-size:9.5pt; } QToolButton:checked { background:#e3f2fd; border-radius:8px; }")
        side_l = QVBoxLayout(sidebar); side_l.setContentsMargins(6,12,6,12); side_l.setSpacing(8)
        hdr = QLabel("Secciones", sidebar, alignment=Qt.AlignCenter); hdr.setStyleSheet("font-size:8pt; color:#666; font-weight:bold;"); side_l.addWidget(hdr)
        self.nav_group = QButtonGroup(self); self.nav_group.setExclusive(True)
        sections = [("\U0001f4dd", "Notas", 0), ("\U0001f4c5", "Calendario", 1), ("\u2705", "Tareas", 2), ("\U0001f578\ufe0f", "Grafo", 3)]
        self.nav_buttons = {}
        for icon, name, idx in sections:
            btn = QToolButton(sidebar); btn.setText(f"{icon}\n{name}"); btn.setCheckable(True); btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setFixedSize(86, 64)
            btn.setIconSize(QSize(22,22))
            if idx==0: btn.setChecked(True)
            btn.clicked.connect(lambda _, i=idx: self.switch_section(i))
            side_l.addWidget(btn, alignment=Qt.AlignCenter); self.nav_group.addButton(btn, idx); self.nav_buttons[idx]=btn
        side_l.addSpacing(8)
        # Herramientas en sidebar (descongestiona top bar) - Grafo ya es sección
        for icon, tip, cb in [("\U0001f345", "Pomodoro", self.open_pomodoro), ("\U0001f4ca", "Stats", self.show_stats), ("\U0001f4c1", "Sync", self.show_folder_sync)]:
            b = QToolButton(sidebar); b.setText(icon); b.setToolTip(tip); b.setFixedSize(86,36); b.clicked.connect(cb); side_l.addWidget(b, alignment=Qt.AlignCenter)
        side_l.addStretch()
        foot = QLabel(f"Qt {QT_LIB}", sidebar, alignment=Qt.AlignCenter); foot.setStyleSheet("font-size:8pt; color:#888;"); side_l.addWidget(foot)
        central_layout.addWidget(sidebar)

        # Middle + Right en splitter (más aire)
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        central_layout.addWidget(splitter)

        # Middle: QStackedWidget con secciones (desatura)
        self.stacked = QStackedWidget(self)
        splitter.addWidget(self.stacked)

        # Page 0: Notas - más aire (antes apiñuscado)
        page_notas = QWidget(self); pn_l = QVBoxLayout(page_notas); pn_l.setContentsMargins(14,14,14,14); pn_l.setSpacing(12)
        # buscador dentro de Notas (no en top bar)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Filtrar:", self))
        self.search_entry = QLineEdit(self); self.search_entry.setPlaceholderText("Buscar #tag texto…  fecha:hoy/semana  highlight amarillo"); self.search_entry.setClearButtonEnabled(True)
        self.search_entry.textChanged.connect(self.refresh_notes)
        search_row.addWidget(self.search_entry)
        btn_clear = QPushButton("\u2715", self); btn_clear.setFixedWidth(28); btn_clear.setToolTip("Limpiar filtro Esc"); btn_clear.clicked.connect(lambda: self.search_entry.clear())
        search_row.addWidget(btn_clear)
        pn_l.addLayout(search_row)
        # hint
        hint = QLabel("Tip: tag:casa  fecha:hoy  #tag  [[enlace]]  - [ ] tarea", self); hint.setStyleSheet("color:#777; font-size:11px;"); pn_l.addWidget(hint)
        # tag cloud
        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel("Tags:", self))
        self.tag_cloud = QHBoxLayout()
        tag_container = QWidget(self); tag_container.setLayout(self.tag_cloud)
        tag_row.addWidget(tag_container); tag_row.addStretch()
        btn_filter_clear = QPushButton("\u2715 filtro", self); btn_filter_clear.clicked.connect(lambda: self.search_entry.clear()); tag_row.addWidget(btn_filter_clear)
        pn_l.addLayout(tag_row)
        pn_l.addWidget(QLabel("Notas (click abre en editor \u2192)", self))
        self.notes_list = QListWidget(self); self.notes_list.setAlternatingRowColors(True); self.notes_list.itemClicked.connect(self.on_select_note)
        self.notes_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pn_l.addWidget(self.notes_list)
        pn_l.addWidget(QLabel("Eventos del mes (doble click detalle)", self))
        self.event_list = QListWidget(self); self.event_list.setMaximumHeight(130); self.event_list.itemDoubleClicked.connect(self.on_edit_event); pn_l.addWidget(self.event_list)
        ev_btns = QHBoxLayout()
        b_ne = QPushButton("Nuevo evento", self); b_ne.clicked.connect(self.new_event); ev_btns.addWidget(b_ne)
        b_de = QPushButton("Borrar", self); b_de.clicked.connect(self.delete_event); ev_btns.addWidget(b_de)
        b_ln = QPushButton("Vincular nota", self); b_ln.clicked.connect(self.link_event_note); ev_btns.addWidget(b_ln)
        pn_l.addLayout(ev_btns)
        self.stacked.addWidget(page_notas)

        # Page 1: Calendario - más aire
        page_cal = QWidget(self); pc_l = QVBoxLayout(page_cal); pc_l.setContentsMargins(14,14,14,14); pc_l.setSpacing(12)
        cal_head = QHBoxLayout()
        self.cal_label = QLabel("", self); self.cal_label.setStyleSheet("font-weight:bold; font-size:14px;")
        cal_head.addWidget(self.cal_label); cal_head.addStretch()
        btn_today = QPushButton("Hoy", self); btn_today.clicked.connect(self.go_today); cal_head.addWidget(btn_today)
        btn_prev = QPushButton("\u25c0", self); btn_prev.setFixedWidth(36); btn_prev.clicked.connect(lambda: self.shift_month(-1)); cal_head.addWidget(btn_prev)
        btn_next = QPushButton("\u25b6", self); btn_next.setFixedWidth(36); btn_next.clicked.connect(lambda: self.shift_month(1)); cal_head.addWidget(btn_next)
        pc_l.addLayout(cal_head)
        # Toggle mes/semana
        toggle_cal = QHBoxLayout()
        self.btn_view_month = QPushButton("\U0001f4c5 Mes", self); self.btn_view_month.setCheckable(True); self.btn_view_month.setChecked(True); self.btn_view_month.clicked.connect(lambda: self.switch_cal_view(0))
        self.btn_view_week = QPushButton("\U0001f5d3 Semana", self); self.btn_view_week.setCheckable(True); self.btn_view_week.clicked.connect(lambda: self.switch_cal_view(1))
        grp_cal = QButtonGroup(self); grp_cal.addButton(self.btn_view_month,0); grp_cal.addButton(self.btn_view_week,1); grp_cal.setExclusive(True)
        toggle_cal.addWidget(self.btn_view_month); toggle_cal.addWidget(self.btn_view_week); toggle_cal.addStretch()
        pc_l.addLayout(toggle_cal)
        self.cal_stack = QStackedWidget(self)
        # Mes view
        mes_w = QWidget(self); mes_l = QVBoxLayout(mes_w); mes_l.setContentsMargins(0,0,0,0)
        self.calendar = CalendarWidget(self)
        self.calendar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mes_l.addWidget(self.calendar)
        mes_l.addWidget(QLabel("Leyenda: \u2022 verde = evento  \u2022 azul = hoy  \u2022 click d\u00eda selecciona", self))
        self.cal_stack.addWidget(mes_w)
        # Semana view - QTable 7x24
        semana_w = QWidget(self); sw_l = QVBoxLayout(semana_w); sw_l.setContentsMargins(0,0,0,0)
        self.week_table = QTableWidget(24, 7, self)
        self.week_table.setHorizontalHeaderLabels(["Lu","Ma","Mi","Ju","Vi","S\u00e1","Do"])
        self.week_table.verticalHeader().setDefaultSectionSize(22)
        self.week_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.week_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.week_table.setSelectionMode(QTableWidget.NoSelection)
        self.week_table.cellDoubleClicked.connect(self.on_week_cell)
        sw_l.addWidget(QLabel("Semana - doble click crea evento 10:00", self))
        sw_l.addWidget(self.week_table)
        self.cal_stack.addWidget(semana_w)
        pc_l.addWidget(self.cal_stack)
        pc_l.addWidget(QLabel("Eventos del mes (abajo) - doble click detalle", self))
        self.event_list = QListWidget(self); self.event_list.setMaximumHeight(110); self.event_list.itemDoubleClicked.connect(self.on_edit_event)
        pc_l.addWidget(self.event_list)
        ev_btns = QHBoxLayout()
        b_ne = QPushButton("Nuevo evento", self); b_ne.clicked.connect(self.new_event); ev_btns.addWidget(b_ne)
        b_de = QPushButton("Borrar", self); b_de.clicked.connect(self.delete_event); ev_btns.addWidget(b_de)
        b_ln = QPushButton("Vincular nota", self); b_ln.clicked.connect(self.link_event_note); ev_btns.addWidget(b_ln)
        pc_l.addLayout(ev_btns)
        self.stacked.addWidget(page_cal)

        # Page 2: Tareas - más aire
        page_tasks = QWidget(self); pt_l = QVBoxLayout(page_tasks); pt_l.setContentsMargins(14,14,14,14); pt_l.setSpacing(12)
        pt_l.addWidget(QLabel("Tareas globales \u2014 doble click completa  • due:YYYY-MM-DD prio:alta/media/baja", self))
        # Filtro prio
        filt = QHBoxLayout()
        filt.addWidget(QLabel("Filtrar prio:", self))
        self.task_filter = QComboBox(self); self.task_filter.addItems(["Todas","alta","media","baja"]); self.task_filter.currentTextChanged.connect(self.refresh_tasks)
        filt.addWidget(self.task_filter)
        filt.addStretch()
        btn_upd = QPushButton("Actualizar", self); btn_upd.clicked.connect(self.refresh_tasks); filt.addWidget(btn_upd)
        pt_l.addLayout(filt)
        self.task_list = QListWidget(self); self.task_list.itemDoubleClicked.connect(self.on_toggle_task_global)
        self.task_list.setAlternatingRowColors(True)
        pt_l.addWidget(self.task_list)
        pt_l.addWidget(QLabel("Sintaxis: - [ ] texto due:2026-08-24 prio:alta", self))
        self.stacked.addWidget(page_tasks)

        # Page 3: Grafo embebido - más aire
        page_graph = QWidget(self); pg_l = QVBoxLayout(page_graph); pg_l.setContentsMargins(14,14,14,14); pg_l.setSpacing(12)
        pg_l.addWidget(QLabel("\U0001f578\ufe0f Grafo Knowledge OS \u2014 arrastra nodos, click navega", self))
        filt_g = QHBoxLayout()
        filt_g.addWidget(QLabel("Filtrar tag:", self))
        self.graph_filter = QLineEdit(self); self.graph_filter.setPlaceholderText("ej: trabajo, deja vac\u00edo para todos"); self.graph_filter.setMaximumWidth(200)
        filt_g.addWidget(self.graph_filter)
        btn_gf = QPushButton("Filtrar", self); btn_gf.clicked.connect(self.refresh_graph_page); filt_g.addWidget(btn_gf)
        btn_gr = QPushButton("Actualizar", self); btn_gr.clicked.connect(self.refresh_graph_page); filt_g.addWidget(btn_gr)
        btn_go = QPushButton("Ventana grande", self); btn_go.clicked.connect(self.show_graph); filt_g.addWidget(btn_go)
        filt_g.addStretch()
        pg_l.addLayout(filt_g)
        self.graph_container = QVBoxLayout()
        # placeholder label, se crea GraphView dinámico
        self.graph_placeholder = QLabel("Cargando grafo…", self, alignment=Qt.AlignCenter)
        self.graph_placeholder.setStyleSheet("color:#888; padding:20px;")
        pg_l.addWidget(self.graph_placeholder)
        pg_l.addLayout(self.graph_container)
        self.stacked.addWidget(page_graph)

        # Right editor - split markdown con más respiración
        right = QWidget(self); right_layout = QVBoxLayout(right); right_layout.setContentsMargins(16,16,16,16); right_layout.setSpacing(12)
        right.setMinimumWidth(460)
        hdr = QHBoxLayout(); hdr.setSpacing(8)
        hdr.addWidget(QLabel("T\u00edtulo:", self))
        self.title_entry = QLineEdit(self); self.title_entry.setPlaceholderText("T\u00edtulo de la nota\u2026"); self.title_entry.setMinimumHeight(32)
        hdr.addWidget(self.title_entry)
        self.title_entry.textChanged.connect(self.auto_tag_hint)
        right_layout.addLayout(hdr)
        tb = QHBoxLayout(); tb.setSpacing(6)
        for label, cb in [("\u2610 Tarea", self.insert_task), ("\u2713 Toggle", self.toggle_task_in_editor), ("\U0001f517 [[link]]", self.insert_link), ("#tag", self.insert_tag)]:
            b = QPushButton(label, self); b.setMinimumHeight(28); b.clicked.connect(cb); tb.addWidget(b)
        tb.addStretch()
        self.btn_preview = QPushButton("\U0001f441 Vista previa", self); self.btn_preview.setCheckable(True); self.btn_preview.setMinimumHeight(28); self.btn_preview.setToolTip("Alternar preview markdown (F9)"); self.btn_preview.toggled.connect(self.toggle_preview)
        tb.addWidget(self.btn_preview)
        b_exp = QPushButton("Export .md", self); b_exp.setMinimumHeight(28); b_exp.clicked.connect(self.export_markdown); tb.addWidget(b_exp)
        right_layout.addLayout(tb)
        # Split editor / preview
        self.editor_split = QSplitter(Qt.Vertical, self)
        self.text_edit = QTextEdit(self); self.text_edit.setPlaceholderText("Escribe markdown, #tag, [[enlace]], - [ ] tarea\u2026  (Ctrl+S guarda)"); self.text_edit.textChanged.connect(self.on_editor_changed)
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        doc_font = QFont("Sans", 11); doc_font.setStyleHint(QFont.SansSerif); self.text_edit.setFont(doc_font)
        self.editor_split.addWidget(self.text_edit)
        self.preview_browser = QTextBrowser(self); self.preview_browser.setOpenExternalLinks(True); self.preview_browser.setVisible(False)
        self.preview_browser.setStyleSheet("QTextBrowser { background:#fcfcfc; padding:10px; }")
        self.editor_split.addWidget(self.preview_browser)
        self.editor_split.setSizes([400, 200])
        right_layout.addWidget(self.editor_split)
        self.highlighter = SearchHighlighter(self.text_edit.document())
        splitter.addWidget(right)
        splitter.setSizes([520, 680])
        splitter.setStretchFactor(0, 0); splitter.setStretchFactor(1, 1)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pn_l.setSpacing(8)
        pc_l.setSpacing(8)
        pt_l.setSpacing(8)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # shortcuts globales (incluye maximizar y preview)
        for seq, cb in [("Ctrl+S", self.save_note), ("Ctrl+N", self.new_note), ("Ctrl+P", self.open_pomodoro), ("F11", self.toggle_maximize), ("F9", self.toggle_preview)]:
            act = QAction(self); act.setShortcut(QKeySequence(seq)); act.triggered.connect(cb if seq!="F9" else lambda: self.btn_preview.setChecked(not self.btn_preview.isChecked())); self.addAction(act)
        act_toggle = QAction(self); act_toggle.setShortcut(QKeySequence("Ctrl+Return")); act_toggle.triggered.connect(self.toggle_task_in_editor); self.addAction(act_toggle)
        act_esc = QAction(self); act_esc.setShortcut(QKeySequence("Escape")); act_esc.triggered.connect(lambda: self.search_entry.clear() if self.stacked.currentIndex()==0 else None); self.addAction(act_esc)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Listo. Usa #tag y [[enlace]] \u2022 Ctrl+S guardar \u2022 Ctrl+Enter toggle \u2022 F11 maximizar")

        # dark/light auto via palette check
        self._apply_theme()

    def toggle_preview(self, checked=None):
        if checked is None:
            checked = self.btn_preview.isChecked()
        else:
            self.btn_preview.setChecked(checked)
        self.preview_browser.setVisible(checked)
        if checked:
            self.update_preview()
            self.statusBar().showMessage("Vista previa markdown activa (F9 para ocultar)", 3000)
        else:
            self.statusBar().showMessage("Vista previa oculta", 2000)

    def on_editor_changed(self):
        self.auto_tag_hint()
        if hasattr(self, 'preview_browser') and self.preview_browser.isVisible():
            self.update_preview()

    def update_preview(self):
        body = self.text_edit.toPlainText()
        title = self.title_entry.text()
        # Render markdown simple + tags
        if HAS_MARKDOWN and md_lib:
            try:
                html = md_lib.markdown(f"# {title}\n\n{body}", extensions=['extra', 'codehilite', 'toc'])
                # replace tags and links visually
                html = re.sub(r"#(\w+)", r"<span style='color:#4a90e2;'>#\1</span>", html)
                self.preview_browser.setHtml(html)
                return
            except: pass
        # fallback plain
        esc = body.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        esc = re.sub(r"#(\w+)", r"<b style='color:#4a90e2;'>#\1</b>", esc)
        esc = re.sub(r"\[\[([^\]]+)\]\]", r"<b style='color:#2e7d32;'>[[\1]]</b>", esc)
        esc = esc.replace("\n","<br>")
        self.preview_browser.setHtml(f"<h2>{title}</h2><div style='line-height:1.6;'>{esc}</div>")

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
            self.statusBar().showMessage("Secci\u00f3n Notas \u2022 editor activo \u2022 F11 maximizar", 3000)
        elif idx == 1:
            self.statusBar().showMessage("Secci\u00f3n Calendario \u2022 Mes/Semana \u2022 doble click crea evento", 3000)
            self.refresh_calendar()
            if hasattr(self, 'week_table'):
                self.refresh_week()
        elif idx == 2:
            self.statusBar().showMessage("Secci\u00f3n Tareas \u2022 due/prio \u2022 doble click completa", 3000)
            self.refresh_tasks()
        elif idx == 3:
            self.statusBar().showMessage("Secci\u00f3n Grafo \u2022 arrastra nodos, click navega", 3000)
            self.refresh_graph_page()

    def switch_cal_view(self, idx):
        self.cal_stack.setCurrentIndex(idx)
        self.btn_view_month.setChecked(idx==0)
        self.btn_view_week.setChecked(idx==1)
        if idx==1:
            self.refresh_week()

    def refresh_week(self):
        # Semana del selected_date: lunes a domingo
        if not hasattr(self, 'week_table'):
            return
        # lunes de la semana
        dt = self.selected_date
        wd = dt.weekday()  # 0 lunes
        mon = dt - timedelta(days=wd)
        # limpiar
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
                # colorear
                it = self.week_table.item(h,col)
                it.setBackground(QColor("#e3f2fd"))
        con.close()
        # header con fecha
        for c in range(7):
            d = mon + timedelta(days=c)
            self.week_table.horizontalHeaderItem(c).setText(d.strftime("%a %d"))

    def on_week_cell(self, row, col):
        dt = self.selected_date
        wd = dt.weekday()
        mon = dt - timedelta(days=wd)
        day = mon + timedelta(days=col)
        hora = f"{row:02d}:00"
        ok = QMessageBox.question(self, "Nuevo evento", f"\u00bfCrear evento el {day.strftime('%Y-%m-%d')} a las {hora}?")
        if ok != QMessageBox.Yes:
            return
        title, ok2 = QInputDialog.getText(self, "T\u00edtulo", "T\u00edtulo del evento:")
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
        # limpiar anterior
        # quitar placeholder y contenedor previo
        # crear GraphView embebido
        # buscar y limpiar layout contenedor
        while self.graph_container.count():
            item=self.graph_container.takeAt(0)
            w=item.widget()
            if w: w.deleteLater()
        self.graph_placeholder.setVisible(False)
        con=db(); cur=con.cursor(); cur.execute("SELECT id,title,body FROM notes"); rows=cur.fetchall()
        # filtrar por tag si filtro
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
        hint=QLabel(f"Grafo filtrado: {len(nodes)} nodos, {len(edges)} enlaces \u2014 filtro '{filt}'" if filt else f"Grafo: {len(nodes)} nodos, {len(edges)} enlaces", self); hint.setStyleSheet("color:#666; font-size:11px;")
        self.graph_container.addWidget(hint)

    def _apply_theme(self):
        # detect dark via palette (Qt6 compat)
        try:
            bg = self.palette().color(self.palette().Window).lightness()
        except:
            try:
                bg = self.palette().color(QPalette.Window).lightness()
            except:
                bg = 255
        is_dark = bg < 128
        # Paleta base editor respirable
        if is_dark:
            editor_bg = "#1e1e1e"; editor_fg = "#e0e0e0"
        else:
            editor_bg = "#fffef8"; editor_fg = "#1a1a1a"
        # Hoja de estilo global - desapiñuscar: más aire, padding generoso
        self.setStyleSheet(f"""
            QMainWindow {{ font-size: 11pt; }}
            QLabel {{ padding: 4px 6px; font-size: 10.5pt; }}
            QLineEdit {{ padding: 8px 10px; font-size: 11pt; border: 1px solid #d0d7de; border-radius: 8px; }}
            QLineEdit:focus {{ border: 1.5px solid #4a90e2; }}
            QPushButton {{ padding: 8px 14px; font-size: 10.5pt; border-radius: 8px; margin: 2px; }}
            QPushButton:hover {{ background: #eef2ff; }}
            QListWidget {{ font-size: 11pt; border: 1px solid #e1e4e8; border-radius: 8px; padding: 4px; }}
            QListWidget::item {{ padding: 10px 14px; margin: 3px 4px; border-radius: 6px; line-height: 1.4; }}
            QListWidget::item:selected {{ background: #e3f2fd; color: #0d47a1; border: none; }}
            QListWidget::item:alternate {{ background: #f6f8fa; }}
            QCalendarWidget QToolButton {{ padding: 8px; margin: 2px; }}
            QCalendarWidget QWidget {{ alternate-background-color: #f6f8fa; }}
            QTextEdit {{ background: {editor_bg}; color: {editor_fg}; padding: 16px; font-size: 11pt; line-height: 1.6; border: 1px solid #d0d7de; border-radius: 10px; }}
            QTextBrowser {{ padding: 16px; font-size: 11pt; }}
            QToolButton {{ padding: 8px; margin: 2px; border-radius: 8px; }}
            QToolBar {{ spacing: 10px; padding: 6px; }}
            QTableWidget {{ gridline-color: #e1e4e8; selection-background-color: #e3f2fd; }}
            QTableWidget::item {{ padding: 6px; }}
            QHeaderView::section {{ padding: 6px 8px; background: #f6f8fa; border: none; border-bottom: 1px solid #e1e4e8; }}
        """)
        self.text_edit.setStyleSheet(self.text_edit.styleSheet() + f"QTextEdit {{ background:{editor_bg}; color:{editor_fg}; padding:16px; }}")
        self.preview_browser.setStyleSheet(f"QTextBrowser {{ background:#fcfcfc; padding:16px; border:1px solid #e1e4e8; border-radius:10px; }}")

    def _load_settings(self):
        s = QSettings("gnote-calendar", "gnote-qt")
        geom = s.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        state = s.value("windowState")
        if state:
            self.restoreState(state)
        idx = s.value("section", 0)
        try:
            self.switch_section(int(idx))
        except: pass
        preview = s.value("preview", False)
        if preview in (True, "true", 1, "1"):
            self.btn_preview.setChecked(True)
            self.toggle_preview(True)

    def closeEvent(self, e):
        s = QSettings("gnote-calendar", "gnote-qt")
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())
        s.setValue("section", self._current_section)
        s.setValue("preview", self.btn_preview.isChecked() if hasattr(self, 'btn_preview') else False)
        super().closeEvent(e)

    def _setup_tray(self):
        # Fase 5: QSystemTrayIcon para notificaciones 15min, fallback notify-send
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray = QSystemTrayIcon(self)
                # usar icono del sistema o pixmap simple
                try:
                    self.tray.setIcon(QIcon.fromTheme("gnote-calendar"))
                except: pass
                if self.tray.icon().isNull():
                    # fallback pixmap azul
                    from PySide6.QtGui import QPixmap
                    pm = QPixmap(16,16); pm.fill(QColor("#4a90e2"))
                    self.tray.setIcon(QIcon(pm))
                menu = QMenu(self)
                for txt, cb in [("Mostrar", self.show), ("Nueva nota", self.new_note), ("Pomodoro", self.open_pomodoro), ("Salir", self.close)]:
                    a = QAction(txt, self); a.triggered.connect(cb); menu.addAction(a)
                self.tray.setContextMenu(menu)
                self.tray.setToolTip("gnote-calendar - Knowledge OS")
                self.tray.show()
                self.tray.activated.connect(lambda r: self.show() if r==QSystemTrayIcon.DoubleClick else None)
            else:
                self.tray = None
        except:
            self.tray = None

    def _setup_accessibility(self):
        # Fase 5: a11y setAccessibleName, escalado, high-contrast toggle
        try:
            self.search_entry.setAccessibleName("Buscar notas")
            self.search_entry.setAccessibleDescription("Filtra por tag:, fecha:hoy/semana, texto. Esc para limpiar")
            self.title_entry.setAccessibleName("Título de la nota")
            self.text_edit.setAccessibleName("Editor de nota")
            self.text_edit.setAccessibleDescription("Markdown, #tag, [[enlace]], - [ ] tarea. Ctrl+S guarda")
            self.notes_list.setAccessibleName("Lista de notas")
            self.task_list.setAccessibleName("Lista de tareas")
            self.calendar.setAccessibleName("Calendario mensual")
            self.week_table.setAccessibleName("Vista semanal")
            # high-contrast action
            act_hc = QAction("Alto contraste", self); act_hc.setCheckable(True)
            act_hc.setShortcut(QKeySequence("Ctrl+H"))
            act_hc.toggled.connect(self.toggle_high_contrast)
            self.addAction(act_hc)
            # añadir a menú Ver
            for m in self.menuBar().findChildren(QMenu):
                if m.title()=="&Ver":
                    m.addAction(act_hc)
                    break
        except: pass

    def toggle_high_contrast(self, checked):
        if checked:
            self.setStyleSheet(self.styleSheet() + """
                QMainWindow { background: #000; color: #fff; }
                QListWidget::item:selected { background: #ffff00; color: #000; border: 2px solid #000; }
                QTextEdit { background: #000; color: #fff; border: 2px solid #fff; }
                QPushButton { background: #fff; color: #000; border: 2px solid #000; }
            """)
            self.statusBar().showMessage("Alto contraste activado (Ctrl+H para desactivar)", 3000)
        else:
            self._apply_theme()
            self.statusBar().showMessage("Alto contraste desactivado", 2000)

    def notify_event(self, title, body):
        # Fase 5: notifica via tray o notify-send
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
        # also poll fallback every 5s
        self._fs_timer = QTimer(self); self._fs_timer.timeout.connect(self.auto_folder_sync); self._fs_timer.start(5000)

    def _on_fs_changed(self):
        # debounce
        QTimer.singleShot(800, self._do_sync_and_refresh)

    def _do_sync_and_refresh(self):
        folder = get_sync_folder()
        if os.path.isdir(folder) and os.path.exists(BIN_PATH):
            try:
                r = subprocess.run([BIN_PATH, "sync", "--folder", folder], capture_output=True, text=True, timeout=4)
                if r.stdout and ("Importados" in r.stdout or "Exportados" in r.stdout):
                    if any(c.isdigit() and int(c)>0 for c in r.stdout if c.isdigit()):
                        self.refresh_notes(); self.refresh_tasks(); self.refresh_tag_cloud()
            except: pass

    # Calendar
    def refresh_calendar(self):
        dt = self.selected_date
        self.cal_label.setText(f"{calendar.month_name[dt.month]} {dt.year}")
        # set calendar to selected month
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
        # keep day valid
        last = calendar.monthrange(y,m)[1]
        d=min(self.selected_date.day, last)
        self.selected_date = self.selected_date.replace(year=y, month=m, day=d)
        self.refresh_calendar()
    def go_today(self): self.selected_date=datetime.now(); self.refresh_calendar()

    def refresh_tag_cloud(self):
        # clear
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
            b=QPushButton(f"#{t}", self); b.setFlat(True); b.setStyleSheet("color:#4a90e2; font-size:11px;")
            b.clicked.connect(lambda _, t=t: self.search_entry.setText(f"#{t}"))
            self.tag_cloud.addWidget(b)
        self.tag_cloud.addStretch()

    def refresh_notes(self):
        q=self.search_entry.text().strip() if hasattr(self,'search_entry') else ""
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
        else:
            cur.execute("SELECT id,title,body,updated_at FROM notes ORDER BY updated_at DESC LIMIT 100"); rows=cur.fetchall()
            if fecha:
                if fecha=="hoy": rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date()==date.today()]
                elif fecha=="semana":
                    cutoff=date.today()-timedelta(days=7)
                    rows=[r for r in rows if datetime.fromtimestamp(r["updated_at"]).date() >= cutoff]
        con.close()
        self.notes_list.clear()
        self._note_rows = rows
        for r in rows:
            ts=datetime.fromtimestamp(r["updated_at"]).strftime("%m-%d %H:%M")
            pend=r["body"].count("- [ ]")
            suffix=f"  \u2610{pend}" if pend else ""
            item = QListWidgetItem(f"{r['id']:>3}  {r['title'][:44]}{suffix}  \u00b7 {ts}")
            item.setData(Qt.UserRole, r["id"])
            self.notes_list.addItem(item)
        self.statusBar().showMessage(f"{len(rows)} notas" + (f" \u2022 filtro: {q}" if q else ""), 3000)
        # highlight
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
        self.highlighter.setQuery(self.search_entry.text())
        back = f" \u2022 enlazada por #{', #'.join(linked)}" if linked else ""
        self.statusBar().showMessage(f"Nota #{nid} \u2022 {len(re.findall(r'#(\w+)', r['body']+r['title']))} tags{back}", 4000)

    def new_note(self):
        idx=self.template_combo.currentIndex()
        keys=list(TEMPLATES.keys())
        tmpl_key=keys[idx] if 0 <= idx < len(keys) else "Diario"
        tmpl=TEMPLATES.get(tmpl_key, "")
        title_base=self.selected_date.strftime("%Y-%m-%d")
        body=tmpl.format(date=self.selected_date.strftime("%Y-%m-%d"), title=title_base)
        title=title_base
        if tmpl_key!="Diario":
            title, ok = QInputDialog.getText(self, "Nueva nota", f"T\u00edtulo ({tmpl_key}):", text=title_base)
            if not ok or not title.strip(): title=title_base
            # replace title placeholder if any
            if "{title}" not in tmpl:
                body = tmpl.format(date=self.selected_date.strftime("%Y-%m-%d"), title=title) if "{title}" in tmpl else body
            else:
                body = body.replace("{title}", title)
        con=db(); cur=con.cursor(); now=int(time.time())
        cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (title, body, now, now))
        nid=cur.lastrowid
        try:
            for m in re.findall(r"\[\[([^\]]+)\]\]", body):
                cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (nid, m.strip()))
        except: pass
        con.commit(); con.close()
        self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
        # select new
        for i in range(self.notes_list.count()):
            if self.notes_list.item(i).data(Qt.UserRole)==nid:
                self.notes_list.setCurrentRow(i)
                self.on_select_note(self.notes_list.item(i))
                break
        self.statusBar().showMessage(f"Nota creada #{nid}", 3000)

    def save_note(self):
        title=self.title_entry.text()
        body=self.text_edit.toPlainText().strip()
        if not self.current_note_id:
            if not title.strip() and not body:
                QMessageBox.information(self, "Guardar", "Nada que guardar"); return
            con=db(); cur=con.cursor(); now=int(time.time())
            cur.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)", (title or "Sin t\u00edtulo", body, now, now))
            self.current_note_id=cur.lastrowid
            try:
                for m in re.findall(r"\[\[([^\]]+)\]\]", body):
                    cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (self.current_note_id, m.strip()))
            except: pass
            con.commit(); con.close()
            self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
            self.statusBar().showMessage(f"Nota creada #{self.current_note_id}", 3000); return
        con=db(); cur=con.cursor(); now=int(time.time())
        cur.execute("UPDATE notes SET title=?, body=?, updated_at=? WHERE id=?", (title, body, now, self.current_note_id))
        tags=re.findall(r"#(\w+)", title+" "+body)
        cur.execute("DELETE FROM note_tags WHERE note_id=?", (self.current_note_id,))
        for t in tags:
            cur.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (t,))
            cur.execute("SELECT id FROM tags WHERE name=?", (t,)); tid=cur.fetchone()[0]
            cur.execute("INSERT OR IGNORE INTO note_tags(note_id,tag_id) VALUES(?,?)", (self.current_note_id, tid))
        cur.execute("DELETE FROM backlinks WHERE src_id=?", (self.current_note_id,))
        for m in re.findall(r"\[\[([^\]]+)\]\]", body):
            cur.execute("INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", (self.current_note_id, m.strip()))
        con.commit(); con.close()
        self.refresh_notes(); self.refresh_tag_cloud(); self.refresh_tasks()
        self.statusBar().showMessage(f"Guardado #{self.current_note_id} \u2713", 3000)

    def delete_note(self):
        if not self.current_note_id: return
        if QMessageBox.question(self, "Borrar", f"\u00bfBorrar nota #{self.current_note_id}?") != QMessageBox.Yes: return
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
            self.statusBar().showMessage("Tarea toggled \u2014 Ctrl+S para guardar", 3000)
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
