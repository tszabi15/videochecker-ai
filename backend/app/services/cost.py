from typing import Dict, Any, Tuple
from app.config import MODEL_CONFIG

def calculate_gemini_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    is_batch: bool = False
) -> Tuple[float, bool]:
    """
    Calculates USD cost for Gemini model call based on exact token usage.
    Returns (cost_usd, long_context_applied).
    """
    config = MODEL_CONFIG.get(model_name, MODEL_CONFIG["gemini-3.1-pro"])
    
    long_context = input_tokens > 200_000
    
    if long_context:
        input_rate = config["input_price_per_m_long"]
        output_rate = config["output_price_per_m_long"]
    else:
        input_rate = config["input_price_per_m"]
        output_rate = config["output_price_per_m"]
        
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
    is_batch: bool = False
) -> float:
    """
    Estimates job cost prior to execution based on file size or probed duration.
    """
    if duration_seconds > 0:
        est_input_tokens = int(duration_seconds * 300) + 5000
    else:
        # Approximate ~3s per MB
        est_input_tokens = int(file_size_mb * 900) + 5000
        
    est_output_tokens = 2500  # standard JSON report output length
    
    cost, _ = calculate_gemini_cost(model_name, est_input_tokens, est_output_tokens, is_batch)
    return max(cost, 0.001)
