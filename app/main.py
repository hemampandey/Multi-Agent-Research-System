import argparse

from app.harness.runner import run_research


def main():
    parser = argparse.ArgumentParser(description="Generate a cited research report.")
    parser.add_argument("topic", nargs="?", help="research topic (prompted for if omitted)")
    parser.add_argument("--mode", choices=["Basic", "Advanced"], default="Advanced")
    parser.add_argument("--save-dir", default="runs", help="where to save the run's JSON trace")
    args = parser.parse_args()

    topic = args.topic or input("Enter topic: ")
    result = run_research(topic, args.mode, save_dir=args.save_dir)

    if not result.ok:
        print(f"\n⛔ {result.error_code}: {result.error}")
        return

    print("\n📄 FINAL REPORT:\n")
    print(result.final_report)

    print("\n🔗 SOURCES:\n")
    for i, url in enumerate(result.sources, 1):
        print(f"{i}. {url}")

    if result.guardrail_events:
        print("\n🛡 GUARDRAILS:\n")
        for e in result.guardrail_events:
            print(f"- {e['guard']} ({e['action']}) {e['detail']}")

    print(f"\n🔍 TRACE: {result.trace['summary']}")


if __name__ == "__main__":
    main()
