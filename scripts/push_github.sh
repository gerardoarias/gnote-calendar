#!/bin/bash
# push_github.sh - Fase 7 GitHub gerardoarias/gnote-calendar
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "=== Fase 7 GitHub push ==="
echo "Remote: $(git remote get-url origin 2>/dev/null || echo 'no remote')"
echo "Repo: https://github.com/gerardoarias/gnote-calendar"
echo "Branch: $(git branch --show-current)"
echo "Tag: $(git tag --sort=-v:refname | head -3)"
echo ""
echo "1. Crea repo vacío en https://github.com/new -> gerardoarias/gnote-calendar (Public, sin README)"
echo "2. Luego ejecuta:"
echo "   git push -u origin main"
echo "   git push origin v2.0.0"
echo ""
read -p "¿Push ahora? (s/N) " ans
if [[ "$ans" =~ ^[sS] ]]; then
  git push -u origin main
  git push origin v2.0.0
  echo "✓ Push completado. Verifica https://github.com/gerardoarias/gnote-calendar"
else
  echo "Saltado. Ejecuta manualmente cuando crees el repo."
fi
