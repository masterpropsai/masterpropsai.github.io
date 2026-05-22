#!/usr/bin/env python3
"""
MasterProps.ai — Coupon Code Generator
Uses Playwright to generate valid DBbet coupon codes via the app's own $httpModule.
The $httpModule adds the critical x-hd security header that makes codes valid.
"""

import json
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
COUPONS_FILE = BASE_DIR / 'coupons.json'
TICKETS_DATA_FILE = BASE_DIR / 'tickets_data.json'

DBBET_URL = "https://db-bet.com/es"
PARTNER_ID = 164


def generate_coupon_codes(tickets_data: list[dict]) -> dict[str, str]:
    """
    Generate valid coupon codes for each ticket using Playwright.

    tickets_data: list of dicts with:
      - ticket_id: str (e.g. "S1")
      - events: list of dicts with GameId, Type, Coef, Param, PlayerId

    Returns: dict of ticket_id → coupon_code
    """
    from playwright.sync_api import sync_playwright

    codes = {}

    with sync_playwright() as p:
        print("🌐 Launching headless browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"📡 Navigating to {DBBET_URL}...")
        page.goto(DBBET_URL, wait_until="networkidle", timeout=30000)

        # Wait for Vue app to be fully loaded
        print("⏳ Waiting for Vue app to initialize...")
        page.wait_for_function(
            "() => !!document.querySelector('#__BETTING_APP__')?.__vue_app__",
            timeout=20000
        )
        # Extra wait for $httpModule hooks to be fully registered
        page.wait_for_timeout(2000)

        print(f"✅ App loaded. Generating {len(tickets_data)} coupon codes...\n")

        for ticket in tickets_data:
            tid = ticket['ticket_id']
            events = ticket['events']

            if not events:
                print(f"  ⚠️  {tid}: no events, skipping")
                continue

            # Build the SaveCoupon request body
            save_body = {
                "notWait": True,
                "CheckCf": 1,
                "partner": PARTNER_ID,
                "AntiExpressCoef": 2,
                "Summ": 100,
                "Events": [
                    {
                        "GameId": ev["GameId"],
                        "Type": ev["Type"],
                        "Coef": ev["Coef"],
                        "Param": ev.get("Param", 0),
                        "PV": None,
                        "PlayerId": ev.get("PlayerId", 0),
                        "Kind": 3,  # prematch
                        "InstrumentId": 0,
                        "Seconds": 0,
                        "Price": 0,
                        "Expired": 0,
                        "PlayersDuel": []
                    }
                    for ev in events
                ],
                "Vid": 0
            }

            # Call SaveCoupon through the app's $httpModule (includes x-hd header)
            js_code = f"""
            async () => {{
                const app = document.querySelector('#__BETTING_APP__').__vue_app__;
                const httpModule = app.config.globalProperties.$httpModule;
                const body = {json.dumps(save_body)};

                const request = httpModule('https://db-bet.com/service-api/LiveBet/Open/SaveCoupon', {{
                    method: 'POST',
                    body: JSON.stringify(body),
                    headers: {{
                        'content-type': 'application/json',
                        'accept': 'application/json, text/plain, */*'
                    }}
                }});

                try {{
                    const result = await request.execute();
                    return JSON.stringify(result);
                }} catch(e) {{
                    return JSON.stringify({{Success: false, Error: e.message || String(e)}});
                }}
            }}
            """

            try:
                result_str = page.evaluate(js_code)
                result = json.loads(result_str)

                if result.get('Success') and result.get('Value'):
                    code = result['Value']
                    codes[tid] = code
                    legs_str = ", ".join(f"G{ev['GameId']}" for ev in events)
                    print(f"  ✅ {tid}: {code} ({len(events)} legs: {legs_str})")
                else:
                    error = result.get('Error', 'Unknown error')
                    print(f"  ❌ {tid}: Failed - {error}")

            except Exception as e:
                print(f"  ❌ {tid}: Exception - {e}")

            # Small delay between requests to avoid rate limiting
            page.wait_for_timeout(500)

        browser.close()

    return codes


def main():
    """Generate coupon codes from tickets_data.json and save to coupons.json."""
    print("🎫 MasterProps Coupon Code Generator")
    print("=" * 50)

    if not TICKETS_DATA_FILE.exists():
        print(f"❌ {TICKETS_DATA_FILE} not found. Run generate_live.py first.")
        sys.exit(1)

    tickets_data = json.loads(TICKETS_DATA_FILE.read_text(encoding='utf-8'))
    print(f"📋 {len(tickets_data)} tickets to process\n")

    codes = generate_coupon_codes(tickets_data)

    # Merge with existing coupons
    existing = {}
    if COUPONS_FILE.exists():
        try:
            existing = json.loads(COUPONS_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass

    existing.update(codes)
    COUPONS_FILE.write_text(json.dumps(existing, indent=2), encoding='utf-8')

    print(f"\n{'=' * 50}")
    print(f"🎉 Generated {len(codes)}/{len(tickets_data)} coupon codes")
    print(f"📁 Saved to {COUPONS_FILE}")

    # Show deep links
    print(f"\n🔗 Deep links:")
    for tid, code in codes.items():
        print(f"  {tid}: https://db-bet.com/es?load={code}")


if __name__ == '__main__':
    main()
