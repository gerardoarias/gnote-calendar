import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import gui_qt
from PySide6.QtWidgets import QApplication

def test_markdown_preview():
    app = QApplication.instance() or QApplication([])
    w = gui_qt.MainWindow()
    w.title_entry.setText("Test Title")
    w.text_edit.setPlainText("# Hello\n[[link]] #tag due:2026-08-23")
    w.btn_preview.setChecked(True)
    w.toggle_preview(True)
    # offscreen isVisible may be False, but html should still be set
    plain = w.preview_browser.toPlainText()
    assert "Hello" in plain or "Test Title" in plain
    w.toggle_preview(False)
    w.close()

def test_markdown_fallback():
    app = QApplication.instance() or QApplication([])
    w = gui_qt.MainWindow()
    w.title_entry.setText("A")
    w.text_edit.setPlainText("plain **bold** #test")
    w.update_preview()
    assert len(w.preview_browser.toHtml()) > 0
    w.close()
