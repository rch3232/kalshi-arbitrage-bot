#!/usr/bin/env python3
"""
Quick authentication test script for debugging Kalshi API connection.
Run this to verify your API credentials are working before deploying.
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("="*70)
print("KALSHI API AUTHENTICATION TEST")
print("="*70)

# Check environment variables
api_key = os.getenv("KALSHI_API_KEY")
api_secret = os.getenv("KALSHI_API_SECRET")
base_url = os.getenv("KALSHI_API_BASE_URL", "https://api.elections.kalshi.com/trade-api/v2")

print(f"\n1. Environment Variables:")
print(f"   KALSHI_API_KEY: {'✅ Set' if api_key else '❌ Missing'}")
if api_key:
    print(f"   Key preview: {api_key[:15]}...")

print(f"   KALSHI_API_SECRET: {'✅ Set' if api_secret else '❌ Missing'}")
if api_secret:
    print(f"   Secret length: {len(api_secret)} characters")
    print(f"   Starts with '-----BEGIN': {api_secret.startswith('-----BEGIN')}")
    print(f"   Contains '\\n' (escaped): {'\\n' in api_secret}")
    print(f"   First 50 chars: {api_secret[:50]}...")

print(f"\n2. Testing Kalshi SDK Import:")
try:
    from kalshi_python import Configuration, KalshiClient as SDKClient
    print("   ✅ Kalshi SDK imported successfully")

    # Handle escaped newlines
    private_key = api_secret.replace('\\n', '\n')

    print(f"\n3. After newline processing:")
    print(f"   Key starts with '-----BEGIN': {private_key.startswith('-----BEGIN')}")
    print(f"   Number of lines: {len(private_key.split(chr(10)))}")

    print(f"\n4. Attempting to initialize SDK:")
    config = Configuration(
        host=base_url,
        api_key_id=api_key,
        private_key_pem=private_key
    )
    client = SDKClient(config)
    print("   ✅ SDK client initialized")

    print(f"\n5. Testing API call (get_markets):")
    response = client.get_markets(limit=5, status="open")

    # Handle different response types
    markets = None
    if hasattr(response, 'markets'):
        markets = response.markets
    elif isinstance(response, dict):
        markets = response.get("markets", [])
    elif isinstance(response, list):
        markets = response

    if markets:
        print(f"   ✅ Successfully fetched {len(markets)} markets!")
        if len(markets) > 0:
            print(f"   First market: {markets[0].get('ticker', 'N/A')}")
    else:
        print(f"   ⚠️  Got response but no markets: {type(response)}")

    print(f"\n6. Testing balance fetch:")
    balance = client.get_balance()
    print(f"   ✅ Balance fetched: {balance}")

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED - Your API credentials are working!")
    print("="*70)

except ImportError as e:
    print(f"   ❌ Kalshi SDK not installed: {e}")
    print("   Install with: pip install kalshi-python")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nFull error details:")
    import traceback
    traceback.print_exc()

    print("\n" + "="*70)
    print("TROUBLESHOOTING:")
    print("="*70)
    print("1. Make sure KALSHI_API_KEY is your API Key ID from Kalshi")
    print("2. Make sure KALSHI_API_SECRET contains your FULL private key")
    print("3. The private key should start with: -----BEGIN RSA PRIVATE KEY-----")
    print("4. If you pasted with literal \\n, the script will convert them")
    print("5. Try using actual newlines in your .env file instead of \\n")
