from __future__ import annotations

import math
from scipy import stats
from source.logger import get_logger

log = get_logger(__name__)


def required_sample_size(
    population: int,
    alpha: float = 0.05,
    power: float = 0.80,
    effect_size: float = 0.2,
    margin: float = 0.02,
    n_categories: int = 1,
) -> int:
    """Compute the minimum sample size for a given month's population.

    Uses the *larger* of two criteria so the sample is both powerful enough
    to detect shifts and precise enough to estimate proportions:

    1. **Power-based** (two-proportion z-test, Cohen's *h*):
       n = ((z_{α/2} + z_β) / h)²

    2. **Margin-of-error-based** (worst-case proportion, Bonferroni-adjusted
       for ``n_categories`` simultaneous intervals):
       n = z_{α/(2k)}² · p(1−p) / E²

    A finite-population correction is applied to both, and the result is
    capped at ``population`` (i.e. full enumeration for small months).
    """
    # bonferroni-adjusted alpha for multi-category estimation
    alpha_adj = alpha / max(n_categories, 1)

    # --- criterion 1: power-based (detect effect_size shift) ---
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    n_power = math.ceil(((z_a + z_b) / effect_size) ** 2)

    # --- criterion 2: margin-of-error-based (estimate proportions) ---
    z_m = stats.norm.ppf(1 - alpha_adj / 2)
    n_moe = math.ceil(z_m ** 2 * 0.25 / margin ** 2)  # p=0.5 worst case

    n_raw = max(n_power, n_moe)

    # finite-population correction
    n_adj = math.ceil(n_raw * population / (n_raw + population - 1))
    return min(n_adj, population)


def monthly_sample_plan(
    populations: dict[str, int],
    alpha: float = 0.05,
    power: float = 0.80,
    effect_size: float = 0.2,
    margin: float = 0.02,
    n_categories: int = 1,
) -> dict[str, int]:
    """Return {year_month: required_n} for every month in *populations*.

    Also logs a summary so the user can audit the plan.
    """
    plan: dict[str, int] = {}
    for ym, pop in sorted(populations.items()):
        plan[ym] = required_sample_size(
            pop,
            alpha=alpha,
            power=power,
            effect_size=effect_size,
            margin=margin,
            n_categories=n_categories,
        )

    total_pop = sum(populations.values())
    total_sample = sum(plan.values())
    full_enum = sum(1 for ym in plan if plan[ym] == populations[ym])
    log.info(
        "Sample plan: %d months, %d/%d total sampled (%.1f%%), "
        "%d months at full enumeration",
        len(plan),
        total_sample,
        total_pop,
        total_sample / total_pop * 100 if total_pop else 0,
        full_enum,
    )
    return plan
