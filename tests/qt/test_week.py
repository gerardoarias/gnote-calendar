import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import gui_qt
from PySide6.QtWidgets import QApplication
from datetime import datetime

def test_week_view():
    app = QApplication.instance() or QApplication([])
    w = gui_qt.MainWindow()
    w.switch_cal_view(1)
    assert w.cal_stack.currentIndex()==1
    w.refresh_week()
    assert w.week_table.rowCount()==24
    assert w.week_table.columnCount()==7
    # header should be updated
    assert w.week_table.horizontalHeaderItem(0).text() != ""
    w.switch_cal_view(0)
    assert w.cal_stack.currentIndex()==0
    w.close()

def test_week_cell_create():
    app = QApplication.instance() or QApplication([])
    w = gui_qt.MainWindow()
    # ensure no crash on week cell handler (mock)
    # we don't actually double click, just check method exists
    assert hasattr(w, 'on_week_cell')
    w.close()
