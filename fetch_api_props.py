#!/usr/bin/env python3
"""
MasterProps.ai — DBbet API Prop Fetcher
Fetches real events + odds from DBbet Marketing API,
filters for high-value props (x10+), and outputs a prop pool
that generate_offline.py can consume.
"""

import json
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── API Config ──
TOKEN_URL = "https://cpservm.com/gateway/token"
API_BASE = "https://cpservm.com/gateway/marketing/datafeed/prematch/api/v2"
CLIENT_ID = "partners-3151f4df3df18d1d17e3eae7a6c43792"
CLIENT_SECRET = "LDnyHnPGpVdar!gId431qn&YQRAZg!D5A1R010T5rk0F3ciWT1CHreULFN2Ly3Ck"
REF = "164"
PARTNER_LINK = "refpa1800.com"

# ── Sport config ──
SPORT_MAP = {
    1: 'futbol',
    2: 'hockey',
    3: 'nba',
    4: 'tenis',
    5: 'mlb',
    189: 'ufc',
}

SPORT_EMOJI = {
    'futbol': '⚽',
    'hockey': '🏒',
    'nba': '🏀',
    'tenis': '🎾',
    'mlb': '⚾',
    'ufc': '🥊',
}

# ── Odds filtering ──
MIN_ODD = 10.0       # minimum odds for a prop (x10)
MAX_ODD = 100.0      # maximum odds cap
MIN_LEG_ODD = 1.5    # minimum per-leg odd for building parlays
MAX_LEG_ODD = 5.0    # max per-leg odd

# Props that are interesting for tickets (not just correct scores)
INTERESTING_TYPES = {
    # 1X2
    1, 2, 3,       # W1, X, W2
    4, 5, 6,       # 1X, 12, 2X
    # Handicap
    7, 8,           # Handicap 1, Handicap 2
    # Totals
    9, 10,          # Total Over, Total Under
    # Both teams to score
    15, 16,         # BTTS Yes, BTTS No (common types)
    # HT/FT combos - various types
    401, 402,       # First/Second Team Wins (basketball)
}

# Display name filters for interesting high-odds props
INTERESTING_KEYWORDS = [
    'Handicap', 'Total', 'Both Teams', 'HT-FT', 'Win And Total',
    'Individual Total', 'Race To', 'W1', 'W2', 'To Win',
    'Next Goal', 'Clean Sheet', 'Win To Nil',
]


OUTPUT_FILE = Path(__file__).parent / 'api_props.json'


def get_token():
    """Get OAuth2 access token."""
    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, headers={
        'Content-Type': 'application/x-www-form-urlencoded'
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result['access_token']
    except Exception as e:
        print(f"❌ Error getting token: {e}")
        sys.exit(1)


def fetch_events(token):
    """Fetch all events with full odds."""
    url = (f"{API_BASE}/sportevents?"
           f"ref={REF}"
           f"&SchemeOfGettingOddsOperations=GetAllOdds"
           f"&partnerLink={PARTNER_LINK}")

    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}'
    })

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"❌ Error fetching events: {e}")
        sys.exit(1)


def is_interesting_prop(odd):
    """Check if an odd is an interesting prop for MasterProps."""
    display = odd.get('display', '')

    # Skip blocked odds
    if odd.get('isBlocked', False):
        return False

    # Check if display contains interesting keywords
    for kw in INTERESTING_KEYWORDS:
        if kw.lower() in display.lower():
            return True

    return False


def extract_team_abbrev(name):
    """Extract a short team abbreviation from full name."""
    # Common mappings
    abbrevs = {
        'Real Madrid': 'RMA', 'Barcelona': 'BAR', 'Atletico Madrid': 'ATM',
        'Manchester City': 'MCI', 'Manchester United': 'MUN', 'Liverpool': 'LIV',
        'Arsenal': 'ARS', 'Chelsea': 'CHE', 'Tottenham': 'TOT',
        'Bayern': 'BAY', 'Dortmund': 'BVB', 'Juventus': 'JUV',
        'Inter': 'INT', 'AC Milan': 'MIL', 'Paris': 'PSG',
        'Fiorentina': 'FIO', 'Atalanta': 'ATA', 'Roma': 'ROM',
        'Napoli': 'NAP', 'Lazio': 'LAZ', 'Bologna': 'BOL',
        'Colorado Avalanche': 'COL', 'Vegas Golden Knights': 'VGK',
    }

    for full, abbr in abbrevs.items():
        if full.lower() in name.lower():
            return abbr

    # Fallback: first 3 chars uppercase
    words = name.split()
    if len(words) >= 2:
        return (words[0][:2] + words[1][0]).upper()
    return name[:3].upper()


