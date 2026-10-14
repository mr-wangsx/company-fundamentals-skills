#!/usr/bin/env python3
"""Deterministic multi-scenario FCFF DCF calculator using JSON input.

Input amounts must use one consistent currency/unit. Example keys:
{
  "fcf0": 1000, "net_debt": -200, "shares": 225,
  "current_price": 95,
  "scenarios": [
    {"name": "base", "growth_rates": [0.08, 0.07, 0.06, 0.05, 0.04],
     "discount_rate": 0.09, "terminal_growth": 0.025, "weight": 0.5}
  ]
}

Positive net_debt means debt exceeds cash. Negative net_debt means net cash.
The script validates arithmetic; it does not validate economic assumptions.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def growth_path(scenario: dict[str, Any]) -> list[float]:
    if "growth_rates" in scenario:
        raw = scenario["growth_rates"]
        if not isinstance(raw, list) or not raw:
            raise ValueError("growth_rates must be a non-empty list")
        rates = [number(item, "growth_rates[]") for item in raw]
    else:
        rate = number(scenario.get("annual_growth"), "annual_growth")
        years = scenario.get("forecast_years")
        if isinstance(years, bool) or not isinstance(years, int) or years < 1:
            raise ValueError("forecast_years must be a positive integer")
        rates = [rate] * years
    if any(rate <= -1 for rate in rates):
        raise ValueError("each growth rate must be greater than -100%")
    return rates


def value_scenario(
    fcf0: float,
    net_debt: float,
    shares: float,
    scenario: dict[str, Any],
    current_price: float | None,
) -> dict[str, Any]:
    name = str(scenario.get("name", "scenario"))
    rates = growth_path(scenario)
    discount_rate = number(scenario.get("discount_rate"), "discount_rate")
    terminal_growth = number(scenario.get("terminal_growth"), "terminal_growth")
    if discount_rate <= terminal_growth:
        raise ValueError(f"{name}: discount_rate must exceed terminal_growth")
    if discount_rate <= -1:
        raise ValueError(f"{name}: discount_rate must be greater than -100%")

    cash_flows: list[float] = []
    pv_cash_flows: list[float] = []
    fcf = fcf0
    for year, rate in enumerate(rates, start=1):
        fcf *= 1 + rate
        cash_flows.append(fcf)
        pv_cash_flows.append(fcf / ((1 + discount_rate) ** year))

    terminal_value = cash_flows[-1] * (1 + terminal_growth) / (
        discount_rate - terminal_growth
    )
    pv_terminal = terminal_value / ((1 + discount_rate) ** len(rates))
    enterprise_value = sum(pv_cash_flows) + pv_terminal
    equity_value = enterprise_value - net_debt
    per_share = equity_value / shares
    result: dict[str, Any] = {
        "name": name,
        "growth_rates": rates,
        "discount_rate": discount_rate,
        "terminal_growth": terminal_growth,
        "forecast_fcf": cash_flows,
        "pv_forecast_fcf": pv_cash_flows,
        "terminal_value_at_horizon": terminal_value,
        "pv_terminal_value": pv_terminal,
        "terminal_value_share_of_ev": pv_terminal / enterprise_value
        if enterprise_value
        else None,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "value_per_share": per_share,
    }
    if "weight" in scenario:
        weight = number(scenario["weight"], "weight")
        if weight < 0:
            raise ValueError(f"{name}: weight cannot be negative")
        result["weight"] = weight
    if current_price is not None:
        result["upside_from_current_price"] = per_share / current_price - 1
        result["margin_of_safety"] = (per_share - current_price) / per_share if per_share else None
    return result


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    fcf0 = number(payload.get("fcf0"), "fcf0")
    net_debt = number(payload.get("net_debt", 0), "net_debt")
    shares = number(payload.get("shares"), "shares")
    if shares <= 0:
        raise ValueError("shares must be positive")
    current_price = None
    if payload.get("current_price") is not None:
        current_price = number(payload["current_price"], "current_price")
        if current_price <= 0:
            raise ValueError("current_price must be positive")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios must be a non-empty list")

    results = [
        value_scenario(fcf0, net_debt, shares, scenario, current_price)
        for scenario in scenarios
    ]
    output: dict[str, Any] = {
        "input_summary": {
            "fcf0": fcf0,
            "net_debt": net_debt,
            "shares": shares,
            "current_price": current_price,
        },
        "scenarios": results,
    }
    weighted = [item for item in results if "weight" in item]
    if weighted:
        total_weight = sum(item["weight"] for item in weighted)
        if total_weight <= 0:
            raise ValueError("scenario weights must sum to a positive number")
        output["probability_weighted_value_per_share"] = sum(
            item["value_per_share"] * item["weight"] for item in weighted
        ) / total_weight
        output["weight_sum"] = total_weight
    return output


def self_test() -> None:
    payload = {
        "fcf0": 100.0,
        "net_debt": 20.0,
        "shares": 10.0,
        "current_price": 80.0,
        "scenarios": [
            {
                "name": "base",
                "growth_rates": [0.1, 0.08, 0.06, 0.04, 0.03],
                "discount_rate": 0.1,
                "terminal_growth": 0.025,
                "weight": 1.0,
            }
        ],
    }
    result = calculate(payload)
    assert result["scenarios"][0]["value_per_share"] > 0
    assert result["probability_weighted_value_per_share"] > 0
    print("self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="JSON input file; omit to read stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    try:
        raw = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("top-level JSON must be an object")
        print(json.dumps(calculate(payload), ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError, ZeroDivisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

