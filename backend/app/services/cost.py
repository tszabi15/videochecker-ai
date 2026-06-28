"""
Cost estimation and calculation service for Gemini API usage.

Supports per-model pricing tiers, long-context surcharges, and batch discounts.
"""

from typing import Tuple
from app.config import MODEL_CONFIG


def calculate_gemini_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    is_batch: bool = False,
) -> Tuple[float, bool]:
    """
    Calculates USD cost for a Gemini model call based on exact token usage.

    Handles both model aliases (e.g. "HEAVY_ANALYZER") and raw model names
    (e.g. "gemini-3.5-flash") by looking up MODEL_CONFIG with a fallback.

    Returns:
        (cost_usd, long_context_applied): The total cost and whether the
        long-context pricing tier was applied (>200k input tokens).
    """
    long_context = input_tokens > 200_000

    if model_name in ("gemini-3.5-flash", "HEAVY_ANALYZER", "FAST_VERIFIER"):
        return 0.0000, long_context

    config = MODEL_CONFIG.get(model_name, MODEL_CONFIG.get("gemini-3.5-flash", {}))

    if long_context:
        input_rate = config.get("input_price_per_m_long", config.get("input_price_per_m", 0.00))
        output_rate = config.get("output_price_per_m_long", config.get("output_price_per_m", 0.00))
    else:
        input_rate = config.get("input_price_per_m", 0.00)
        output_rate = config.get("output_price_per_m", 0.00)

    input_cost = (input_tokens / 1_000_000) * input_rate
    output_cost = (output_tokens / 1_000_000) * output_rate

    total_cost = input_cost + output_cost

    if is_batch:
        total_cost *= config.get("batch_discount", 0.50)

    return round(total_cost, 6), long_context


def estimate_job_cost(
    model_name: str,
    file_size_mb: float,
    duration_seconds: float = 0.0,
    is_batch: bool = False,
) -> float:
    """
    Estimates job cost prior to execution based on file size or probed duration.

    Uses a heuristic of ~300 tokens/second for video or ~900 tokens/MB as fallback.
    """
    if model_name in ("gemini-3.5-flash", "HEAVY_ANALYZER", "FAST_VERIFIER"):
        return 0.0000

    if duration_seconds > 0:
        est_input_tokens = int(duration_seconds * 300) + 5000
    else:
        # Approximate ~3s per MB
        est_input_tokens = int(file_size_mb * 900) + 5000

    est_output_tokens = 2500  # standard JSON report output length

    cost, _ = calculate_gemini_cost(model_name, est_input_tokens, est_output_tokens, is_batch)
    return cost