def translate_display(display):
    """Translate English display names to Spanish prop descriptions."""
    d = display

    # Simple translations
    translations = {
        'Over': 'Más de', 'Under': 'Menos de',
        'Total': 'Total', 'Handicap': 'Hándicap',
        'Both Teams To Score - Yes': 'Ambos anotan - Sí',
        'Both Teams To Score - No': 'Ambos anotan - No',
        'Win And Total': 'Gana y Total',
        'Individual Total': 'Total Individual',
        'Race To': 'Primero en llegar a',
        'Goals': 'goles',
        'Clean Sheet': 'Portería invicta',
        'Win To Nil': 'Gana sin recibir gol',
        'HT-FT': 'MT-FT',
        'Team 1': 'Equipo 1',
        'Team 2': 'Equipo 2',
    }

    for en, es in translations.items():
        d = d.replace(en, es)

    return d


def build_prop_pool(data):
    """Build a prop pool from API events data."""
    props = []

    for event in data.get('items', []):
        sport_id = event.get('sportId', 0)
        sport = SPORT_MAP.get(sport_id, f'sport_{sport_id}')

        team1 = event.get('opponent1NameLocalization', 'Team A')
        team2 = event.get('opponent2NameLocalization', 'Team B')
        match_name = f"{team1} vs {team2}"
        tournament = event.get('tournamentNameLocalization', '')
        link = event.get('link', '')
        start_ts = event.get('startDate', 0)

        # Convert timestamp to date string
        if start_ts:
            dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
            date_str = dt.strftime('%b %d')
        else:
            date_str = 'TBD'

        team1_abbr = extract_team_abbrev(team1)
        team2_abbr = extract_team_abbrev(team2)

        for odd in event.get('oddsLocalization', []):
            odds_value = odd.get('oddsMarket', 0)

            if not is_interesting_prop(odd):
                continue

            display = odd.get('display', '')

            # Determine which team is referenced
            if '1' in display and '2' not in display:
                team_abbr = team1_abbr
            elif '2' in display and '1' not in display:
                team_abbr = team2_abbr
            else:
                team_abbr = team1_abbr  # default to team1

            prop_entry = {
                'player': team1 if '1' in display else team2 if '2' in display else team1,
                'prop': translate_display(display),
                'match': match_name,
                'odd': round(odds_value, 2),
                'sport': sport,
                'team': team_abbr,
                'date': date_str,
                'tournament': tournament,
                'link': link,
                'api_type': odd.get('type', 0),
                'param': odd.get('parameter', 0),
            }

            props.append(prop_entry)

    return props


def categorize_props(props):
    """Categorize props into buckets for ticket generation."""

    # High value singles (x10+)
    high_value = [p for p in props if p['odd'] >= MIN_ODD and p['odd'] <= MAX_ODD]

    # Parlay legs (x1.5 - x5.0 range)
    parlay_legs = [p for p in props if MIN_LEG_ODD <= p['odd'] <= MAX_LEG_ODD]

    return {
        'high_value': sorted(high_value, key=lambda x: x['odd'], reverse=True),
        'parlay_legs': sorted(parlay_legs, key=lambda x: x['odd'], reverse=True),
        'total_props': len(props),
    }


def main():
    print("🚀 MasterProps API Fetcher")
    print("=" * 50)

    # 1. Get token
    print("🔑 Getting OAuth2 token...")
    token = get_token()
    print("✅ Token obtained")

    # 2. Fetch events
    print("📡 Fetching events with odds...")
    data = fetch_events(token)
    event_count = data.get('count', 0)
    print(f"✅ Got {event_count} events")

    # 3. Build prop pool
    print("🎯 Building prop pool...")
    all_props = build_prop_pool(data)
    print(f"✅ {len(all_props)} interesting props found")

    # 4. Categorize
    categorized = categorize_props(all_props)
    print(f"   🔥 High value (x10+): {len(categorized['high_value'])}")
    print(f"   🎰 Parlay legs (x1.5-5): {len(categorized['parlay_legs'])}")

    # 5. Save
    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'event_count': event_count,
        'props': all_props,
        'stats': {
            'total_props': len(all_props),
            'high_value': len(categorized['high_value']),
            'parlay_legs': len(categorized['parlay_legs']),
        }
    }

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\n💾 Saved to {OUTPUT_FILE}")

    # 6. Show sample
    print("\n🎯 Top 10 high-value props:")
    for p in categorized['high_value'][:10]:
        emoji = SPORT_EMOJI.get(p['sport'], '🎯')
        print(f"  {emoji} x{p['odd']:.1f} | {p['prop']} | {p['match'][:40]} | {p['tournament']}")

    print("\n🎰 Sample parlay legs:")
    for p in categorized['parlay_legs'][:10]:
        emoji = SPORT_EMOJI.get(p['sport'], '🎯')
        print(f"  {emoji} x{p['odd']:.2f} | {p['prop']} | {p['match'][:40]}")


if __name__ == '__main__':
    main()
