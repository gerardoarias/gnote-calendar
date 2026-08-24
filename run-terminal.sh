#!/bin/bash
# Lanzador para gnote-calendar (CLI) - mantiene terminal abierta
DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$DIR/build/gnote-calendar"
if [ ! -x "$BIN" ]; then
  echo "Error: no se encontró $BIN"
  echo "Compila con: make -j1"
  read -p "Presiona Enter para cerrar..."
  exit 1
fi
echo "=== gnote-calendar ==="
echo "DB: $HOME/.local/share/gnote-calendar/notes.db"
echo ""
"$BIN" note list 2>&1 | head -20
echo ""
echo "Comandos disponibles:"
echo "  $BIN note add \"Titulo\" \"Cuerpo\""
echo "  $BIN event list"
echo "  $BIN ics export --output /tmp/cal.ics"
echo "  $BIN --help"
echo ""
# Si se lanzó sin argumentos, abrir shell interactiva dentro del contexto
if [ -t 0 ]; then
  exec bash --init-file <(echo "PS1='gnote> '; alias gnote=\"$BIN\"; echo 'Escribe: gnote --help  (o note list, event list)'; echo ''")
else
  read -p "Presiona Enter para cerrar..."
fi
