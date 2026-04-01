from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentic_browser.intelligence.benchmarks import (
    load_benchmark_cases,
    run_planner_benchmarks,
    run_workflow_benchmarks,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run planner or workflow benchmarks for Agentic Browser.")
    parser.add_argument("cases", help="Path to a JSON file containing benchmark cases.")
    parser.add_argument(
        "--mode",
        choices=("planner", "workflow"),
        default="planner",
        help="Which benchmark mode to run.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    cases = load_benchmark_cases(args.cases)
    if args.mode == "workflow":
        payload = await run_workflow_benchmarks(cases)
    else:
        payload = await run_planner_benchmarks(cases)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
