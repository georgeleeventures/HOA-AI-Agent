"""Management CLI for HouseKeep AI platform operations."""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def create_hoa(args):
    import asyncpg

    conn = await asyncpg.connect(args.database_url or os.environ.get("DATABASE_URL"))
    try:
        row = await conn.fetchrow(
            """INSERT INTO hoas (name, slug, email_address)
               VALUES ($1, $2, $3)
               ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
               RETURNING id, name, slug""",
            args.name,
            args.slug,
            f"board@{args.slug}.housekeep.click",
        )
        print(f"HOA created: {row['name']} (slug={row['slug']}, id={row['id']})")

        if args.admin_email:
            await conn.execute(
                """INSERT INTO residents (hoa_id, email, name, role, is_authorized)
                   VALUES ($1, $2, $3, 'admin', TRUE)
                   ON CONFLICT (hoa_id, email) DO UPDATE SET role = 'admin', is_authorized = TRUE""",
                row["id"],
                args.admin_email,
                args.admin_name or args.admin_email,
            )
            print(f"Admin added: {args.admin_email}")
    finally:
        await conn.close()


async def list_hoas(args):
    import asyncpg

    conn = await asyncpg.connect(args.database_url or os.environ.get("DATABASE_URL"))
    try:
        rows = await conn.fetch(
            "SELECT id, name, slug, email_address, is_active, created_at FROM hoas ORDER BY created_at"
        )
        if not rows:
            print("  No HOAs found.")
            return
        for r in rows:
            status = "active" if r["is_active"] else "inactive"
            email = r["email_address"] or "no email"
            print(f"  {r['slug']:<20} {r['name']:<30} {email:<40} [{status}]")
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description="HouseKeep AI Management CLI")
    parser.add_argument("--database-url", help="PostgreSQL URL")
    sub = parser.add_subparsers(dest="command")

    create = sub.add_parser("create-hoa", help="Create a new HOA")
    create.add_argument("--name", required=True, help="HOA display name")
    create.add_argument("--slug", required=True, help="Subdomain slug")
    create.add_argument("--admin-email", help="First admin email")
    create.add_argument("--admin-name", help="First admin name")

    sub.add_parser("list-hoas", help="List all HOAs")

    args = parser.parse_args()
    if args.command == "create-hoa":
        asyncio.run(create_hoa(args))
    elif args.command == "list-hoas":
        asyncio.run(list_hoas(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
