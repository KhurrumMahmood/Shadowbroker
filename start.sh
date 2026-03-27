#!/bin/bash
# =========================================================================
#   S H A D O W B R O K E R   —   Dev Environment Setup & Launcher
# =========================================================================
#
# Finds a working Node.js (tries nvm > fnm > volta > brew > system),
# caches the result, sets up Python venv + pip deps, installs frontend
# npm deps, checks for required/optional env vars, and starts the dev
# servers.
#
# Usage:
#   ./start.sh          # full setup + launch
#   ./start.sh --check  # setup + env check only, don't start servers
# =========================================================================

set -euo pipefail
cleanup() { kill 0 2>/dev/null; exit 0; }
trap cleanup SIGINT SIGTERM

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE_CACHE="$SCRIPT_DIR/.node-path"
CHECK_ONLY=false
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=true

# Minimum Node.js version (major)
MIN_NODE=18

echo "======================================================="
echo "   S H A D O W B R O K E R   —   macOS / Linux Setup   "
echo "======================================================="
echo ""

# -----------------------------------------------------------------
# Node.js Discovery
# -----------------------------------------------------------------
# Tries multiple sources in preference order. A candidate must:
#   1. Actually execute without errors (e.g. no broken dylibs)
#   2. Meet the minimum version requirement
#
# The winning node/npm paths are cached to .node-path so subsequent
# runs skip the search.
# -----------------------------------------------------------------

node_version_ok() {
    local node_bin="$1"
    local ver
    ver=$("$node_bin" --version 2>/dev/null) || return 1
    local major="${ver#v}"
    major="${major%%.*}"
    [[ "$major" -ge "$MIN_NODE" ]] 2>/dev/null
}

find_node() {
    # 1. Check cache first
    if [[ -f "$NODE_CACHE" ]]; then
        local cached
        cached=$(cat "$NODE_CACHE")
        if [[ -x "$cached" ]] && node_version_ok "$cached"; then
            echo "$cached"
            return 0
        fi
        # Cache is stale — remove and re-search
        rm -f "$NODE_CACHE"
    fi

    local candidates=()

    # 2. nvm — check common nvm dirs for all installed versions (newest first)
    local nvm_dir="${NVM_DIR:-$HOME/.nvm}"
    if [[ -d "$nvm_dir/versions/node" ]]; then
        while IFS= read -r d; do
            [[ -x "$d/bin/node" ]] && candidates+=("$d/bin/node")
        done < <(ls -1d "$nvm_dir/versions/node/"* 2>/dev/null | sort -rV)
    fi

    # 3. fnm
    local fnm_dir="${FNM_MULTISHELL_PATH:-$HOME/.local/share/fnm/node-versions}"
    if [[ -d "$fnm_dir" ]]; then
        while IFS= read -r d; do
            [[ -x "$d/installation/bin/node" ]] && candidates+=("$d/installation/bin/node")
        done < <(ls -1d "$fnm_dir/"* 2>/dev/null | sort -rV)
    fi

    # 4. volta
    local volta_dir="${VOLTA_HOME:-$HOME/.volta}"
    if [[ -d "$volta_dir/bin" && -x "$volta_dir/bin/node" ]]; then
        candidates+=("$volta_dir/bin/node")
    fi

    # 5. Homebrew
    if command -v brew &>/dev/null; then
        local brew_prefix
        brew_prefix=$(brew --prefix 2>/dev/null)
        [[ -x "$brew_prefix/bin/node" ]] && candidates+=("$brew_prefix/bin/node")
    fi

    # 6. System paths
    for p in /usr/local/bin/node /usr/bin/node; do
        [[ -x "$p" ]] && candidates+=("$p")
    done

    # 7. Whatever is on PATH (may duplicate, but that's fine)
    local path_node
    path_node=$(command -v node 2>/dev/null) && candidates+=("$path_node")

    # Test each candidate
    for candidate in "${candidates[@]}"; do
        if node_version_ok "$candidate"; then
            # Cache the winner
            echo "$candidate" > "$NODE_CACHE"
            echo "$candidate"
            return 0
        fi
    done

    return 1
}

NODE_BIN=$(find_node) || {
    echo "[!] ERROR: No working Node.js >= $MIN_NODE found."
    echo "[!] Searched: nvm, fnm, volta, brew, /usr/local/bin, PATH"
    echo ""
    echo "[!] Install Node.js:"
    echo "    brew install node          # macOS"
    echo "    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
    echo "    nvm install --lts          # then: nvm use --lts"
    exit 1
}

# Derive npm from the same directory as the found node
NODE_DIR="$(dirname "$NODE_BIN")"
NPM_BIN="$NODE_DIR/npm"
if [[ ! -x "$NPM_BIN" ]]; then
    # npm might be a symlink elsewhere; fall back to npx-style lookup
    NPM_BIN=$(PATH="$NODE_DIR:$PATH" command -v npm 2>/dev/null) || {
        echo "[!] ERROR: Found node at $NODE_BIN but npm is missing."
        exit 1
    }
fi

# Export so child processes (npm scripts, etc.) use the same node
export PATH="$NODE_DIR:$PATH"

NODE_VER=$("$NODE_BIN" --version)
NPM_VER=$("$NPM_BIN" --version)
echo "[*] Node.js $NODE_VER  ($NODE_BIN)"
echo "[*] npm     v$NPM_VER"

# Show cache status
if [[ -f "$NODE_CACHE" ]]; then
    echo "    (cached in .node-path — delete to re-scan)"
fi

# -----------------------------------------------------------------
# Python Discovery
# -----------------------------------------------------------------

PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo ""
    echo "[!] ERROR: Python is not installed."
    echo "[!] Install Python 3.10-3.12 from https://python.org"
    exit 1
fi

PYVER=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PY_MINOR=$(echo "$PYVER" | cut -d. -f2)
echo "[*] Python  $PYVER"
if [[ "$PY_MINOR" -ge 13 ]] 2>/dev/null; then
    echo "    WARNING: Python $PYVER may have package build issues."
    echo "    Recommended: 3.10, 3.11, or 3.12."
fi
echo ""

# -----------------------------------------------------------------
# Backend Setup
# -----------------------------------------------------------------

echo "[*] Setting up backend..."
cd "$SCRIPT_DIR/backend"

if [[ ! -d "venv" ]]; then
    echo "    Creating Python virtual environment..."
    $PYTHON_CMD -m venv venv || { echo "[!] Failed to create venv."; exit 1; }
fi

source venv/bin/activate
echo "    Installing Python dependencies..."
pip install -q -r requirements.txt || {
    echo ""
    echo "[!] pip install failed. If you see Rust/cargo errors, try Python 3.11."
    exit 1
}
echo "    Python deps OK."
deactivate

# Backend also has a start-backend.js that needs node
if [[ -f package.json ]]; then
    echo "    Installing backend Node.js deps..."
    "$NPM_BIN" install --silent 2>/dev/null || true
fi

cd "$SCRIPT_DIR"

# -----------------------------------------------------------------
# Frontend Setup
# -----------------------------------------------------------------

echo ""
echo "[*] Setting up frontend..."
cd "$SCRIPT_DIR/frontend"

echo "    Installing frontend dependencies..."
"$NPM_BIN" install --silent 2>&1 | tail -3
echo "    Frontend deps OK."

cd "$SCRIPT_DIR"

# -----------------------------------------------------------------
# Environment Variable Check
# -----------------------------------------------------------------

echo ""
echo "======================================================="
echo "  Environment Check"
echo "======================================================="

MISSING_CRITICAL=0
MISSING_OPTIONAL=0

check_env() {
    local file="$1" var="$2" level="$3" desc="$4"
    if [[ -f "$file" ]] && grep -q "^${var}=" "$file" 2>/dev/null; then
        local val
        val=$(grep "^${var}=" "$file" | head -1 | cut -d= -f2-)
        # Strip quotes and whitespace
        val=$(echo "$val" | sed 's/^["'"'"']//;s/["'"'"']$//' | xargs)
        if [[ -n "$val" ]]; then
            return 0
        fi
    fi

    case "$level" in
        critical)
            echo "  [!!] MISSING: $var — $desc"
            MISSING_CRITICAL=$((MISSING_CRITICAL + 1))
            ;;
        recommended)
            echo "  [!]  MISSING: $var — $desc"
            MISSING_OPTIONAL=$((MISSING_OPTIONAL + 1))
            ;;
        optional)
            echo "  [ ]  MISSING: $var — $desc (optional)"
            ;;
    esac
    return 1
}

BE="$SCRIPT_DIR/backend/.env"
FE="$SCRIPT_DIR/frontend/.env.local"

echo ""
echo "  Backend ($([[ -f "$BE" ]] && echo "backend/.env found" || echo "backend/.env NOT FOUND"))"
if [[ ! -f "$BE" ]]; then
    echo "  [!!] Create backend/.env — copy from .env.example or add keys manually"
    MISSING_CRITICAL=$((MISSING_CRITICAL + 1))
else
    check_env "$BE" "ADMIN_KEY"       critical    "Protects settings endpoints (REQUIRED for production)" || true
    check_env "$BE" "LLM_API_KEY"     recommended "LLM provider API key (OpenRouter/Cerebras) — AI assistant won't work" || true
    check_env "$BE" "AIS_API_KEY"     recommended "aisstream.io — ships layer" || true
    check_env "$BE" "TTS_OPENAI_API_KEY" optional "OpenAI — voice mode (STT + TTS)" || true
    check_env "$BE" "TAVILY_API_KEY"  optional    "Tavily — web search tool for AI agent" || true
    check_env "$BE" "OPENSKY_CLIENT_ID" optional  "OpenSky — extended flight coverage" || true
    check_env "$BE" "LTA_ACCOUNT_KEY" optional    "Singapore LTA — CCTV cameras" || true
fi

echo ""
echo "  Frontend ($([[ -f "$FE" ]] && echo "frontend/.env.local found" || echo "frontend/.env.local not found — using defaults"))"
if [[ -f "$FE" ]]; then
    check_env "$FE" "NEXT_PUBLIC_PICOVOICE_ACCESS_KEY" optional "Picovoice — wake word detection for voice mode" || true
fi

echo ""
if [[ $MISSING_CRITICAL -gt 0 ]]; then
    echo "  $MISSING_CRITICAL critical key(s) missing. Some features won't work."
elif [[ $MISSING_OPTIONAL -gt 0 ]]; then
    echo "  All critical keys present. $MISSING_OPTIONAL recommended key(s) missing."
else
    echo "  All keys present."
fi

# -----------------------------------------------------------------
# Launch or Exit
# -----------------------------------------------------------------

if $CHECK_ONLY; then
    echo ""
    echo "  Setup complete (--check mode, not starting servers)."
    exit 0
fi

echo ""
echo "======================================================="
echo "  Starting services..."
echo "  Dashboard:  http://localhost:3000"
echo "  Backend:    http://localhost:8000"
echo "  (Press Ctrl+C to stop)"
echo "======================================================="
echo ""

cd "$SCRIPT_DIR/frontend"
"$NPM_BIN" run dev
