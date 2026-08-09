#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Read version from pyproject.toml
VERSION=$(
  python3 - <<'PY'
from pathlib import Path
text = Path("pyproject.toml").read_text(encoding="utf-8")
for line in text.splitlines():
    s = line.strip()
    if s.startswith("version") and "=" in s:
        val = s.split("=", 1)[1].strip().strip('"').strip("'")
        print(val)
        break
else:
    raise SystemExit("version not found in pyproject.toml")
PY
)

TAG="v${VERSION}"

echo "======================================"
echo " GranTED release helper"
echo " Version: $VERSION"
echo " Tag:     $TAG"
echo "======================================"
echo

if [[ -z "$VERSION" ]]; then
  echo "ERROR: could not read version from pyproject.toml"
  exit 1
fi

if [[ ! "$VERSION" =~ ^[0-9]+(\.[0-9]+)+$ ]]; then
  echo "ERROR: version '$VERSION' does not look numeric"
  exit 1
fi

echo "What do you want to do?"
echo "  1) Only upload changes to GitHub"
echo "  2) Upload changes to GitHub AND publish to PyPI"
echo
read -r -p "Choose [1/2]: " CHOICE
echo

# ---------- option 1 ----------
if [[ "$CHOICE" == "1" ]]; then
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Uncommitted changes:"
    git status --short
    echo
    read -r -p "Commit message: " COMMIT_MSG
    if [[ -z "$COMMIT_MSG" ]]; then
      echo "ERROR: empty commit message"
      exit 1
    fi
    git add -A
    git commit -m "$COMMIT_MSG"
  else
    echo "No local changes to commit."
  fi

  git push origin main
  echo
  echo "Done. GitHub updated."
  exit 0
fi

# ---------- option 2 ----------
if [[ "$CHOICE" != "2" ]]; then
  echo "Invalid choice."
  exit 1
fi

# Commit if needed
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Uncommitted changes:"
  git status --short
  echo
  read -r -p "Commit message [${VERSION} release]: " COMMIT_MSG
  COMMIT_MSG=${COMMIT_MSG:-"${VERSION} release"}
  git add -A
  git commit -m "$COMMIT_MSG"
fi

# Refuse existing tags
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "ERROR: local tag $TAG already exists. Bump version first."
  exit 1
fi

if git ls-remote --tags origin | grep -q "refs/tags/${TAG}$"; then
  echo "ERROR: remote tag $TAG already exists. Bump version first."
  exit 1
fi

# Clean old build artifacts (critical)
echo "Cleaning old build artifacts..."
rm -rf dist/ build/ *.egg-info src/*.egg-info src/granted.egg-info 2>/dev/null || true

# Build fresh package from current pyproject.toml
echo "Building package..."
python3 -m pip install --upgrade build twine >/dev/null
python3 -m build

echo "Built files:"
ls -l dist/

# Safety: ensure dist contains only this version
if ls dist | grep -v "${VERSION}" | grep -E '\.(whl|tar\.gz)$' >/dev/null; then
  echo "ERROR: dist/ contains files from another version:"
  ls dist/
  echo "Aborting upload."
  exit 1
fi

# Upload to PyPI from this script
echo "Uploading to PyPI..."
python3 -m twine upload dist/*

# Push code + tag to GitHub
echo "Pushing main and tag to GitHub..."
git push origin main
git tag "$TAG"
git push origin "$TAG"

echo
echo "Done."
echo "- PyPI:  granted==${VERSION}"
echo "- GitHub tag: ${TAG}"
echo "- tests/publish workflows may also run from the push/tag"
