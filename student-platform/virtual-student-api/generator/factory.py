from .base import StudentGenerator
from .random_generator import RandomGenerator

# 새 전략 추가 시 이 dict에만 등록하면 된다.
_REGISTRY: dict[str, type] = {
    "random": RandomGenerator,
}


def get_generator(strategy: str = "random") -> StudentGenerator:
    cls = _REGISTRY.get(strategy)
    if cls is None:
        raise ValueError(f"Unknown generator strategy: '{strategy}'. Available: {list(_REGISTRY)}")
    return cls()


def available_strategies() -> list[str]:
    return list(_REGISTRY.keys())
