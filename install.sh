#!/bin/bash
# install.sh - Instalador gnote-calendar Qt (PySide6) para Linux (2015+)
# No requiere sudo si instalas en $HOME/.local
set -e

PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
SHARE_DIR="$PREFIX/share/gnote-calendar"
APP_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/scalable/apps"

echo "=== gnote-calendar instalador v2.0 (Qt) ==="
echo "Prefijo: $PREFIX"

if [ ! -f "build/gnote-calendar" ]; then
  echo "Compilando (make)..."
  make -j1 2>&1 | tail -5
fi

echo "Instalando binario..."
mkdir -p "$BIN_DIR" "$SHARE_DIR" "$APP_DIR" "$ICON_DIR"
cp build/gnote-calendar "$BIN_DIR/gnote-calendar"
cp gui_qt.py gui.py "$SHARE_DIR/"
# legacy GTK4 opcional
if [ -f "gui_gtk4.py" ]; then cp gui_gtk4.py "$SHARE_DIR/" 2>/dev/null || true; fi
cp -r data "$SHARE_DIR/" 2>/dev/null || true
cp requirements.txt "$SHARE_DIR/" 2>/dev/null || true
cp packaging/gnote-calendar.svg "$ICON_DIR/gnote-calendar.svg" 2>/dev/null || true

# Detectar Qt (PySide6 > PySide2 > PyQt5)
QT_OK=0
QT_LIB=""
if python3 -c "import PySide6" 2>/dev/null; then
  QT_OK=1; QT_LIB="PySide6"
  echo "Qt detectado: PySide6 $(python3 -c 'import PySide6; print(PySide6.__version__)' 2>/dev/null) — instalando GUI Qt"
elif python3 -c "import PySide2" 2>/dev/null; then
  QT_OK=1; QT_LIB="PySide2"
  echo "Qt detectado: PySide2 — instalando GUI Qt (compat)"
elif python3 -c "import PyQt5" 2>/dev/null; then
  QT_OK=1; QT_LIB="PyQt5"
  echo "Qt detectado: PyQt5 — instalando GUI Qt (compat)"
else
  echo "Qt no detectado — se usará fallback Tk (gui.py)"
  echo "  Para Qt: pip install --break-system-packages PySide6==6.7.3"
  echo "  o apt install python3-pyqt5 (si no tienes pip)"
fi

# Desktop file con ruta correcta (elige Qt si disponible) - robusto a gui_qt.py ya en packaging
if [ "$QT_OK" = "1" ]; then
  sed -E "s|Exec=python3 .*/gui.*\.py|Exec=python3 $SHARE_DIR/gui_qt.py|" packaging/gnote-calendar.desktop > "$APP_DIR/gnote-calendar.desktop"
else
  sed -E "s|Exec=python3 .*/gui.*\.py|Exec=python3 $SHARE_DIR/gui.py|" packaging/gnote-calendar.desktop > "$APP_DIR/gnote-calendar.desktop"
fi
# Actualizar comentario en desktop para Qt
if [ "$QT_OK" = "1" ]; then
  sed -i "s|Comment=.*|Comment=Gestor ligero de notas y calendario - offline, <60MB RAM Qt ($QT_LIB), ICS Gmail|" "$APP_DIR/gnote-calendar.desktop" 2>/dev/null || true
fi

ln -sf "$BIN_DIR/gnote-calendar" "$BIN_DIR/gnote" 2>/dev/null || true

chmod +x "$BIN_DIR/gnote-calendar" "$SHARE_DIR/gui_qt.py" "$SHARE_DIR/gui.py" 2>/dev/null || true

echo "Actualizando cache..."
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true
fi

echo ""
echo "✓ Instalado en $PREFIX"
echo "  Binario: $BIN_DIR/gnote-calendar"
if [ "$QT_OK" = "1" ]; then echo "  GUI: $SHARE_DIR/gui_qt.py (Qt $QT_LIB)"; else echo "  GUI: $SHARE_DIR/gui.py (Tk fallback)"; fi
echo "  Lanzador: $APP_DIR/gnote-calendar.desktop"
echo ""
echo "Uso:"
echo "  gnote-calendar --help                 # CLI"
echo "  python3 $SHARE_DIR/gui_qt.py          # GUI Qt"
echo "  python3 $SHARE_DIR/gui.py             # GUI Tk fallback"
echo "  O busca 'gnote-calendar' en tu menú de aplicaciones"
echo ""
echo "DB: ~/.local/share/gnote-calendar/notes.db"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo ""
  echo "⚠ Añade a tu PATH: export PATH=\"\$PATH:$BIN_DIR\" >> ~/.bashrc"
fi
# bench hint
echo ""
echo "Verifica: bash $SHARE_DIR/../scripts/bench.sh 2>/dev/null || bash scripts/bench.sh"
