#!/bin/bash
# =============================================================================
# Jarvis Platform — Setup Script
# Installs and configures the full Jarvis AI platform on Apple Silicon Macs.
#
# Minimum: 64GB (Personal tier)
# Recommended: 128GB+ (Pro/Business tier)
#
# Usage:
#   curl -s https://raw.githubusercontent.com/.../setup_jarvis.sh | bash
#   OR: bash scripts/setup_jarvis.sh
# =============================================================================

set -e
JARVIS_DIR="${JARVIS_DIR:-$HOME/jarvis}"
VENV_DIR="$HOME/myenv"
LOG_DIR="$JARVIS_DIR/Logs/mlx"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; exit 1; }
info() { echo -e "   $1"; }

echo ""
echo "========================================"
echo "  Jarvis Platform Setup"
echo "========================================"
echo ""

# ── 1. Hardware check ─────────────────────────────────────────────────────────
echo "1. Checking hardware..."
RAM_GB=$(sysctl -n hw.memsize | awk '{printf "%.0f", $1/1073741824}')
CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "unknown")
info "Chip: $CHIP"
info "RAM:  ${RAM_GB}GB"

if [ "$RAM_GB" -lt 32 ]; then
    err "Minimum 32GB RAM required. This Mac has ${RAM_GB}GB."
fi
if [ "$RAM_GB" -lt 64 ]; then
    warn "32GB mode — limited model support. 64GB recommended."
fi
ok "Hardware check passed (${RAM_GB}GB)"

# ── 2. Homebrew ───────────────────────────────────────────────────────────────
echo ""
echo "2. Checking Homebrew..."
if ! command -v brew &>/dev/null; then
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
ok "Homebrew ready"

# ── 3. Python 3.10 ───────────────────────────────────────────────────────────
echo ""
echo "3. Checking Python..."
if ! command -v python3.10 &>/dev/null; then
    info "Installing Python 3.10..."
    brew install python@3.10
fi
PYTHON=$(command -v python3.10 || command -v python3)
info "Python: $($PYTHON --version)"
ok "Python ready"

# ── 4. Virtual environment ────────────────────────────────────────────────────
echo ""
echo "4. Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    info "Creating venv at $VENV_DIR..."
    $PYTHON -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
ok "venv activated: $VENV_DIR"

# ── 5. Python dependencies ────────────────────────────────────────────────────
echo ""
echo "5. Installing Python packages..."
pip install --quiet --upgrade pip
pip install --quiet mlx mlx-lm mlx-vlm anthropic fastapi uvicorn aiohttp aiofiles \
    sqlite-utils rich httpx pydantic
ok "Python packages installed"

# ── 6. Create directories ─────────────────────────────────────────────────────
echo ""
echo "6. Creating directories..."
mkdir -p "$LOG_DIR"
mkdir -p "$JARVIS_DIR/training_data/sessions"
ok "Directories created"

# ── 7. MLX model download ─────────────────────────────────────────────────────
echo ""
echo "7. Downloading MLX models (this takes a while — ~35GB total)..."
info "Progress logged to $LOG_DIR/model_download.log"

MODELS=(
    "mlx-community/Qwen2.5-7B-Instruct-4bit"
    "mlx-community/Qwen3.5-9B-4bit"
)
if [ "$RAM_GB" -ge 64 ]; then
    MODELS+=(
        "mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit"
        "mlx-community/Qwen3.5-35B-A3B-4bit"
    )
fi

for MODEL in "${MODELS[@]}"; do
    MODEL_NAME=$(basename "$MODEL")
    MODEL_PATH="$HOME/.cache/huggingface/hub/models--${MODEL//\//'--'}"
    if [ -d "$MODEL_PATH" ]; then
        ok "  $MODEL_NAME (already downloaded)"
    else
        info "  Downloading $MODEL_NAME..."
        python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('$MODEL', local_dir_use_symlinks=False)
print('  Done: $MODEL_NAME')
" >> "$LOG_DIR/model_download.log" 2>&1
        ok "  $MODEL_NAME"
    fi
done

# ── 8. Training DB init ───────────────────────────────────────────────────────
echo ""
echo "8. Initializing training database..."
cd "$JARVIS_DIR"
python3 -c "
import sys; sys.path.insert(0,'.')
from Core.session_distiller import init_db
init_db()
print('Training DB initialized')
" 2>/dev/null && ok "Training DB ready" || warn "Training DB init skipped (check logs)"

# ── 9. Detect tier + test boot ────────────────────────────────────────────────
echo ""
echo "9. Hardware tier detection..."
python3 -c "
import sys; sys.path.insert(0,'.')
from Core.resource_config import detect_hardware_tier, get_tier_profile
tier = detect_hardware_tier()
profile = get_tier_profile()
print(f'Tier: {tier.value}')
print(f'Budget: {profile.model_budget_gb}GB')
print(f'Resident: {profile.resident_models}')
print(f'On-demand: {profile.on_demand_models}')
" && ok "Tier detection working" || warn "Check Core/ imports"

# ── 10. LaunchAgent (boot persistence) ────────────────────────────────────────
echo ""
echo "10. Installing boot persistence..."
PLIST_SRC="$JARVIS_DIR/scripts/com.jarvis.mlx.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.jarvis.mlx.plist"

if [ -f "$PLIST_SRC" ]; then
    cp "$PLIST_SRC" "$PLIST_DST"
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    launchctl load "$PLIST_DST" 2>/dev/null
    ok "LaunchAgent installed — models will start at login"
else
    warn "Plist not found at $PLIST_SRC — skipping boot persistence"
fi

# ── 11. First boot test ───────────────────────────────────────────────────────
echo ""
echo "11. Running bootstrap..."
python3 -c "
import asyncio, sys; sys.path.insert(0,'.')
from Core.system_bootstrap import run_bootstrap
result = asyncio.run(run_bootstrap(start_models=True))
alive = result.get('alive_models', [])
print(f'Alive models: {alive}')
print(f'Loaded: {result.get(\"loaded_memory_gb\", 0)}GB / {result.get(\"model_budget_gb\", 0)}GB')
" 2>/dev/null && ok "Bootstrap complete" || warn "Bootstrap had issues — check Logs/mlx/"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo -e "  ${GREEN}Setup complete!${NC}"
echo "========================================"
echo ""
echo "Quick commands:"
echo "  bash scripts/mlx_servers.sh status       — check model status"
echo "  python3 Core/system_status.py            — full status snapshot"
echo "  python3 Core/system_bootstrap.py         — manual re-bootstrap"
echo ""
