from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from restaurant_agent import build_default_agent


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def run_interactive() -> None:
    agent = build_default_agent()
    print("Restaurant agent is ready. اكتب رسالتك، أو exit للخروج.")
    print(f"Agent: {agent.welcome()}")
    while True:
        message = input("Customer: ").strip()
        if message.lower() in {"exit", "quit"}:
            break
        print(f"Agent: {agent.reply(message)}")


def run_scenarios(path: Path) -> None:
    scenarios = json.loads(path.read_text(encoding="utf-8"))
    for scenario in scenarios:
        agent = build_default_agent()
        print(f"\n=== {scenario['name']} ===")
        for message in scenario["messages"]:
            print(f"Customer: {message}")
            print(f"Agent: {agent.reply(message)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Try the sample Arabic restaurant AI agent.")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path(__file__).parent / "sample_conversations.json",
        help="Path to a JSON file with test conversations.",
    )
    parser.add_argument("--interactive", action="store_true", help="Start an interactive chat.")
    args = parser.parse_args()

    if args.interactive:
        run_interactive()
    else:
        run_scenarios(args.scenarios)


if __name__ == "__main__":
    main()
