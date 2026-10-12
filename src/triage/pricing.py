"""Per-run cost from the API's usage numbers. USD per million tokens.

Cache-write price assumes 1.25x input for 5-minute caching. Re-check these
against the Anthropic pricing page before quoting costs to anyone.
"""

PRICES = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.20, "cache_write": 2.50},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write": 0.125},
}


def cost_usd(model: str, usage) -> float:
    p = PRICES.get(model)
    if p is None:
        return float("nan")
    return (
        (getattr(usage, "input_tokens", 0) or 0) * p["input"]
        + (getattr(usage, "output_tokens", 0) or 0) * p["output"]
        + (getattr(usage, "cache_read_input_tokens", 0) or 0) * p["cache_read"]
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * p["cache_write"]
    ) / 1_000_000
