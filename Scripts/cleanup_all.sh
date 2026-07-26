#!/usr/bin/env bash
# Remove generated artifacts but keep source, .git, and every input/ output/ folder.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND="$ROOT/batch_highlighter_api_integrated"
FRONTEND="$ROOT/flutter_frontend"
REMOVED=0

printf '============================================================\n'
printf '                      CLEANUP ALL\n'
printf '============================================================\n'
printf '  Root: %s\n\n' "$ROOT"
printf '  Removes generated artifacts:\n'
printf '    - Python venvs (.venv / venv)\n'
printf '    - __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, *.pyc\n'
printf '    - Flutter .dart_tool and build folders\n'
printf '    - logs folders and crash logs\n'
printf '    - temp, jobs, temp_*, *.db, *.sqlite, *.sqlite3\n\n'
printf '  PRESERVED: source code, .git, Scripts, Docs, and EVERY\n'
printf '             input/ and output/ folder anywhere in the repo.\n\n'

ANSWER=""
read -r -n 1 -t 20 -p "  Delete all generated artifacts? [Y]es / [N]o : " ANSWER 2>/dev/null || true
printf '\n'
case "$ANSWER" in
    y|Y) ;;
    *) printf '  Cancelled - nothing was deleted.\n'; sleep 5; exit 0 ;;
esac

is_protected() {
    case "$1" in
        */input/*|*/output/*) return 0 ;;
        *) return 1 ;;
    esac
}

remove_dir() {
    if [ -d "$1" ] && ! is_protected "$1"; then
        printf '  Removing %s\n' "$1"
        rm -rf "$1"
        REMOVED=$((REMOVED + 1))
    fi
}

remove_file() {
    if [ -f "$1" ] && ! is_protected "$1"; then
        printf '  Removing %s\n' "$1"
        rm -f "$1"
        REMOVED=$((REMOVED + 1))
    fi
}

printf '\n[1/6] Virtual environments\n'
for d in "$ROOT/.venv" "$ROOT/venv" "$BACKEND/.venv" "$BACKEND/venv"; do
    remove_dir "$d"
done

printf '[2/6] Python / tool caches\n'
while IFS= read -r -d '' d; do
    remove_dir "$d"
done < <(find "$ROOT" -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -print0 2>/dev/null)
while IFS= read -r -d '' f; do
    remove_file "$f"
done < <(find "$ROOT" -type f \( -name '*.pyc' -o -name '*.pyo' \) -print0 2>/dev/null)

printf '[3/6] Flutter build artifacts\n'
remove_dir "$FRONTEND/.dart_tool"
remove_dir "$FRONTEND/build"

printf '[4/6] Logs\n'
remove_dir "$ROOT/logs"
remove_dir "$BACKEND/logs"
while IFS= read -r -d '' f; do
    remove_file "$f"
done < <(find "$ROOT" -maxdepth 1 -type f \( -name 'hs_err_*.log' -o -name 'replay_*.log' \) -print0 2>/dev/null)

printf '[5/6] Runtime folders (temp / jobs)\n'
while IFS= read -r -d '' d; do
    remove_dir "$d"
done < <(find "$ROOT" -type d \( -name temp -o -name jobs -o -name 'temp_*' \) -print0 2>/dev/null)

printf '[6/6] Runtime databases\n'
while IFS= read -r -d '' f; do
    remove_file "$f"
done < <(find "$ROOT" -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) -print0 2>/dev/null)

printf '\n============================================================\n'
printf '  Removed %s folders/files\n' "$REMOVED"
printf '  Preserved: input/, output/, source code, .git\n'
printf '============================================================\n'
printf '  Closing in 8 seconds ...\n'
sleep 8
