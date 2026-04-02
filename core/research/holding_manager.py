"""Limit turnover when refreshing a concentrated sleeve from ranked candidates."""

from __future__ import annotations

from typing import Dict, List, Sequence, Set


def _rank_index(ranked: Sequence[str]) -> Dict[str, int]:
    return {str(s): i for i, s in enumerate(ranked)}


def resolve_holdings(
    current: Sequence[str],
    ranked: Sequence[str],
    *,
    portfolio_slots: int,
    max_turnover_fraction: float = 0.25,
) -> List[str]:
    """
    Build next holdings: prefer `ranked[:portfolio_slots]`, but cap how many
    names we add/remove vs `current` in one step.

    - `ranked`: best -> worst (e.g. from momentum + selector).
    - `max_turnover_fraction`: max fraction of len(current) that may change
      (adds + drops each count toward the budget when replacing).
    """
    cap = max(0, int(portfolio_slots))
    ranked_list = [str(s) for s in ranked]
    desired: List[str] = []
    seen: Set[str] = set()
    for s in ranked_list:
        if s in seen:
            continue
        seen.add(s)
        desired.append(s)
        if len(desired) >= cap:
            break

    cur = [str(s) for s in current]
    if not cur:
        return desired

    cur_set, des_set = set(cur), set(desired)
    to_drop = [s for s in cur if s not in des_set]
    to_add = [s for s in desired if s not in cur_set]

    budget = max(1, int(max_turnover_fraction * len(cur) + 0.999))  # ceil
    ri = _rank_index(ranked_list)

    # Drop worst-ranked among to_drop first (higher index = worse)
    to_drop_sorted = sorted(to_drop, key=lambda s: -ri.get(s, 10**9))
    # Add best-ranked among to_add first
    to_add_sorted = sorted(to_add, key=lambda s: ri.get(s, 10**9))

    new_set = set(cur)
    ops = 0
    while ops < budget and (to_drop_sorted or to_add_sorted):
        if to_drop_sorted and to_add_sorted:
            new_set.discard(to_drop_sorted.pop(0))
            new_set.add(to_add_sorted.pop(0))
            ops += 1
        elif to_drop_sorted and len(new_set) > cap:
            new_set.discard(to_drop_sorted.pop(0))
            ops += 1
        elif to_add_sorted and len(new_set) < cap:
            new_set.add(to_add_sorted.pop(0))
            ops += 1
        else:
            break

    # Order output by rank
    out = [s for s in ranked_list if s in new_set]
    return out[:cap]
