#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Robust version read from pyproject.toml
VERSION=$(
  python3 - <<'PY'
from pathlib import Path
text = Path("pyproject.toml").read_text(encoding="utf-8")
for line in text.splitlines():
    s = line.strip()
    if s.startswith("version") and "=" in s:
        val = s.split("=", 1)[1].strip()
        val = val.strip().strip('"').strip("'")
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
echo "  1) Only upload changes to GitHub          → tests.yml"
echo "  2) Upload changes AND release to PyPI     → tests.yml + publish.yml"
echo
read -r -p "Choose [1/2]: " CHOICE
echo

# Commit anything pending
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Committing current changes..."
  git add -A
  git commit -m "Release ${VERSION}" || true
fi

case "$CHOICE" in
  1)
    echo "Pushing main..."
    git push origin main
    echo
    echo "Done."
    echo "Changes uploaded. tests.yml should run."
    ;;

  2)
    if git rev-parse "$TAG" >/dev/null 2>&1; then
      echo "ERROR: tag $TAG already exists locally."
      echo "Bump the version in pyproject.toml and try again."
      exit 1
    fi

    if git ls-remote --tags origin | grep -q "refs/tags/${TAG}$"; then
      echo "ERROR: tag $TAG already exists on GitHub."
      echo "Bump the version in pyproject.toml and try again."
      exit 1
    fi

    echo "Pushing main..."
    git push origin main

    echo "Creating and pushing tag ${TAG}..."
    git tag "$TAG"
    git push origin "$TAG"

    echo
    echo "Done."
    echo "- main pushed      → tests.yml"
    echo "- tag ${TAG} pushed → publish.yml → PyPI"
    echo
    echo "Watch: https://github.com/sgiani95/GranTED/actions"
    ;;

  *)
    echo "Invalid choice."
    exit 1
    ;;
esac
