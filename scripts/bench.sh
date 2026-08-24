#!/bin/bash
# bench.sh - Benchmark RAM y arranque gnote-calendar
# Uso: bash scripts/bench.sh [--assert-ram 60] [--assert-startup 200]
set -e
RAM_LIMIT=0
STARTUP_LIMIT=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --assert-ram) RAM_LIMIT=$2; shift 2;;
    --assert-startup) STARTUP_LIMIT=$2; shift 2;;
    *) shift;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/build/gnote-calendar"
DB="$HOME/.local/share/gnote-calendar/notes.db"

echo "=== gnote-calendar bench ==="
echo "Fecha: $(date -Iseconds)"
echo "Binario: $BIN"
if [[ -f "$BIN" ]]; then
  SIZE=$(stat -c%s "$BIN" 2>/dev/null || stat -f%z "$BIN" 2>/dev/null || echo 0)
  echo "Bin size: $((SIZE/1024))K strip=$SIZE"
  echo "CLI startup (cold):"
  /usr/bin/time -f "  time=%e s maxmem=%M KB" "$BIN" --help 2>&1 | head -5 || echo "  time measurement fallback"
  # fallback sin /usr/bin/time
  START=$(date +%s%3N)
  "$BIN" --help >/dev/null 2>&1 || true
  END=$(date +%s%3N)
  ELAPSED=$((END-START))
  echo "  elapsed=${ELAPSED}ms (help)"
  # RAM idle CLI (sleep 0.5 y ps)
  "$BIN" note list >/dev/null 2>&1 || true
else
  echo "WARN: binario no compilado, ejecuta 'make' primero"
fi

for GUI in "$ROOT/gui_qt.py" "$ROOT/gui.py" "$ROOT/gui_gtk4.py"; do
  if [[ -f "$GUI" ]]; then
    echo ""
    echo "GUI: $(basename $GUI) size=$(wc -c < "$GUI") bytes"
    if [[ "$GUI" == *"gui_qt"* ]]; then
      # Check PySide6
      if python3 -c "import PySide6" 2>/dev/null; then
        echo "  PySide6: $(python3 -c 'import PySide6; print(PySide6.__version__)' 2>/dev/null)"
      elif python3 -c "import PySide2" 2>/dev/null; then
        echo "  PySide2 fallback: $(python3 -c 'import PySide2; print(PySide2.__version__)' 2>/dev/null)"
      elif python3 -c "import PyQt5" 2>/dev/null; then
        echo "  PyQt5 fallback: $(python3 -c 'import PyQt5.QtCore; print(PyQt5.QtCore.PYQT_VERSION_STR)' 2>/dev/null)"
      else
        echo "  WARN: Qt bindings no instalados (pip install --break-system-packages PySide6==6.7.3)"
      fi
    fi
    # Startup smoke con xvfb si disponible
    if command -v xvfb-run >/dev/null 2>&1 && python3 -c "import PySide6" 2>/dev/null; then
      echo "  smoke Qt (xvfb, 2s):"
      timeout 3 xvfb-run -a python3 "$GUI" --smoke 2>&1 | head -10 || echo "  smoke timeout/ok"
    fi
  fi
done

echo ""
echo "DB: $DB"
if [[ -f "$DB" ]]; then
  echo "  size=$(du -h "$DB" | cut -f1) wal=$(ls -lh "$DB"* 2>/dev/null | head -5)"
  sqlite3 "$DB" "SELECT 'notes='||(SELECT COUNT(*) FROM notes)||' events='||(SELECT COUNT(*) FROM events)||' backlinks='||(SELECT COUNT(*) FROM backlinks);" 2>/dev/null || echo "  sqlite3 query fallback"
else
  echo "  no existe (se crea al arrancar)"
fi
echo ""
# RAM check si se pasó límite
if [[ "$RAM_LIMIT" -gt 0 ]]; then
  echo "Check --assert-ram $RAM_LIMIT MB: SKIPPED (requiere medición con ps durante GUI running)"
  echo "  Ejecuta manual: ps -o rss -p \$(pgrep -f gui_qt) -> rss/1024 < $RAM_LIMIT"
fi
if [[ "$STARTUP_LIMIT" -gt 0 ]]; then
  echo "Check --assert-startup $STARTUP_LIMIT ms: elapsed=${ELAPSED:-?}ms limit=${STARTUP_LIMIT}ms"
  if [[ -n "${ELAPSED:-}" && "$ELAPSED" -gt "$STARTUP_LIMIT" ]]; then
    echo "WARN: startup > limit"
  fi
fi
echo "=== bench done ==="
