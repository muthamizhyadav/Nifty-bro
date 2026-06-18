"""
FYERS ACCESS TOKEN GENERATOR
=============================
Run ONCE every 15 days to refresh your token.

═══════════════════════════════════════════════════════════════
REDIRECT URL — CRITICAL SETUP STEP
═══════════════════════════════════════════════════════════════

When you create your Fyers App at https://myapi.fyers.in/dashboard:

   ★ REDIRECT URL: https://trade.fyers.in/api-login/redirect-uri/index.html

That's the EXACT URL you must enter. Don't use google.com or anything else.

This is Fyers' official redirect handler — it displays your auth code
cleanly after login so you can copy it.

═══════════════════════════════════════════════════════════════
SETUP WALKTHROUGH (do once)
═══════════════════════════════════════════════════════════════

1. Go to: https://myapi.fyers.in/dashboard
2. Click "Create App"
3. Fill in:
   • App Name: NiftyBot
   • Redirect URL: https://trade.fyers.in/api-login/redirect-uri/index.html
   • App Type: Personal
   • Permissions: Tick Data, Order placement, Holdings
4. Submit → you'll get:
   • App ID (e.g. ABC123-100)
   • Secret Key

5. Edit config.py and paste them:
   "fyers_app_id": "YOUR_APP_ID_HERE-100",
   "fyers_secret_key": "YOUR_SECRET_KEY_HERE",

6. Run this script:
   python fyers_auth.py

7. Browser opens → login → 2FA → you'll see auth_code on page
8. Copy the FULL URL (or just the auth_code) → paste back here
9. Script saves token to config.py automatically

═══════════════════════════════════════════════════════════════
"""

import webbrowser
import hashlib
import requests
import re
from urllib.parse import urlparse, parse_qs

# Hardcoded Fyers redirect URL — use this when creating your app
FYERS_REDIRECT_URL = "https://trade.fyers.in/api-login/redirect-uri/index.html"


def generate_token():
    print("=" * 65)
    print("  FYERS TOKEN GENERATOR")
    print("=" * 65)
    print(f"\n  Redirect URL (set this in Fyers app): \n  {FYERS_REDIRECT_URL}\n")
    print("=" * 65)

    try:
        from config import CONFIG
    except ImportError:
        print("\n❌ ERROR: config.py not found. Make sure you're in the backend folder.")
        return

    app_id = CONFIG.get("fyers_app_id", "")
    secret = CONFIG.get("fyers_secret_key", "")

    if not app_id or "YOUR_" in app_id:
        print("\n❌ ERROR: Set 'fyers_app_id' in config.py first")
        print("\nGet it from: https://myapi.fyers.in/dashboard")
        return
    if not secret or "YOUR_" in secret:
        print("\n❌ ERROR: Set 'fyers_secret_key' in config.py first")
        return

    # Step 1: Build auth URL
    auth_url = (
        f"https://api-t1.fyers.in/api/v3/generate-authcode"
        f"?client_id={app_id}"
        f"&redirect_uri={FYERS_REDIRECT_URL}"
        f"&response_type=code"
        f"&state=niftybot"
    )

    print(f"\n  Opening browser for Fyers login...")
    print(f"  If browser doesn't open, copy this URL:\n  {auth_url}\n")

    try:
        webbrowser.open(auth_url)
    except:
        pass

    print("=" * 65)
    print("\n  After login, you'll see a page showing your auth_code.")
    print("  Copy either:")
    print("    • Just the auth_code value")
    print("    • OR the entire URL from the address bar\n")

    user_input = input("  Paste auth_code or URL here: ").strip()

    # Extract auth code (works whether they paste URL or just code)
    auth_code = None
    if "auth_code=" in user_input:
        parsed = urlparse(user_input)
        params = parse_qs(parsed.query)
        auth_code = params.get("auth_code", [None])[0]
    elif "code=" in user_input:
        parsed = urlparse(user_input)
        params = parse_qs(parsed.query)
        auth_code = params.get("code", [None])[0]
    else:
        # User pasted just the code
        auth_code = user_input.strip()

    if not auth_code or len(auth_code) < 20:
        print("\n❌ ERROR: Could not extract valid auth_code")
        return

    print(f"\n  ✓ Got auth code")

    # Step 2: Exchange for access token
    app_id_hash = hashlib.sha256(f"{app_id}:{secret}".encode()).hexdigest()

    print(f"  ⏳ Exchanging for access token...")

    try:
        r = requests.post(
            "https://api-t1.fyers.in/api/v3/validate-authcode",
            json={
                "grant_type": "authorization_code",
                "appIdHash": app_id_hash,
                "code": auth_code
            },
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        data = r.json()
    except Exception as e:
        print(f"\n❌ ERROR: Network/API failure — {e}")
        return

    if data.get("s") != "ok":
        print(f"\n❌ ERROR: {data.get('message', 'Token generation failed')}")
        print(f"   Full response: {data}")
        return

    access_token = data["access_token"]
    print(f"\n  ✓ Access token generated (valid 15 days)")
    print(f"\n  Token (first 40 chars): {access_token[:40]}...")

    # Step 3: Auto-update config.py
    try:
        with open("config.py", "r") as f:
            content = f.read()
        new_content = re.sub(
            r'"fyers_access_token":\s*"[^"]*"',
            f'"fyers_access_token": "{access_token}"',
            content
        )
        with open("config.py", "w") as f:
            f.write(new_content)
        print(f"\n  ✓ config.py updated automatically")
    except Exception as e:
        print(f"\n⚠️  Could not auto-update config.py: {e}")
        print(f"   Manually set in config.py:")
        print(f'   "fyers_access_token": "{access_token}"')

    print("\n" + "=" * 65)
    print(f"  ✓ DONE — token valid for 15 days")
    print(f"  Now run: python bot.py")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    generate_token()
