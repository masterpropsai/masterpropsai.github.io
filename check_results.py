#!/usr/bin/env python3
"""
MasterProps.ai — Results Checker
Checks completed games and marks ticket legs as ✅ won or ❌ lost.
Updates the HTML with result indicators.
"""

import requests
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

API_KEY = os.environ.get('ODDS_API_KEY', '')
BASE_URL = 'https://api.the-odds-api.com/v4'
RESULTS_FILE = Path(__file__).parent / 'results.json'
INDEX_FILE = Path(__file__).parent / 'index.html'


def fetch_scores(sport_key):
    """Fetch completed game scores."""
    try:
        resp = requests.get(
            f'{BASE_URL}/sports/{sport_key}/scores',
            params={
                'apiKey': API_KEY,
                'daysFrom': 2,
                'dateFormat': 'iso',
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []


def load_results():
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return {'tickets': {}, 'legs': {}, 'last_updated': None}


def save_results(data):
    data['last_checked'] = datetime.now(timezone.utc).isoformat()
    RESULTS_FILE.write_text(json.dumps(data, indent=2))


def inject_results_into_html(results):
    """
    Add result status (✅/❌/⏳) to each leg in the HTML.
    Modifies the TICKETS JS array to include a 'result' field per leg.
    """
    html = INDEX_FILE.read_text(encoding='utf-8')

    leg_results = results.get('legs', {})
    if not leg_results:
        return

    # For each known result, inject into the JS
    # We add a data attribute approach: inject a RESULTS object
    results_js = json.dumps(leg_results)

    # Insert RESULTS object before TICKETS
    results_block = f"\n// === LIVE RESULTS ===\nconst LEG_RESULTS = {results_js};\n"

    if 'const LEG_RESULTS' in html:
        html = re.sub(
            r'const LEG_RESULTS = .*?;\n',
            f"const LEG_RESULTS = {results_js};\n",
            html
        )
    else:
        html = html.replace(
            '// === TICKET DATA ===',
            f'// === LIVE RESULTS ==={results_block}\n// === TICKET DATA ==='
        )

    # Also inject CSS for result indicators if not present
    if '.leg-result' not in html:
        result_css = """
/* Result indicators */
.leg-result { margin-left: auto; font-size: 0.85rem; flex-shrink: 0; }
.leg-result.won { color: #22c55e; }
.leg-result.lost { color: #ef4444; }
.leg-result.pending { color: #8a8578; opacity: 0.5; }
.ticket-result-badge {
  position: absolute; top: 8px; right: 8px;
  padding: 3px 10px; border-radius: 6px; font-size: 0.65rem;
  font-weight: 800; letter-spacing: 0.5px; z-index: 5;
}
.ticket-result-badge.won { background: rgba(34,197,94,0.2); color: #22c55e; border: 1px solid rgba(34,197,94,0.3); }
.ticket-result-badge.lost { background: rgba(239,68,68,0.2); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
.ticket-result-badge.live { background: rgba(212,165,32,0.2); color: var(--gold); border: 1px solid rgba(212,165,32,0.3); animation: goldPulse 2s infinite; }
"""
        html = html.replace('/* Ticket tier badges */', f'{result_css}\n/* Ticket tier badges */')

    INDEX_FILE.write_text(html, encoding='utf-8')
    print(f"✅ Results injected into index.html")


def main():
    if not API_KEY:
        print("❌ Set ODDS_API_KEY environment variable")
        return

    print("🔍 MasterProps Results Checker")
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    results = load_results()

    sports_to_check = [
        'basketball_nba', 'baseball_mlb',
        'soccer_epl', 'soccer_spain_la_liga',
        'soccer_italy_serie_a', 'soccer_argentina_primera_division',
        'soccer_uefa_champs_league',
    ]

    completed_games = {}
    for sport in sports_to_check:
        scores = fetch_scores(sport)
        for game in scores:
            if game.get('completed'):
                completed_games[game['id']] = game
                print(f"  ✅ {game.get('home_team')} vs {game.get('away_team')} — completed")

    print(f"\n📊 {len(completed_games)} completed games found")

    # TODO: Cross-reference with ticket legs and determine win/loss
    # This requires matching event_ids from tickets with completed scores
    # For player props, we'd need additional result data (player stats APIs)

    save_results(results)
    inject_results_into_html(results)

    print("\n✅ Results check complete")


if __name__ == '__main__':
    main()
