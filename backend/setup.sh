#!/usr/bin/env bash
# ============================================================
# DevOps Assistant — Backend Setup Script
# Creates Python 3.11 venv and installs requirements
# ============================================================
set -euo pipefail

PYTHON=${PYTHON:-python3.11}
VENV_DIR=".venv"

echo "🐍  Checking Python version..."
if ! command -v "$PYTHON" &>/dev/null; then
  echo "❌  $PYTHON not found. Install Python 3.11 first." >&2
  exit 1
fi

PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PY_VER" != "3.11" ]]; then
  echo "❌  Requires Python 3.11, got $PY_VER" >&2
  exit 1
fi

echo "✅  Python $PY_VER detected"

echo "📦  Creating virtual environment at $VENV_DIR ..."
"$PYTHON" -m venv "$VENV_DIR"

echo "⬆️   Upgrading pip ..."
"$VENV_DIR/bin/pip" install --upgrade pip

echo "📥  Installing requirements ..."
"$VENV_DIR/bin/pip" install -r requirements.txt

echo ""
echo "✅  Setup complete! Activate your venv with:"
echo "    source $VENV_DIR/bin/activate"
