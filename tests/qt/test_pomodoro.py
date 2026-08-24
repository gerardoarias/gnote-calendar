import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import gui_qt
from PySide6.QtWidgets import QApplication

def test_pomodoro_timer():
    app = QApplication.instance() or QApplication([])
    dlg = gui_qt.PomodoroDialog()
    assert dlg.remaining == 25*60
    dlg.start()
    assert dlg.running == True
    dlg.tick()
    assert dlg.remaining == 25*60 -1
    dlg.pause()
    assert dlg.running == False
    dlg.reset()
    assert dlg.remaining == 25*60
    dlg.close()

def test_pomodoro_mode_switch():
    from unittest.mock import patch
    app = QApplication.instance() or QApplication([])
    dlg = gui_qt.PomodoroDialog()
    dlg.mode="work"
    dlg.remaining=1
    dlg.running=True
    with patch.object(gui_qt.QMessageBox, 'information', return_value=None):
        with patch('gui_qt.subprocess.run'):
            dlg.tick()  # should trigger switch to break without blocking
    assert dlg.mode in ("work","break")
    dlg.close()
