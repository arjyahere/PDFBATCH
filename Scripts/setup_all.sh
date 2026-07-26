#!/usr/bin/env bash
# Interactive project setup CLI for macOS / Linux (and Git Bash).
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND="$ROOT/batch_highlighter_api_integrated"
FRONTEND="$ROOT/flutter_frontend"
VENV="$BACKEND/.venv"
PROMPT_TIMEOUT="${PROMPT_TIMEOUT:-20}"
FAILED=0

printf '============================================================\n'
printf '                    PROJECT SETUP CLI\n'
printf '============================================================\n'
printf '  Root     : %s\n' "$ROOT"
printf '  Backend  : %s\n' "$BACKEND"
printf '  Frontend : %s\n' "$FRONTEND"
printf '\n'
printf '  Prompts auto-continue in %ss with the default choice.\n' "$PROMPT_TIMEOUT"
printf '\n'

if [ ! -f "$BACKEND/requirements.txt" ]; then
    printf '  [ERROR] requirements.txt not found in %s\n' "$BACKEND"
    sleep 8
    exit 1
fi
if [ ! -f "$FRONTEND/pubspec.yaml" ]; then
    printf '  [ERROR] pubspec.yaml not found in %s\n' "$FRONTEND"
    sleep 8
    exit 1
fi

PY_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PY_CMD=python3
elif command -v python >/dev/null 2>&1; then
    PY_CMD=python
fi
if [ -z "$PY_CMD" ]; then
    printf '  [ERROR] Python not found on PATH\n'
    sleep 8
    exit 1
fi

FLUTTER_CMD=""
if [ -n "${FLUTTER_ROOT:-}" ] && [ -x "$FLUTTER_ROOT/bin/flutter" ]; then
    FLUTTER_CMD="$FLUTTER_ROOT/bin/flutter"
fi
if [ -z "$FLUTTER_CMD" ]; then
    FLUTTER_CMD="$(command -v flutter 2>/dev/null || true)"
fi
if [ -z "$FLUTTER_CMD" ]; then
    for candidate in \
        "$HOME/flutter/bin/flutter" \
        "$HOME/development/flutter/bin/flutter" \
        "/opt/flutter/bin/flutter" \
        "/usr/local/flutter/bin/flutter" \
        "/usr/lib/flutter/bin/flutter" \
        "$ROOT/flutter/bin/flutter"; do
        if [ -x "$candidate" ]; then
            FLUTTER_CMD="$candidate"
            break
        fi
    done
fi

VENV_PY=""
for candidate in "$VENV/bin/python" "$VENV/Scripts/python.exe"; do
    if [ -x "$candidate" ]; then
        VENV_PY="$candidate"
        break
    fi
done

printf '  Detected Python : %s\n' "$PY_CMD"
if [ -n "$FLUTTER_CMD" ]; then
    printf '  Detected Flutter: %s\n' "$FLUTTER_CMD"
else
    printf '  Detected Flutter: NOT FOUND - steps 3 and 4 cannot run\n'
fi
printf '\n'
printf '  Setup steps:\n'
printf '    1. Create Python virtual environment (.venv)\n'
printf '    2. Install Python requirements (pip)\n'
printf '    3. Fetch Flutter packages (flutter pub get)\n'
printf '    4. Build Flutter web (flutter build web)\n'
printf '\n'

ask() {
    ANSWER=""
    read -r -n 1 -t "$PROMPT_TIMEOUT" -p "$1" ANSWER 2>/dev/null || true
    printf '\n'
}

describe() {
    case "$1" in
        1) printf '  Step 1/4 : Create Python virtual environment\n' ;;
        2) printf '  Step 2/4 : Install Python dependencies from requirements.txt\n' ;;
        3) printf '  Step 3/4 : Fetch Flutter packages\n' ;;
        4) printf '  Step 4/4 : Build Flutter web bundle\n' ;;
    esac
    case "$1" in
        3|4) [ -z "$FLUTTER_CMD" ] && printf '             (Flutter SDK not found)\n' ;;
    esac
}

step1() {
    if [ -n "$VENV_PY" ]; then
        printf '  .venv already exists - nothing to do\n'
        return 0
    fi
    printf '  Creating .venv with %s ...\n' "$PY_CMD"
    if ! $PY_CMD -m venv "$VENV"; then
        printf '  [FAILED] Could not create .venv\n'
        return 1
    fi
    for candidate in "$VENV/bin/python" "$VENV/Scripts/python.exe"; do
        if [ -x "$candidate" ]; then
            VENV_PY="$candidate"
            break
        fi
    done
    printf '  [OK] .venv created\n'
}

step2() {
    if [ -z "$VENV_PY" ]; then
        printf '  [FAILED] .venv missing - run step 1 first\n'
        return 1
    fi
    printf '  Running pip install - this can take a few minutes ...\n'
    (cd "$BACKEND" && "$VENV_PY" -m pip install -r requirements.txt) || {
        printf '  [FAILED] pip install\n'
        return 1
    }
    printf '  [OK] Python dependencies installed\n'
}

step3() {
    if [ -z "$FLUTTER_CMD" ]; then
        printf '  [FAILED] Flutter SDK not found - set FLUTTER_ROOT or add flutter to PATH\n'
        return 1
    fi
    printf '  Running flutter pub get - this can take a few minutes ...\n'
    (cd "$FRONTEND" && "$FLUTTER_CMD" pub get) || {
        printf '  [FAILED] flutter pub get\n'
        return 1
    }
    printf '  [OK] Flutter packages fetched\n'
}

step4() {
    if [ -z "$FLUTTER_CMD" ]; then
        printf '  [FAILED] Flutter SDK not found - set FLUTTER_ROOT or add flutter to PATH\n'
        return 1
    fi
    printf '  Running flutter build web - this can take a few minutes ...\n'
    (cd "$FRONTEND" && "$FLUTTER_CMD" build web) || {
        printf '  [FAILED] flutter build web\n'
        return 1
    }
    printf '  [OK] Web build written to %s/build/web\n' "$FRONTEND"
}

for S in 1 2 3 4; do
    echo '------------------------------------------------------------'
    describe "$S"
    ask '  Action [Y]es / [N]o / [S]kip rest / [Q]uit : '
    case "$ANSWER" in
        q|Q)
            printf '  Aborted by user.\n'
            break
            ;;
        s|S)
            break
            ;;
        n|N)
            printf '  [SKIPPED]\n'
            ;;
        *)
            if ! step"$S"; then
                FAILED=1
                ask '  Step failed. [C]ontinue / [Q]uit : '
                case "$ANSWER" in
                    q|Q) printf '  Aborted by user.\n'; break ;;
                esac
            fi
            ;;
    esac
done

printf '============================================================\n'
if [ "$FAILED" -eq 1 ]; then
    printf '  SETUP FINISHED WITH ERRORS\n'
else
    printf '  SETUP COMPLETE\n'
fi
printf '  Backend venv : %s\n' "$VENV"
printf '  Web build    : %s/build/web\n' "$FRONTEND"
printf '  Start app    : Scripts/start.bat (Windows)\n'
printf '============================================================\n'
printf '  Closing in 8 seconds ...\n'
sleep 8
