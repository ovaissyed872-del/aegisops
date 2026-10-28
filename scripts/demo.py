"""Six narrated, deterministic demonstrations; never contacts Docker."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegisops.audit import check_complete
from aegisops.orchestrator import Engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print decisions and plans without any adapter actions",
    )
    args = parser.parse_args()
    print("AEGISOPS — POLICY-GATED REMEDIATION DEMO")
    print("SIMULATE ONLY · Authored demo fixtures, not organizer ground truth.\n")
    cases = [
        ("1. Log-full fault: automatic, bounded cleanup", "log_full", "RESOLVED"),
        (
            "2. Core dump: refuse mutation and escalate to operator",
            "core_dump",
            "REFUSE",
        ),
        (
            "3. Logs + core dump: ambiguous, escalate without guessing",
            "logs_and_core",
            "ESCALATE",
        ),
        (
            "4. Certificate: recorded human approval, then execute",
            "cert_expiring",
            "RESOLVED",
        ),
        ("5. Ineffective fix: ONE rollback, then escalate", "log_full", "ESCALATE"),
        (
            "6. Kill switch after mutation: abort, compensate, escalate",
            "log_full",
            "ESCALATE",
        ),
    ]
    for index, (title, fault, expected) in enumerate(cases, 1):
        engine = Engine()
        engine.adapter.inject(fault)
        if index == 5:
            engine.adapter.fail_remediation = True
        if index == 6:
            engine.adapter.after_step = lambda *_: engine.killswitch.set(True)
        print("=" * 72)
        print(title)
        result = engine.run(dry_run=args.dry_run)
        if result["outcome"] == "NEEDS_APPROVAL":
            print("Policy: NEEDS_APPROVAL. No action has executed.")
            engine.approvals.approve(
                result["approval_id"],
                "demo-on-call",
                "Reviewed exact certificate rotation plan and staging scope",
            )
            result = engine.resume(result["approval_id"])
        if args.dry_run:
            assert not engine.adapter.calls
            print("Plan:", json.dumps(result.get("plan", []), indent=2))
        else:
            assert result["outcome"] == expected, (title, result)
        record = result["audit"]
        assert check_complete(record) == []
        print("Outcome:", result["outcome"], "| policy:", result["decision"]["outcome"])
        print("Reasons:", "; ".join(result["decision"]["reasons"]))
        print("Audit:", json.dumps(record, indent=2))
        print(
            f"Adapter calls: {len(engine.adapter.calls)} | change snapshots: {len(engine.store.changes())} | completeness: 100%\n"
        )
    print("All six demonstrations completed.")


if __name__ == "__main__":
    main()
