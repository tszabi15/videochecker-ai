import pytest
from app.services.cost import calculate_gemini_cost, estimate_job_cost
from app.config import MODEL_CONFIG

def test_standard_context_cost():
    # 100k input, 2k output on gemini-3.1-pro
    cost, long_ctx = calculate_gemini_cost("gemini-3.1-pro", 100_000, 2_000, is_batch=False)
    assert not long_ctx
    # 100k / 1M * 2.00 = 0.20
    # 2k / 1M * 12.00 = 0.024
    # Total = 0.224
    assert round(cost, 3) == 0.224

def test_long_context_cost_tier():
    # 250k input (>200k threshold), 5k output on gemini-3.1-pro
    cost, long_ctx = calculate_gemini_cost("gemini-3.1-pro", 250_000, 5_000, is_batch=False)
    assert long_ctx
    # 250k / 1M * 4.00 (long rate) = 1.00
    # 5k / 1M * 18.00 (long rate) = 0.09
    # Total = 1.09
    assert round(cost, 2) == 1.09

def test_batch_mode_discount():
    cost_realtime, _ = calculate_gemini_cost("gemini-3.1-pro", 100_000, 2_000, is_batch=False)
    cost_batch, _ = calculate_gemini_cost("gemini-3.1-pro", 100_000, 2_000, is_batch=True)
    assert round(cost_batch, 4) == round(cost_realtime * 0.50, 4)

def test_estimate_job_cost():
    est_cost = estimate_job_cost("gemini-3.5-flash", file_size_mb=50.0, duration_seconds=120.0)
    assert est_cost > 0.0
