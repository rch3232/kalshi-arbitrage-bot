#!/usr/bin/env python3
"""
Helper script to convert your RSA private key to base64 (single line).
Use this if Render's environment variable field won't accept multi-line input.

Usage:
    python encode_key.py

Then paste the output into Render's KALSHI_API_SECRET field.
"""
import base64
import sys

print("="*70)
print("RSA PRIVATE KEY TO BASE64 CONVERTER")
print("="*70)
print("\nThis converts your multi-line private key to a single base64 string")
print("that's easier to paste into environment variables.")
print("\n" + "="*70)

print("\nPaste your FULL private key below (including -----BEGIN/END----- lines)")
print("When done, press Enter, then Ctrl+D (Mac/Linux) or Ctrl+Z (Windows):\n")

try:
    # Read multi-line input
    lines = []
    while True:
        try:
            line = input()
            lines.append(line)
        except EOFError:
            break

    private_key = '\n'.join(lines)

    if not private_key.strip():
        print("\n❌ No input received!")
        sys.exit(1)

    # Validate it looks like a private key
    if not private_key.startswith('-----BEGIN'):
        print("\n⚠️  Warning: This doesn't look like a PEM-formatted key")
        print("   Make sure you included the -----BEGIN RSA PRIVATE KEY----- line")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)

    # Encode to base64
    encoded = base64.b64encode(private_key.encode('utf-8')).decode('utf-8')

    print("\n" + "="*70)
    print("✅ SUCCESS - Your base64-encoded key:")
    print("="*70)
    print(f"\n{encoded}\n")
    print("="*70)
    print("\n📋 INSTRUCTIONS:")
    print("   1. Copy the base64 string above (just the letters/numbers)")
    print("   2. In Render, paste it as the value for KALSHI_API_SECRET")
    print("   3. The bot will automatically decode it on startup")
    print("\n✅ This is a SINGLE LINE - much easier to paste!")
    print("="*70)

    # Save to file as backup
    with open('private_key_base64.txt', 'w') as f:
        f.write(encoded)
    print("\n💾 Also saved to: private_key_base64.txt")

except KeyboardInterrupt:
    print("\n\n❌ Cancelled")
    sys.exit(1)
