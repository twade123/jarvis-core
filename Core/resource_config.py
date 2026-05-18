"""
Resource configuration — hardware tier detection and model catalog.
Single source of truth for what models exist, where they run, and how much memory they need.
"""
import subprocess
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class HardwareTier(Enum):
    MINIMAL     = "minimal"      # 16GB — trained model only tier
    STANDARD    = "standard"     # 32GB — 2 resident, rest on-demand
    POWER_USER  = "power_user"   # 64GB — all resident (Tim's current setup)
    PRO         = "pro"          # 128GB — parallel sessions
    SERVER      = "server"       # 192GB+ — multi-tenant SaaS


@dataclass
class ModelSpec:
    key: str
    port: int
    hf_repo: str
    memory_gb: float
    server_type: str          # "vlm" (no /v1/ prefix), "lm" (/v1/ prefix), or "lm_lenient" (mlx_lm strict=False, /v1/ prefix)
    workspaces: List[str]     # which workspaces consume this model
    board_seat: str = ""      # boardroom seat name if applicable


@dataclass
class TierProfile:
    tier: HardwareTier
    model_budget_gb: float
    resident_models: List[str]         # always keep loaded
    on_demand_models: List[str]        # load when needed, evict under pressure
    max_parallel_sessions: int
    unload_idle_after_minutes: float   # 0.0 = never unload


# ── Model Catalog ─────────────────────────────────────────────────────────────
# Global registry of all MLX models. Both trading and boardroom reference this.
# VLM servers: /models + /chat/completions (no /v1/ prefix)
# LM  servers: /v1/models + /v1/chat/completions

MODEL_CATALOG: Dict[str, ModelSpec] = {
    "qwen3.5-9b": ModelSpec(
        key="qwen3.5-9b",
        port=11500,
        hf_repo="mlx-community/Qwen3.5-9B-4bit",
        memory_gb=6.0,
        server_type="lm_lenient",  # VLM weights but text+tools via mlx_lm strict=False
        workspaces=["trading", "boardroom"],
        board_seat="CRO",
    ),
    "deepseek-32b": ModelSpec(
        key="deepseek-32b",
        port=11501,
        hf_repo="mlx-community/DeepSeek-R1-Distill-Qwen-32B-4bit",
        memory_gb=19.0,
        server_type="lm",
        workspaces=["boardroom"],
        board_seat="CTO",
    ),
    "qwen3.5-35b": ModelSpec(
        key="qwen3.5-35b",
        port=11502,
        hf_repo="mlx-community/Qwen3.5-35B-A3B-4bit",
        memory_gb=16.0,
        server_type="lm_lenient",  # VLM weights but text+tools via mlx_lm strict=False
        workspaces=["trading", "boardroom"],
        board_seat="CSO",
    ),
    "qwen2.5-7b": ModelSpec(
        key="qwen2.5-7b",
        port=11503,
        hf_repo="mlx-community/Qwen2.5-7B-Instruct-4bit",
        memory_gb=4.5,
        server_type="lm",
        workspaces=["boardroom"],
        board_seat="CDO",
    ),
    # ── Future: trained domain model replaces all seats ──────────────────────
    # "trevor-domain": ModelSpec(
    #     key="trevor-domain", port=11500,
    #     hf_repo="local/trevor-domain-latest", memory_gb=9.0,
    #     server_type="lm", workspaces=["trading", "boardroom", "all"],
    #     board_seat="",  # serves all seats
    # ),
}

# Boardroom seat → model key (derived from catalog)
SEAT_TO_MODEL: Dict[str, str] = {
    spec.board_seat: key
    for key, spec in MODEL_CATALOG.items()
    if spec.board_seat
}
# Result: {"CRO": "qwen3.5-9b", "CTO": "deepseek-32b", "CSO": "qwen3.5-35b", "CDO": "qwen2.5-7b"}


# ── Tier Profiles ─────────────────────────────────────────────────────────────

