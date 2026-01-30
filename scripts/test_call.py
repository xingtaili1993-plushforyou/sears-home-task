#!/usr/bin/env python3
"""
Test script to make an outbound test call.

Usage:
    python scripts/test_call.py --to +1234567890

This will initiate a call from your Twilio number to test the voice agent.
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from twilio.rest import Client
    from dotenv import load_dotenv
except ImportError:
    print("Please install required packages: pip install twilio python-dotenv")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Make a test call")
    parser.add_argument(
        "--to",
        required=True,
        help="Phone number to call (e.g., +1234567890)"
    )
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    
    if not all([account_sid, auth_token, from_number]):
        print("Error: Twilio credentials must be set in .env")
        sys.exit(1)
    
    client = Client(account_sid, auth_token)
    
    print(f"Making call from {from_number} to {args.to}")
    print(f"Using webhook URL: {base_url}/voice/incoming-call")
    
    try:
        call = client.calls.create(
            to=args.to,
            from_=from_number,
            url=f"{base_url}/voice/incoming-call",
            method="POST",
            status_callback=f"{base_url}/voice/call-status",
            status_callback_method="POST"
        )
        
        print(f"\n✓ Call initiated!")
        print(f"  Call SID: {call.sid}")
        print(f"  Status: {call.status}")
        print("\nThe phone should ring shortly...")
        
    except Exception as e:
        print(f"\n✗ Failed to make call: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
