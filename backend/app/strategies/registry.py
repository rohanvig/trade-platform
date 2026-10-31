from typing import Type

from app.strategies.base import BaseStrategy
from app.strategies.macd_crossover import MACDCrossoverStrategy
from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from app.strategies.sma_crossover import SMACrossoverStrategy

STRATEGY_REGISTRY: dict[str, Type[BaseStrategy]] = {
    SMACrossoverStrategy.name: SMACrossoverStrategy,
    RSIMeanReversionStrategy.name: RSIMeanReversionStrategy,
    MACDCrossoverStrategy.name: MACDCrossoverStrategy,
}


def list_strategies() -> list[dict]:
    """Return all available strategies with their descriptions and default parameters."""
    return [
        {
            "name": name,
            "description": cls.description,
            "default_params": cls.default_params,
        }
        for name, cls in STRATEGY_REGISTRY.items()
    ]


def get_strategy(name: str, **params) -> BaseStrategy:
    """Instantiate a strategy by name with optional parameter overrides."""
    key = name.strip().upper()
    if key not in STRATEGY_REGISTRY:
        available = list(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available strategies: {available}")
    strategy_cls = STRATEGY_REGISTRY[key]
    return strategy_cls(**params)
