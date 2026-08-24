# Fase 7 — Publicación GitHub (gerardoarias)

**Repo objetivo:** `https://github.com/gerardoarias/gnote-calendar`
**Tag:** `v2.0.0` `Qt PySide6 Knowledge OS` `9388833`
**Branch:** `main`

## 1. Crear repo en GitHub (1 vez, web)

1. Abre https://github.com/new
2. Owner: `gerardoarias` — Repository name: `gnote-calendar`
3. Description: `Gestor ligero de notas y calendario offline <60MB Qt PySide6 — Knowledge OS con journal, backlinks, grafo, sync`
4. Visibility: **Public** (para Flathub requiere public)
5. **No** marques `Initialize with README` (ya tenemos `README.md:1`)
6. Click **Create repository** → copia URL `https://github.com/gerardoarias/gnote-calendar.git`

## 2. Push local → GitHub

Desde `/home/familia/Documents/sistema_contabilidad`:

```bash
cd /home/familia/Documents/sistema_contabilidad
git remote -v  # debe mostrar origin https://github.com/gerardoarias/gnote-calendar.git
git status     # clean, commit 9388833 Release v2.0.0

# Si creaste repo vacío sin README, push directo:
git push -u origin main
git push origin v2.0.0

# Si pide Username/Password → usa PAT (Settings → Developer settings → Personal access tokens → Tokens classic → Generate → repo)
# Usuario: gerardoarias, Password: pega PAT

# Alternativa SSH (recomendado, sin PAT):
git remote set-url origin git@github.com:gerardoarias/gnote-calendar.git
# añade tu ~/.ssh/id_ed25519.pub a https://github.com/settings/keys
git push -u origin main
git push origin v2.0.0
```

Verifica en https://github.com/gerardoarias/gnote-calendar → commits + tag `v2.0.0` + `dist/*.deb` + `flatpak/`.

## 3. Release GitHub v2.0.0 con artefactos

En https://github.com/gerardoarias/gnote-calendar/releases → **Draft a new release**:

- Tag: `v2.0.0` (selecciona existente)
- Title: `v2.0.0 Qt PySide6 — Knowledge OS`
- Description: copia `docs/CHANGELOG.md:2` `2.0.0` + `README.md:22` Features
- Adjunta artefactos `dist/`:
  - `gnote-calendar_2.0.0_amd64.deb` (700K)
  - `gnote-calendar_2.0.0_portable.tar.gz` (1.7M)
  - `gnote-calendar.AppImage` (stub)
  - `gnote-calendar.flatpak` (si generaste `flatpak build-bundle`)
- Publish

O via CLI con `gh` (si instalas `gh auth login`):

```bash
gh release create v2.0.0 dist/gnote-calendar_2.0.0_amd64.deb dist/gnote-calendar_2.0.0_portable.tar.gz --title "v2.0.0 Qt PySide6" --notes-file docs/CHANGELOG.md
```

## 4. Verificación post-push

```bash
git ls-remote origin  # debe listar main y v2.0.0
git log --oneline -3
flatpak install flathub org.kde.Sdk//6.9 -y # para OF en otro PC
```

## 5. Siguiente Fase 7 Flathub

Una vez en GitHub público, fork `flathub/flathub` y PR `io.github.gerardoarias.gnote-calendar` (ver `flatpak/io.github.gerardoarias.gnote-calendar.json:1` `6.9`).

## Scripts

- `scripts/push_github.sh` — automatiza push
- `scripts/release.sh` — crea tag y artefactos
