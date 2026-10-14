#!/usr/bin/env python3
"""Recompute common fundamental-analysis metrics and compare reported values.

Input JSON format:
{
  "default_relative_tolerance": 0.01,
  "checks": [
    {"name": "2025 ROE", "formula": "roe", "reported": 0.18,
     "inputs": {"net_income_parent": 18, "equity_begin": 95, "equity_end": 105}}
  ]
}

Supported formulas: fcf, roe, roic, fcf_conversion, payout_ratio,
dividend_yield, net_debt, cagr and dcf_per_share. Percentages use decimals.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable


def num(inputs: dict[str, Any], key: str) -> float:
    value = inputs.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"input '{key}' must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"input '{key}' must be finite")
    return value


def nonzero(value: float, key: str) -> float:
    if value == 0:
        raise ValueError(f"input '{key}' cannot be zero")
    return value


def fcf(i: dict[str, Any]) -> float:
    return num(i, "cfo") - num(i, "capex")


def roe(i: dict[str, Any]) -> float:
    average_equity = (num(i, "equity_begin") + num(i, "equity_end")) / 2
    return num(i, "net_income_parent") / nonzero(average_equity, "average_equity")


def roic(i: dict[str, Any]) -> float:
    if "nopat" in i:
        nopat = num(i, "nopat")
    else:
        nopat = num(i, "ebit") * (1 - num(i, "tax_rate"))
    average_capital = (num(i, "invested_capital_begin") + num(i, "invested_capital_end")) / 2
    return nopat / nonzero(average_capital, "average_invested_capital")


def fcf_conversion(i: dict[str, Any]) -> float:
    return (num(i, "cfo") - num(i, "capex")) / nonzero(
        num(i, "net_income_parent"), "net_income_parent"
    )


def payout_ratio(i: dict[str, Any]) -> float:
    return num(i, "cash_dividends") / nonzero(num(i, "net_income_parent"), "net_income_parent")


def dividend_yield(i: dict[str, Any]) -> float:
    return num(i, "dividend_per_share") / nonzero(num(i, "reference_price"), "reference_price")


def net_debt(i: dict[str, Any]) -> float:
    return num(i, "interest_bearing_debt") - num(i, "cash_and_equivalents")


def cagr(i: dict[str, Any]) -> float:
    start = num(i, "start")
    end = num(i, "end")
    years = num(i, "years")
    if start <= 0 or end < 0 or years <= 0:
        raise ValueError("cagr requires start > 0, end >= 0 and years > 0")
    return (end / start) ** (1 / years) - 1


def dcf_per_share(i: dict[str, Any]) -> float:
    current_fcf = num(i, "fcf0")
    raw_rates = i.get("growth_rates")
    if not isinstance(raw_rates, list) or not raw_rates:
        raise ValueError("input 'growth_rates' must be a non-empty list")
    rates: list[float] = []
    for index, raw in enumerate(raw_rates):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"growth_rates[{index}] must be a number")
        rate = float(raw)
        if not math.isfinite(rate) or rate <= -1:
            raise ValueError(f"growth_rates[{index}] must be finite and greater than -100%")
        rates.append(rate)
    discount_rate = num(i, "discount_rate")
    terminal_growth = num(i, "terminal_growth")
    if discount_rate <= terminal_growth:
        raise ValueError("discount_rate must exceed terminal_growth")
    pv_explicit = 0.0
    for year, rate in enumerate(rates, start=1):
        current_fcf *= 1 + rate
        pv_explicit += current_fcf / ((1 + discount_rate) ** year)
    terminal = current_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    enterprise_value = pv_explicit + terminal / ((1 + discount_rate) ** len(rates))
    equity_value = enterprise_value - num(i, "net_debt")
    return equity_value / nonzero(num(i, "shares"), "shares")


FORMULAS: dict[str, Callable[[dict[str, Any]], float]] = {
    "fcf": fcf,
    "roe": roe,
    "roic": roic,
    "fcf_conversion": fcf_conversion,
    "payout_ratio": payout_ratio,
    "dividend_yield": dividend_yield,
    "net_debt": net_debt,
    "cagr": cagr,
    "dcf_per_share": dcf_per_share,
}


def run(payload: dict[str, Any]) -> dict[str, Any]:
    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("checks must be a non-empty list")
    default_relative = float(payload.get("default_relative_tolerance", 0.01))
    default_absolute = float(payload.get("default_absolute_tolerance", 0.0))
    if default_relative < 0 or default_absolute < 0:
        raise ValueError("tolerances cannot be negative")
    output: list[dict[str, Any]] = []
    counts = {"within_tolerance": 0, "outside_tolerance": 0, "computed_only": 0, "error": 0}

    for index, check in enumerate(checks):
        name = str(check.get("name", f"check-{index + 1}")) if isinstance(check, dict) else f"check-{index + 1}"
        row: dict[str, Any] = {"name": name}
        try:
            if not isinstance(check, dict):
                raise ValueError("check must be an object")
            formula_name = str(check.get("formula", ""))
            row["formula"] = formula_name
            if formula_name not in FORMULAS:
                raise ValueError(f"unsupported formula '{formula_name}'")
            inputs = check.get("inputs")
            if not isinstance(inputs, dict):
                raise ValueError("inputs must be an object")
            computed = FORMULAS[formula_name](inputs)
            row["computed"] = computed
            if check.get("reported") is None:
                row["status"] = "computed_only"
            else:
                reported_raw = check["reported"]
                if isinstance(reported_raw, bool) or not isinstance(reported_raw, (int, float)):
                    raise ValueError("reported must be a number")
                reported = float(reported_raw)
                absolute_difference = computed - reported
                denominator = max(abs(reported), abs(computed), 1e-15)
                relative_difference = abs(absolute_difference) / denominator
                relative_tolerance = float(check.get("relative_tolerance", default_relative))
                absolute_tolerance = float(check.get("absolute_tolerance", default_absolute))
                if relative_tolerance < 0 or absolute_tolerance < 0:
                    raise ValueError("tolerances cannot be negative")
                within = abs(absolute_difference) <= absolute_tolerance or relative_difference <= relative_tolerance
                row.update(
                    {
                        "reported": reported,
                        "absolute_difference": absolute_difference,
                        "relative_difference": relative_difference,
                        "relative_tolerance": relative_tolerance,
                        "absolute_tolerance": absolute_tolerance,
                        "status": "within_tolerance" if within else "outside_tolerance",
                    }
                )
            counts[row["status"]] += 1
        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            row["status"] = "error"
            row["error"] = str(exc)
            counts["error"] += 1
        output.append(row)
    return {"summary": counts, "checks": output}


def self_test() -> None:
    result = run(
        {
            "checks": [
                {
                    "name": "roe",
                    "formula": "roe",
                    "reported": 0.2,
                    "inputs": {"net_income_parent": 20, "equity_begin": 90, "equity_end": 110},
                },
                {"name": "fcf", "formula": "fcf", "inputs": {"cfo": 50, "capex": 20}},
            ]
        }
    )
    assert result["summary"]["within_tolerance"] == 1
    assert result["checks"][1]["computed"] == 30
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
        print(json.dumps(run(payload), ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

