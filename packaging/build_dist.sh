#!/bin/bash
# build_dist.sh - Genera .deb y tar.gz portable para gnote-calendar 2.0.0 Qt
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION=$(grep -m1 "Version:" "$ROOT/packaging/control" | awk '{print $2}')
ARCH="amd64"
DIST="$ROOT/dist"
BUILD="$ROOT/build"

echo "=== gnote-calendar dist builder v$VERSION ==="

# Asegurar binario
if [ ! -f "$BUILD/gnote-calendar" ]; then
  echo "Compilando..."
  make -C "$ROOT" -j1
fi
make -C "$ROOT" test

# Preparar staging .deb
STAGE=$(mktemp -d)
trap "rm -rf $STAGE" EXIT
mkdir -p "$STAGE/DEBIAN"
mkdir -p "$STAGE/usr/bin"
mkdir -p "$STAGE/usr/share/gnote-calendar/data"
mkdir -p "$STAGE/usr/share/applications"
mkdir -p "$STAGE/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$STAGE/usr/share/man/man1"
mkdir -p "$STAGE/usr/share/doc/gnote-calendar"

cp "$BUILD/gnote-calendar" "$STAGE/usr/bin/gnote-calendar"
chmod 755 "$STAGE/usr/bin/gnote-calendar"
cp "$ROOT/gui_qt.py" "$ROOT/gui.py" "$STAGE/usr/share/gnote-calendar/"
if [ -f "$ROOT/legacy/gui_gtk4.py" ]; then cp "$ROOT/legacy/gui_gtk4.py" "$STAGE/usr/share/gnote-calendar/gui_gtk4.py" 2>/dev/null || true; fi
cp -r "$ROOT/data/schema.sql" "$STAGE/usr/share/gnote-calendar/data/" 2>/dev/null || true
cp "$ROOT/requirements.txt" "$STAGE/usr/share/gnote-calendar/" 2>/dev/null || true
cp "$ROOT/packaging/gnote-calendar.desktop" "$STAGE/usr/share/applications/"
cp "$ROOT/packaging/gnote-calendar.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/"
cp "$ROOT/README.md" "$STAGE/usr/share/doc/gnote-calendar/" 2>/dev/null || true
cp "$ROOT/plan_accion.md" "$STAGE/usr/share/doc/gnote-calendar/" 2>/dev/null || true

# man
if [ -f "$ROOT/packaging/gnote-calendar.1" ]; then
  gzip -9c "$ROOT/packaging/gnote-calendar.1" > "$STAGE/usr/share/man/man1/gnote-calendar.1.gz"
fi

# control
cp "$ROOT/packaging/control" "$STAGE/DEBIAN/control"
echo "Installed-Size: $(du -sk "$STAGE/usr" | cut -f1)" >> "$STAGE/DEBIAN/control"
# postinst para update-desktop-database
cat > "$STAGE/DEBIAN/postinst" <<'POST'
#!/bin/bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then update-desktop-database /usr/share/applications 2>/dev/null || true; fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true; fi
POST
chmod 755 "$STAGE/DEBIAN/postinst"

mkdir -p "$DIST"
DEB="$DIST/gnote-calendar_${VERSION}_${ARCH}.deb"
dpkg-deb --build "$STAGE" "$DEB"
echo "✓ .deb: $DEB ($(du -h "$DEB" | cut -f1))"

# Portable tar.gz (ligero, solo binario + gui, sin obj)
PORTABLE="$DIST/gnote-calendar_${VERSION}_portable.tar.gz"
STAGE2=$(mktemp -d)
trap "rm -rf $STAGE $STAGE2" EXIT
mkdir -p "$STAGE2/gnote-calendar/build"
cp -a "$STAGE/usr" "$STAGE2/gnote-calendar/"
cp -a "$ROOT/gui_qt.py" "$ROOT/gui.py" "$STAGE2/gnote-calendar/" 2>/dev/null || true
if [ -f "$ROOT/legacy/gui_gtk4.py" ]; then cp "$ROOT/legacy/gui_gtk4.py" "$STAGE2/gnote-calendar/" 2>/dev/null || true; fi
cp -a "$BUILD/gnote-calendar" "$STAGE2/gnote-calendar/build/" 2>/dev/null || true
cp -a "$ROOT/data" "$STAGE2/gnote-calendar/" 2>/dev/null || true
cp "$ROOT/README.md" "$STAGE2/gnote-calendar/" 2>/dev/null || true
cp "$ROOT/install.sh" "$STAGE2/gnote-calendar/" 2>/dev/null || true
cp "$ROOT/requirements.txt" "$STAGE2/gnote-calendar/" 2>/dev/null || true
tar -czf "$PORTABLE" -C "$STAGE2" gnote-calendar
echo "✓ portable: $PORTABLE ($(du -h "$PORTABLE" | cut -f1))"

# AppImage stub actualizado Qt
APPIMG="$DIST/gnote-calendar.AppImage"
cat > "$APPIMG" <<'APP'
#!/bin/bash
# AppImage stub Qt - gnote-calendar 2.0.0
DIR="$(dirname "$(readlink -f "$0")")"
# Si estamos dentro de AppDir portable
if [ -f "$DIR/gnote-calendar/build/gnote-calendar" ]; then
  exec python3 "$DIR/gnote-calendar/gui_qt.py" "$@"
elif [ -f "/usr/share/gnote-calendar/gui_qt.py" ]; then
  exec python3 /usr/share/gnote-calendar/gui_qt.py "$@"
elif [ -f "./gui_qt.py" ]; then
  exec python3 ./gui_qt.py "$@"
else
  exec python3 /usr/local/share/gnote-calendar/gui_qt.py "$@" 2>/dev/null || python3 ./gui.py "$@"
fi
APP
chmod +x "$APPIMG"
echo "✓ AppImage stub: $APPIMG"

echo ""
echo "=== Verifica ==="
ls -lh "$DIST" | grep "$VERSION"
echo ""
echo "Instala .deb: sudo dpkg -i $DEB"
echo "Portable: tar -xzf $PORTABLE && ./gnote-calendar/build/gnote-calendar --help"
