#!/usr/bin/env python3
"""
Setup script for configuring Twilio webhooks.

Usage:
    python scripts/setup_twilio.py --base-url https://your-ngrok-url.ngrok.io

This script will:
1. Verify your Twilio credentials
2. List your phone numbers
3. Configure the voice webhook for incoming calls
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
    parser = argparse.ArgumentParser(description="Configure Twilio for Voice AI")
    parser.add_argument(
        "--base-url",
        required=True,
        help="Your public base URL (e.g., https://abc123.ngrok.io)"
    )
    parser.add_argument(
        "--phone-number",
        help="Specific phone number to configure (optional)"
    )
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env")
        sys.exit(1)
    
    # Initialize client
    client = Client(account_sid, auth_token)
    
    print("=" * 60)
    print("Twilio Voice AI Configuration")
    print("=" * 60)
    
    # Verify credentials
    try:
        account = client.api.accounts(account_sid).fetch()
        print(f"\n✓ Connected to Twilio account: {account.friendly_name}")
    except Exception as e:
        print(f"\n✗ Failed to connect to Twilio: {e}")
        sys.exit(1)
    
    # List phone numbers
    print("\nAvailable phone numbers:")
    phone_numbers = client.incoming_phone_numbers.list(limit=20)
    
    if not phone_numbers:
        print("  No phone numbers found. Please purchase a phone number first.")
        sys.exit(1)
    
    for i, number in enumerate(phone_numbers, 1):
        print(f"  {i}. {number.phone_number} ({number.friendly_name})")
    
    # Determine which number to configure
    target_number = None
    if args.phone_number:
        for number in phone_numbers:
            if number.phone_number == args.phone_number:
                target_number = number
                break
        if not target_number:
            print(f"\n✗ Phone number {args.phone_number} not found")
            sys.exit(1)
    else:
        target_number = phone_numbers[0]
        print(f"\nUsing first phone number: {target_number.phone_number}")
    
    # Configure webhook URLs
    voice_url = f"{args.base_url}/voice/incoming-call"
    status_url = f"{args.base_url}/voice/call-status"
    
    print(f"\nConfiguring webhooks:")
    print(f"  Voice URL: {voice_url}")
    print(f"  Status URL: {status_url}")
    
    try:
        target_number.update(
            voice_url=voice_url,
            voice_method="POST",
            status_callback=status_url,
            status_callback_method="POST"
        )
        print("\n✓ Webhook configuration updated successfully!")
    except Exception as e:
        print(f"\n✗ Failed to update webhook: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Configuration Complete!")
    print("=" * 60)
    print(f"\nYour Voice AI agent is ready at: {target_number.phone_number}")
    print("\nTo test:")
    print(f"  1. Make sure your server is running at {args.base_url}")
    print(f"  2. Call {target_number.phone_number}")
    print("  3. Start talking to the AI agent!")
    print("\nNote: Update BASE_URL in your .env file to match your ngrok URL")


if __name__ == "__main__":
    main()
