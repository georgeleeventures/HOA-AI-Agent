"""CLI runner for HouseKeep AI synthetic test data generation and injection.

Usage:
    # Dry run — generate and print scenario summary (no Gmail or DB needed)
    python -m scripts.testdata.run --dry-run

    # Set up test residents in the database only
    python -m scripts.testdata.run --setup-residents-only --database-url postgresql://...

    # Inject via insert (into HOA inbox, requires test mode)
    python -m scripts.testdata.run \\
        --hoa-email housekeep@yourhoa.com \\
        --client-id YOUR_CLIENT_ID \\
        --client-secret YOUR_SECRET \\
        --hoa-token YOUR_HOA_REFRESH_TOKEN \\
        --method insert

    # Inject via send (from test sender account, passes DKIM)
    python -m scripts.testdata.run \\
        --hoa-email housekeep@yourhoa.com \\
        --client-id YOUR_CLIENT_ID \\
        --client-secret YOUR_SECRET \\
        --sender-token SENDER_REFRESH_TOKEN \\
        --method send

    # Run specific scenarios only
    python -m scripts.testdata.run --scenarios q_rules_ac_unit,doc_ccrs,cc_roof_discussion_1 ...

    # Verify results after injection
    python -m scripts.testdata.run --verify --database-url postgresql://...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

# Allow running from repo root: python -m scripts.testdata.run
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.testdata.scenarios import (
    ALL_SCENARIOS,
    SCENARIO_BY_NAME,
    TEST_RESIDENTS,
    EmailScenario,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("testdata")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

async def setup_residents(database_url: str) -> None:
    """Insert or update test residents in the database."""
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        for key, resident in TEST_RESIDENTS.items():
            if key == "spammer":
                # Spammer is intentionally NOT in the database
                logger.info("Skipping spammer (not added to DB by design)")
                continue

            await conn.execute(
                """
                INSERT INTO residents (email, name, unit, role, ownership_pct, is_authorized)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (email) DO UPDATE SET
                    name = EXCLUDED.name,
                    unit = EXCLUDED.unit,
                    role = EXCLUDED.role,
                    ownership_pct = EXCLUDED.ownership_pct,
                    is_authorized = EXCLUDED.is_authorized,
                    updated_at = NOW()
                """,
                resident.email,
                resident.name,
                resident.unit,
                resident.role,
                resident.ownership_pct,
                resident.is_authorized,
            )
            status = "authorized" if resident.is_authorized else "UNAUTHORIZED"
            logger.info(
                "Resident: %s (%s, %s, %s)",
                resident.name,
                resident.email,
                resident.role,
                status,
            )

        logger.info("Resident setup complete (%d residents)", len(TEST_RESIDENTS) - 1)
    finally:
        await conn.close()


async def clean_test_data(database_url: str) -> None:
    """Remove all test data from the database."""
    import asyncpg

    test_emails = [r.email for r in TEST_RESIDENTS.values()]

    conn = await asyncpg.connect(database_url)
    try:
        # Delete audit log entries from test users
        deleted = await conn.execute(
            "DELETE FROM audit_log WHERE user_email = ANY($1::text[])",
            test_emails,
        )
        logger.info("Cleaned audit_log: %s", deleted)

        # Delete documents sourced from test emails
        deleted = await conn.execute(
            """
            DELETE FROM documents WHERE source_email_id IN (
                SELECT gmail_id FROM emails WHERE sender = ANY($1::text[])
            )
            """,
            test_emails,
        )
        logger.info("Cleaned documents: %s", deleted)

        # Delete emails from test senders
        deleted = await conn.execute(
            "DELETE FROM emails WHERE sender = ANY($1::text[])",
            test_emails,
        )
        logger.info("Cleaned emails: %s", deleted)

        # Delete test residents
        deleted = await conn.execute(
            "DELETE FROM residents WHERE email = ANY($1::text[])",
            test_emails,
        )
        logger.info("Cleaned residents: %s", deleted)

        logger.info("Test data cleanup complete")
    finally:
        await conn.close()


async def verify_results(database_url: str, results: list[dict]) -> None:
    """Check the database for expected processing results."""
    import asyncpg

    if not results:
        logger.warning("No injection results to verify")
        return

    conn = await asyncpg.connect(database_url)
    try:
        print("\n" + "=" * 90)
        print(f"{'SCENARIO':<35} {'INTENT':<15} {'CATEGORY':<25} {'STATUS':<10}")
        print("=" * 90)

        pass_count = 0
        fail_count = 0
        skip_count = 0

        for r in results:
            if r["status"] != "ok":
                print(f"{r['scenario']:<35} {r['intent']:<15} {'—':<25} {'SKIP':>10}")
                skip_count += 1
                continue

            # Check if email was stored
            email_row = await conn.fetchrow(
                "SELECT id, is_processed FROM emails WHERE gmail_id = $1",
                r["gmail_id"],
            )

            if not email_row:
                print(f"{r['scenario']:<35} {r['intent']:<15} {'—':<25} {'NO EMAIL':>10}")
                fail_count += 1
                continue

            # Check document classification for doc forwards
            if r["target_category"]:
                doc_row = await conn.fetchrow(
                    """
                    SELECT category, subcategory, confidence_score
                    FROM documents WHERE source_email_id = $1
                    """,
                    r["gmail_id"],
                )
                if doc_row:
                    cat = f"{doc_row['category']}/{doc_row['subcategory']}"
                    expected = f"{r['target_category']}/{r['target_subcategory']}"
                    match = cat == expected
                    status = "PASS" if match else "WARN"
                    if match:
                        pass_count += 1
                    else:
                        fail_count += 1
                    print(f"{r['scenario']:<35} {r['intent']:<15} {cat:<25} {status:>10}")
                else:
                    print(f"{r['scenario']:<35} {r['intent']:<15} {'NO DOC':<25} {'FAIL':>10}")
                    fail_count += 1
            else:
                # Check audit log for questions/corrections
                audit_row = await conn.fetchrow(
                    "SELECT action, confidence FROM audit_log WHERE thread_id = $1 ORDER BY created_at DESC LIMIT 1",
                    r["thread_id"],
                )
                if audit_row:
                    print(f"{r['scenario']:<35} {r['intent']:<15} {audit_row['action']:<25} {'PASS':>10}")
                    pass_count += 1
                elif email_row["is_processed"]:
                    print(f"{r['scenario']:<35} {r['intent']:<15} {'processed':<25} {'PASS':>10}")
                    pass_count += 1
                else:
                    print(f"{r['scenario']:<35} {r['intent']:<15} {'pending':<25} {'WAIT':>10}")
                    skip_count += 1

        print("=" * 90)
        print(f"Results: {pass_count} passed, {fail_count} failed, {skip_count} skipped")
        print()

    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

def print_dry_run(scenarios: list[EmailScenario]) -> None:
    """Print a summary of all scenarios without injecting."""
    print("\n" + "=" * 100)
    print(f"{'#':<4} {'NAME':<35} {'INTENT':<18} {'SENDER':<10} {'ATTACHMENTS':<20} {'REPLY TO'}")
    print("=" * 100)

    for i, s in enumerate(scenarios, 1):
        att_str = ", ".join(a.filename for a in s.attachments) if s.attachments else "—"
        if len(att_str) > 18:
            att_str = att_str[:15] + "..."
        reply = s.is_reply_to or "—"
        print(f"{i:<4} {s.name:<35} {s.intent:<18} {s.sender_key:<10} {att_str:<20} {reply}")

    print("=" * 100)

    # Summary by intent
    intents: dict[str, int] = {}
    for s in scenarios:
        intents[s.intent] = intents.get(s.intent, 0) + 1
    print("\nSummary:")
    for intent, count in sorted(intents.items()):
        print(f"  {intent}: {count}")
    print(f"  TOTAL: {len(scenarios)}")

    # Count attachments
    total_att = sum(len(s.attachments) for s in scenarios)
    print(f"\n  Total attachments to generate: {total_att}")

    att_types: dict[str, int] = {}
    for s in scenarios:
        for a in s.attachments:
            att_types[a.file_type] = att_types.get(a.file_type, 0) + 1
    if att_types:
        for ft, count in sorted(att_types.items()):
            print(f"    {ft}: {count}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HouseKeep AI — Synthetic Test Data Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--hoa-email", help="HOA inbox email address")
    parser.add_argument("--client-id", help="Google OAuth client ID")
    parser.add_argument("--client-secret", help="Google OAuth client secret")
    parser.add_argument("--hoa-token", help="OAuth refresh token for HOA Gmail account")
    parser.add_argument("--sender-token", help="OAuth refresh token for test sender account")
    parser.add_argument("--database-url", help="PostgreSQL connection URL")
    parser.add_argument(
        "--method",
        choices=["send", "insert"],
        default="send",
        help="Injection method (default: send)",
    )
    parser.add_argument(
        "--scenarios",
        help="Comma-separated scenario names, or 'all' (default: all)",
        default="all",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between injections (default: 2.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and print summary without injecting",
    )
    parser.add_argument(
        "--setup-residents-only",
        action="store_true",
        help="Only insert test residents into DB",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove test data from DB before running",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="After injection, verify results in DB",
    )
    parser.add_argument(
        "--output-json",
        help="Write injection results to a JSON file",
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Resolve database URL from args, env, or .env file
    db_url = args.database_url or os.environ.get("DATABASE_URL")

    # Select scenarios
    if args.scenarios == "all":
        scenarios = ALL_SCENARIOS
    else:
        names = [n.strip() for n in args.scenarios.split(",")]
        scenarios = []
        for name in names:
            if name in SCENARIO_BY_NAME:
                scenarios.append(SCENARIO_BY_NAME[name])
            else:
                logger.error("Unknown scenario: %s", name)
                sys.exit(1)

    # Dry run
    if args.dry_run:
        print_dry_run(scenarios)
        return

    # Clean
    if args.clean:
        if not db_url:
            logger.error("--database-url required for --clean")
            sys.exit(1)
        await clean_test_data(db_url)

    # Setup residents
    if args.setup_residents_only:
        if not db_url:
            logger.error("--database-url required for --setup-residents-only")
            sys.exit(1)
        await setup_residents(db_url)
        return

    # Full injection
    if not args.hoa_email:
        logger.error("--hoa-email is required for injection")
        sys.exit(1)

    if not args.client_id or not args.client_secret:
        # Try to load from env
        args.client_id = args.client_id or os.environ.get("GMAIL_CLIENT_ID", "")
        args.client_secret = args.client_secret or os.environ.get("GMAIL_CLIENT_SECRET", "")

    if not args.client_id or not args.client_secret:
        logger.error("--client-id and --client-secret required (or set GMAIL_CLIENT_ID/GMAIL_CLIENT_SECRET)")
        sys.exit(1)

    # Setup residents if DB URL provided
    if db_url:
        await setup_residents(db_url)

    # Import here to avoid requiring google libs for dry-run
    from scripts.testdata.injector import GmailInjector

    injector = GmailInjector(
        client_id=args.client_id,
        client_secret=args.client_secret,
        hoa_email=args.hoa_email,
        hoa_refresh_token=args.hoa_token or os.environ.get("GMAIL_REFRESH_TOKEN"),
        sender_refresh_token=args.sender_token,
    )

    logger.info(
        "Injecting %d scenarios via %s (delay=%.1fs)",
        len(scenarios),
        args.method,
        args.delay,
    )
    results = await injector.inject_all(scenarios, method=args.method, delay=args.delay)

    # Print results
    print("\n" + "=" * 80)
    print(f"{'SCENARIO':<35} {'INTENT':<15} {'GMAIL ID':<20} {'STATUS':<10}")
    print("=" * 80)
    for r in results:
        gid = r["gmail_id"][:16] + "..." if len(r["gmail_id"]) > 16 else r["gmail_id"]
        print(f"{r['scenario']:<35} {r['intent']:<15} {gid:<20} {r['status']:<10}")
    print("=" * 80)

    ok_count = sum(1 for r in results if r["status"] == "ok")
    err_count = len(results) - ok_count
    print(f"\n{ok_count} injected successfully, {err_count} errors\n")

    # Save results
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(results, f, indent=2)
        logger.info("Results saved to %s", args.output_json)

    # Verify
    if args.verify:
        if not db_url:
            logger.error("--database-url required for --verify")
            sys.exit(1)
        logger.info("Waiting 10 seconds for pipeline processing...")
        await asyncio.sleep(10)
        await verify_results(db_url, results)


if __name__ == "__main__":
    asyncio.run(main())