TIER_PROFILES: Dict[HardwareTier, TierProfile] = {
    HardwareTier.MINIMAL: TierProfile(
        tier=HardwareTier.MINIMAL,
        model_budget_gb=8.0,
        resident_models=[],
        on_demand_models=["qwen2.5-7b"],   # only smallest fits; full system needs trained model
        max_parallel_sessions=1,
        unload_idle_after_minutes=1.0,     # unload immediately after use
    ),
    HardwareTier.STANDARD: TierProfile(
        tier=HardwareTier.STANDARD,
        model_budget_gb=20.0,
        resident_models=["qwen3.5-9b", "qwen2.5-7b"],    # 10.5GB always hot
        on_demand_models=["deepseek-32b"],                 # 19GB on-demand
        max_parallel_sessions=1,
        unload_idle_after_minutes=10.0,
        # Note: qwen3.5-35b (16GB) not viable on 32GB — CDO subs for CSO seat
    ),
    HardwareTier.POWER_USER: TierProfile(
        tier=HardwareTier.POWER_USER,
        model_budget_gb=44.0,              # conservative: 64GB - 20GB system headroom
        resident_models=["qwen3.5-9b", "qwen2.5-7b"],           # trading models always hot
        on_demand_models=["deepseek-32b", "qwen3.5-35b"],        # boardroom heavies on-demand
        max_parallel_sessions=1,
        unload_idle_after_minutes=30.0,    # unload boardroom heavies after 30min idle
    ),
    HardwareTier.PRO: TierProfile(
        tier=HardwareTier.PRO,
        model_budget_gb=100.0,
        resident_models=["qwen3.5-9b", "deepseek-32b", "qwen3.5-35b", "qwen2.5-7b"],
        on_demand_models=[],
        max_parallel_sessions=3,
        unload_idle_after_minutes=0.0,
    ),
    HardwareTier.SERVER: TierProfile(
        tier=HardwareTier.SERVER,
        model_budget_gb=160.0,
        resident_models=["qwen3.5-9b", "deepseek-32b", "qwen3.5-35b", "qwen2.5-7b"],
        on_demand_models=[],
        max_parallel_sessions=10,
        unload_idle_after_minutes=0.0,
    ),
}


# ── Detection ─────────────────────────────────────────────────────────────────

def detect_hardware_tier() -> HardwareTier:
    """Detect hardware tier from unified memory size (Apple Silicon)."""
    try:
        total_bytes = int(subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"], stderr=subprocess.DEVNULL
        ).strip())
        total_gb = total_bytes / (1024 ** 3)
    except Exception:
        total_gb = 16.0  # safe conservative default

    if   total_gb >= 150: return HardwareTier.SERVER
    elif total_gb >= 90:  return HardwareTier.PRO
    elif total_gb >= 50:  return HardwareTier.POWER_USER
    elif total_gb >= 28:  return HardwareTier.STANDARD
    else:                 return HardwareTier.MINIMAL


def get_tier_profile() -> TierProfile:
    return TIER_PROFILES[detect_hardware_tier()]


def get_model_for_port(port: int) -> Optional[ModelSpec]:
    for spec in MODEL_CATALOG.values():
        if spec.port == port:
            return spec
    return None


def get_model_for_seat(seat: str) -> Optional[ModelSpec]:
    key = SEAT_TO_MODEL.get(seat)
    return MODEL_CATALOG.get(key) if key else None


def get_health_endpoint(spec: ModelSpec) -> str:
    """Return the correct health/models endpoint for this server type."""
    # lm_lenient uses mlx_lm.server which has /v1/ prefix (same as lm)
    return "/models" if spec.server_type == "vlm" else "/v1/models"


def get_inference_endpoint(spec: ModelSpec) -> str:
    """Return the correct inference endpoint for this server type."""
    # lm_lenient uses mlx_lm.server which has /v1/ prefix (same as lm)
    return "/chat/completions" if spec.server_type == "vlm" else "/v1/chat/completions"


if __name__ == "__main__":
    import json
    tier = detect_hardware_tier()
    profile = get_tier_profile()
    print(f"Hardware tier:    {tier.value}")
    print(f"Model budget:     {profile.model_budget_gb}GB")
    print(f"Resident models:  {profile.resident_models}")
    print(f"On-demand models: {profile.on_demand_models}")
    print(f"Max sessions:     {profile.max_parallel_sessions}")
    print(f"Unload after:     {profile.unload_idle_after_minutes}min")
    print(f"\nSeat→Model map:   {SEAT_TO_MODEL}")
    print(f"\nFull model catalog:")
    for key, spec in MODEL_CATALOG.items():
        print(f"  {key}: port={spec.port} mem={spec.memory_gb}GB "
              f"type={spec.server_type} seat={spec.board_seat} "
              f"workspaces={spec.workspaces}")
