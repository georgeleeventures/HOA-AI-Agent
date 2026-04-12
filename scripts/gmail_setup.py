#!/usr/bin/env python3
"""One-time Gmail OAuth2 setup script.

Run this interactively to authorize HouseKeep AI to access the HOA's Gmail account.
It opens a browser for the admin to sign in and grant access, then prints the
refresh token to add to the .env file.

Usage:
    python scripts/gmail_setup.py --client-id YOUR_CLIENT_ID --client-secret YOUR_SECRET

Or set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables.
"""

import argparse
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def main():
    parser = argparse.ArgumentParser(description="Gmail OAuth2 Setup for HouseKeep AI")
    parser.add_argument("--client-id", default=os.environ.get("GMAIL_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.environ.get("GMAIL_CLIENT_SECRET"))
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if not args.client_id or not args.client_secret:
        print("Error: Provide --client-id and --client-secret, or set")
        print("GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables.")
        return

    # Build OAuth2 flow from client config
    client_config = {
        "installed": {
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"http://localhost:{args.port}"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    credentials = flow.run_local_server(port=args.port)

    print("\n" + "=" * 60)
    print("SUCCESS! Add this to your .env file:")
    print("=" * 60)
    print(f"\nGMAIL_REFRESH_TOKEN={credentials.refresh_token}\n")
    print("=" * 60)
    print("The HOA Gmail account is now connected to HouseKeep AI.")
    print("This refresh token does not expire unless revoked.")


if __name__ == "__main__":
    main()
