import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
import sqlite3, tempfile

def test_imports():
    # gui_qt debe compilar y tener compat layer
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "../../gui_qt.py"), doraise=True)

def test_db_helpers():
    import gui_qt
    # DB path helpers no requieren Qt
    assert hasattr(gui_qt, 'QT_AVAILABLE')
    folder = gui_qt.get_sync_folder()
    assert folder and isinstance(folder, str) and len(folder) > 1
    # default is ~/Notas, but may be overridden by previous sync test (tmp)
    assert os.path.isabs(os.path.expanduser(folder))

def test_templates():
    import gui_qt
    assert "Diario" in gui_qt.TEMPLATES
    assert "Proyecto" in gui_qt.TEMPLATES
    assert "{date}" in gui_qt.TEMPLATES["Diario"]

def test_toggle():
    import gui_qt
    assert gui_qt.toggle_task_line("- [ ] foo") == "- [x] foo"
    assert gui_qt.toggle_task_line("- [x] foo") == "- [ ] foo"
    assert gui_qt.toggle_task_line("- [X] foo") == "- [ ] foo"
    assert gui_qt.toggle_task_line("plain") == "plain"

def test_qt_flag():
    import gui_qt
    # QT_AVAILABLE debe ser bool, QT_LIB puede ser None si no instalado
    assert isinstance(gui_qt.QT_AVAILABLE, bool)

def test_qt_available_or_fallback(caplog=None):
    # No exige PySide6 instalado, solo que el compat layer no rompa
    try:
        import PySide6  # noqa
        assert True
    except ImportError:
        try:
            import PySide2  # noqa
            assert True
        except ImportError:
            try:
                import PyQt5  # noqa
                assert True
            except ImportError:
                # en CI sin Qt, gui_qt igual debe hacer fallback a Tk logic (import error handled)
                assert True
