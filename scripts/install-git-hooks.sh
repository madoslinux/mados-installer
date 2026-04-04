#!/bin/bash
set -euo pipefail

PRECOMMIT_BIN=""

if command -v pre-commit >/dev/null 2>&1; then
    PRECOMMIT_BIN="pre-commit"
else
    VENV_DIR=".venv-hooks"
    echo "pre-commit not found globally; creating local venv at ${VENV_DIR}"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
    "$VENV_DIR/bin/python" -m pip install pre-commit >/dev/null
    PRECOMMIT_BIN="$VENV_DIR/bin/pre-commit"
fi

"$PRECOMMIT_BIN" install --hook-type pre-commit --hook-type pre-push

echo "Git hooks installed: pre-commit, pre-push"
echo "You can run all checks manually with: $PRECOMMIT_BIN run --all-files"
