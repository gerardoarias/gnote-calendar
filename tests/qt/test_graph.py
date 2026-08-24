import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import gui_qt
from PySide6.QtWidgets import QApplication

def test_graph_build():
    app = QApplication.instance() or QApplication([])
    nodes=[{"id":1,"title":"A","x":100,"y":100,"vx":0,"vy":0},{"id":2,"title":"B","x":200,"y":200,"vx":0,"vy":0}]
    edges=[(0,1)]
    view = gui_qt.GraphView(nodes, edges, 1, lambda x: None)
    assert len(view.edge_items)==1
    assert len(view.items)==2
    # physics step
    view._physics()
    assert True
    view.close()

def test_graph_filter():
    app = QApplication.instance() or QApplication([])
    w = gui_qt.MainWindow()
    w.graph_filter.setText("test")
    w.refresh_graph_page()
    # should not crash, even if no nodes for filter
    assert w.graph_container.count() >= 0
    w.close()
