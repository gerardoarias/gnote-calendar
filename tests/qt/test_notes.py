import os, sys, tempfile, sqlite3, time, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

def test_search_highlighter_query():
    # SearchHighlighter sin QApplication
    try:
        from gui_qt import SearchHighlighter
        from PySide6.QtGui import QTextDocument
    except ImportError:
        try:
            from PySide2.QtGui import QTextDocument
            from gui_qt import SearchHighlighter
        except:
            pytest.skip("Qt no instalado")
    # sólo API check sin crear QApplication headless?
    import pytest
    pytest.skip("requiere QApplication, skip en headless sin xvfb")
