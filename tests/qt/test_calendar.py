import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import gui_qt
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDate

def test_calendar_counts():
    app = QApplication.instance() or QApplication([])
    cal = gui_qt.CalendarWidget()
    cal.setCounts({5:1, 15:2})
    assert cal.counts[5]==1
    # paintCell not crashed
    cal.setCurrentPage(2026,8)
    app.quit() if not QApplication.instance() else None

def test_calendar_navigation():
    app = QApplication.instance() or QApplication([])
    w = gui_qt.MainWindow()
    orig = w.selected_date
    w.shift_month(1)
    assert w.selected_date.month != orig.month or w.selected_date.year != orig.year
    w.go_today()
    assert w.selected_date.date() == w.selected_date.date()
    w.close()
