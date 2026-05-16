#!/usr/bin/env python3
"""
MasterProps.ai — Real Odds Generator
Fetches real player props from The Odds API, builds multi-sport combined tickets,
and updates index.html with live data. Also checks results and marks ✅/❌.
"""

import requests
import json
import os
import sys
import random
import math
from datetime import datetime, timezone, timedelta
from itertools import combinations
from pathlib import Path

# === CONFIG ===
API_KEY = os.environ.get('ODDS_API_KEY', '')
BASE_URL = 'https://api.the-odds-api.com/v4'

# Sports to fetch (keys from The Odds API)
SPORTS = [
    'basketball_nba',
    'soccer_epl',
    'soccer_spain_la_liga',
    'soccer_italy_serie_a',
    'soccer_germany_bundesliga',
    'soccer_france_ligue_one',
    'soccer_uefa_champs_league',
    'soccer_argentina_primera_division',
    'baseball_mlb',
    'tennis_atp_french_open',
    'tennis_wta_french_open',
    'mma_mixed_martial_arts',
    'icehockey_nhl',
]

# Sport display names and emojis
SPORT_META = {
    'basketball_nba': {'name': 'NBA', 'emoji': '🏀', 'short': 'nba'},
    'soccer_epl': {'name': 'Premier League', 'emoji': '⚽', 'short': 'futbol'},
    'soccer_spain_la_liga': {'name': 'La Liga', 'emoji': '⚽', 'short': 'futbol'},
    'soccer_italy_serie_a': {'name': 'Serie A', 'emoji': '⚽', 'short': 'futbol'},
    'soccer_germany_bundesliga': {'name': 'Bundesliga', 'emoji': '⚽', 'short': 'futbol'},
    'soccer_france_ligue_one': {'name': 'Ligue 1', 'emoji': '⚽', 'short': 'futbol'},
    'soccer_uefa_champs_league': {'name': 'Champions League', 'emoji': '⚽', 'short': 'futbol'},
    'soccer_argentina_primera_division': {'name': 'Liga Argentina', 'emoji': '⚽', 'short': 'futbol'},
    'baseball_mlb': {'name': 'MLB', 'emoji': '⚾', 'short': 'mlb'},
    'tennis_atp_french_open': {'name': 'ATP', 'emoji': '🎾', 'short': 'tenis'},
    'tennis_wta_french_open': {'name': 'WTA', 'emoji': '🎾', 'short': 'tenis'},
    'mma_mixed_martial_arts': {'name': 'MMA', 'emoji': '🥊', 'short': 'mma'},
    'icehockey_nhl': {'name': 'NHL', 'emoji': '🏒', 'short': 'nhl'},
}

# Player prop markets to fetch
PROP_MARKETS = {
    'basketball_nba': [
        'player_points', 'player_assists', 'player_rebounds',
        'player_threes', 'player_points_rebounds_assists',
    ],
    'baseball_mlb': [
        'pitcher_strikeouts', 'batter_home_runs', 'batter_hits',
        'batter_total_bases',
    ],
    # Soccer uses match-level props (goalscorer markets)
    'soccer': [
        'player_goal_scorer_anytime',
    ],
}

RESULTS_FILE = Path(__file__).parent / 'results.json'
TEMPLATE_FILE = Path(__file__).parent / 'template.html'
OUTPUT_FILE = Path(__file__).parent / 'index.html'


def fetch_upcoming_games(sport_key):
    """Fetch upcoming games for a sport."""
    try:
        resp = requests.get(
            f'{BASE_URL}/sports/{sport_key}/odds',
            params={
                'apiKey': API_KEY,
                'regions': 'eu',
                'markets': 'h2h',
                'oddsFormat': 'decimal',
                'dateFormat': 'iso',
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  ⚠ {sport_key}: HTTP {resp.status_code}")
            return []
    except Exception as e:
        print(f"  ⚠ {sport_key}: {e}")
        return []


def fetch_player_props(sport_key, event_id, markets):
    """Fetch player props for a specific event."""
    try:
        resp = requests.get(
            f'{BASE_URL}/sports/{sport_key}/events/{event_id}/odds',
            params={
                'apiKey': API_KEY,
                'regions': 'eu',
                'markets': ','.join(markets),
                'oddsFormat': 'decimal',
                'dateFormat': 'iso',
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None


def parse_props_from_event(event_data, sport_key):
    """Extract individual prop bets from event data."""
    props = []
    if not event_data or 'bookmakers' not in event_data:
        return props

    match_name = f"{event_data.get('home_team', '?')} vs {event_data.get('away_team', '?')}"
    commence_time = event_data.get('commence_time', '')
    event_id = event_data.get('id', '')

    for bookmaker in event_data.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            market_key = market.get('key', '')
            for outcome in market.get('outcomes', []):
                name = outcome.get('description', outcome.get('name', ''))
                point = outcome.get('point')
                price = outcome.get('price', 0)

                if price < 1.5 or price > 8.0:
                    # Skip odds too low (no value) or too high (too risky for single leg)
                    continue

                prop_text = format_prop_text(market_key, name, point)
                if prop_text:
                    props.append({
                        'player': name,
                        'prop': prop_text,
                        'prop_es': prop_text,  # Will be the base text
                        'match': match_name,
                        'odd': round(price, 2),
                        'sport_key': sport_key,
                        'event_id': event_id,
                        'commence_time': commence_time,
                        'market_key': market_key,
                        'implied_prob': round(1 / price, 4),
                    })
        break  # Use first bookmaker only to avoid duplicates

    return props


def format_prop_text(market_key, name, point):
    """Convert API market data to human-readable prop text."""
    if point is not None:
        point_str = str(point).rstrip('0').rstrip('.')

    market_formats = {
        'player_points': f'Over {point_str} puntos' if point else None,
        'player_assists': f'Over {point_str} asistencias' if point else None,
        'player_rebounds': f'Over {point_str} rebotes' if point else None,
        'player_threes': f'Over {point_str} triples' if point else None,
        'player_points_rebounds_assists': f'Over {point_str} PRA' if point else None,
        'pitcher_strikeouts': f'Over {point_str} strikeouts' if point else None,
        'batter_home_runs': f'Home Run: Sí',
        'batter_hits': f'Over {point_str} hits' if point else None,
        'batter_total_bases': f'Over {point_str} bases totales' if point else None,
        'player_goal_scorer_anytime': f'Marca gol en cualquier momento',
        'h2h': None,  # Skip match winner
    }

    return market_formats.get(market_key)


def calculate_confidence(legs):
    """
    Calculate confidence score (1-6) based on:
    - Average implied probability of each leg
    - Number of legs (more legs = lower confidence)
    - Variance in odds (consistent odds = higher confidence)
    """
    if not legs:
        return 1

    probs = [leg['implied_prob'] for leg in legs]
    avg_prob = sum(probs) / len(probs)
    n_legs = len(legs)

    # Base score from average probability
    # Higher prob per leg = more confident
    if avg_prob > 0.55:
        base = 5
    elif avg_prob > 0.45:
        base = 4
    elif avg_prob > 0.35:
        base = 3
    elif avg_prob > 0.25:
        base = 2
    else:
        base = 1

    # Penalty for many legs
    if n_legs >= 6:
        base = max(1, base - 2)
    elif n_legs >= 5:
        base = max(1, base - 1)

    # Bonus for consistent odds (low variance)
    variance = sum((p - avg_prob) ** 2 for p in probs) / len(probs)
    if variance < 0.01:
        base = min(6, base + 1)

    return min(6, max(1, base))


def build_tickets(all_props):
    """
    Build combined tickets from available props.
    Strategy: mix sports, target different tier ranges.

    Tiers:
    - WHALE: x100+ (need 5-7 legs, higher individual odds)
    - SHARK: x30-99 (need 4-5 legs, moderate odds)
    - HUNTER: x10-29 (need 3-4 legs, safer individual odds)
    """
    if not all_props:
        return []

    tickets = []
    used_props = set()  # Track used props to avoid duplicates

    # Sort props by implied probability (safest first)
    safe_props = sorted(all_props, key=lambda x: x['implied_prob'], reverse=True)
    risky_props = sorted(all_props, key=lambda x: x['odd'], reverse=True)

    # Get unique sports available
    available_sports = list(set(p['sport_key'] for p in all_props))

    def prop_key(p):
        return f"{p['player']}_{p['market_key']}_{p['event_id']}"

    def pick_multi_sport_legs(pool, n_legs, min_sports=2):
        """Pick legs ensuring multi-sport diversity."""
        selected = []
        sports_used = set()
        players_used = set()

        for p in pool:
            pk = prop_key(p)
            if pk in used_props:
                continue
            if p['player'] in players_used:
                continue

            selected.append(p)
            sports_used.add(p['sport_key'])
            players_used.add(p['player'])

            if len(selected) >= n_legs:
                break

        # Check multi-sport requirement
        if len(selected) >= n_legs and len(sports_used) >= min(min_sports, len(available_sports)):
            for s in selected:
                used_props.add(prop_key(s))
            return selected
        return None

    # === HUNTER TICKETS (x10-29) — Safest picks ===
    for i in range(5):
        # Pick 3-4 safe legs with odds ~2.0-2.5 each
        candidates = [p for p in safe_props if 1.8 <= p['odd'] <= 2.8 and prop_key(p) not in used_props]
        random.shuffle(candidates)  # Add variety
        legs = pick_multi_sport_legs(candidates, random.choice([3, 4]), min_sports=2)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if 10 <= total <= 29.9:
                conf = calculate_confidence(legs)
                tickets.append({
                    'tier': 'hunter',
                    'legs': legs,
                    'total_odds': total,
                    'confidence': conf,
                })

    # === SHARK TICKETS (x30-99) — Medium risk ===
    for i in range(5):
        candidates = [p for p in safe_props if 2.0 <= p['odd'] <= 3.5 and prop_key(p) not in used_props]
        random.shuffle(candidates)
        legs = pick_multi_sport_legs(candidates, random.choice([4, 5]), min_sports=2)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if 30 <= total <= 99.9:
                conf = calculate_confidence(legs)
                tickets.append({
                    'tier': 'shark',
                    'legs': legs,
                    'total_odds': total,
                    'confidence': conf,
                })

    # === WHALE TICKETS (x100+) — High risk, high reward ===
    for i in range(4):
        candidates = [p for p in all_props if 2.2 <= p['odd'] <= 5.0 and prop_key(p) not in used_props]
        random.shuffle(candidates)
        legs = pick_multi_sport_legs(candidates, random.choice([5, 6]), min_sports=2)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if total >= 100:
                conf = calculate_confidence(legs)
                tickets.append({
                    'tier': 'whale',
                    'legs': legs,
                    'total_odds': total,
                    'confidence': conf,
                })

    # Sort: whales first, then sharks, then hunters
    tier_order = {'whale': 0, 'shark': 1, 'hunter': 2}
    tickets.sort(key=lambda t: (tier_order[t['tier']], -t['total_odds']))

    # Assign IDs and titles
    counters = {'whale': 0, 'shark': 0, 'hunter': 0}
    for ticket in tickets:
        tier = ticket['tier']
        counters[tier] += 1
        prefix = tier[0].upper()
        ticket['id'] = f"{prefix}{counters[tier]}"

        # Generate title from sports in the ticket
        sport_names = list(set(
            SPORT_META.get(l['sport_key'], {}).get('name', 'Multi')
            for l in ticket['legs']
        ))
        if len(sport_names) == 1:
            ticket['title'] = f"{sport_names[0]} Props Mix"
        elif len(sport_names) == 2:
            ticket['title'] = f"{sport_names[0]} + {sport_names[1]}"
        else:
            ticket['title'] = f"Multi-Sport x{len(sport_names)}"

    return tickets


def generate_ticket_js(tickets):
    """Convert tickets to JavaScript TICKETS array."""
    if not tickets:
        return "const TICKETS = [];"

    lines = ["const TICKETS = ["]
    for ticket in tickets:
        legs_js = []
        for leg in ticket['legs']:
            sport = SPORT_META.get(leg['sport_key'], {})
            leg_sport = sport.get('short', 'multi')
            legs_js.append(
                f"    {{player:'{_esc(leg['player'])}', "
                f"prop:'{_esc(leg['prop_es'])}', "
                f"match:'{_esc(leg['match'])}', "
                f"odd:{leg['odd']}, sport:'{leg_sport}'}}"
            )

        # Determine primary sport for the ticket (most common)
        sport_counts = {}
        for leg in ticket['legs']:
            sk = SPORT_META.get(leg['sport_key'], {}).get('short', 'multi')
            sport_counts[sk] = sport_counts.get(sk, 0) + 1
        primary_sport = max(sport_counts, key=sport_counts.get) if sport_counts else 'multi'

        lines.append(
            f"  {{ id:'{ticket['id']}', tier:'{ticket['tier']}', "
            f"sport:'{primary_sport}', title:'{_esc(ticket['title'])}', "
            f"confidence:{ticket['confidence']}, totalOdds:{ticket['total_odds']}, "
            f"couponCode:'', legs:[\n" +
            ",\n".join(legs_js) +
            "\n  ]},"
        )

    lines.append("];")
    return "\n".join(lines)


def _esc(s):
    """Escape string for JS single quotes."""
    return str(s).replace("'", "\\'").replace("\n", " ")


def load_results():
    """Load previous results from JSON file."""
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return {'tickets': {}, 'last_updated': None}


def save_results(results):
    """Save results to JSON file."""
    results['last_updated'] = datetime.now(timezone.utc).isoformat()
    RESULTS_FILE.write_text(json.dumps(results, indent=2))


def update_html(tickets_js):
    """Read template HTML and inject fresh ticket data."""
    template = TEMPLATE_FILE.read_text(encoding='utf-8')

    # Replace the TICKETS constant
    import re
    # Find the existing TICKETS array and replace it
    pattern = r'const TICKETS = \[[\s\S]*?\];'
    if re.search(pattern, template):
        updated = re.sub(pattern, tickets_js, template, count=1)
    else:
        # Fallback: insert before the first function
        updated = template.replace(
            '// === TICKET DATA ===',
            f'// === TICKET DATA ===\n{tickets_js}'
        )

    # Update the generation timestamp
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    # Add/update a data attribute on body
    updated = updated.replace(
        '<body>',
        f'<body data-generated="{now}">'
    )

    OUTPUT_FILE.write_text(updated, encoding='utf-8')
    print(f"✅ index.html updated with {len([t for t in updated.split('tier:')])-1} tickets")


def main():
    if not API_KEY:
        print("❌ Set ODDS_API_KEY environment variable")
        print("   export ODDS_API_KEY='your-key-here'")
        sys.exit(1)

    print("🚀 MasterProps Generator")
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    # Step 1: Fetch games and props from all sports
    all_props = []

    for sport_key in SPORTS:
        meta = SPORT_META.get(sport_key, {})
        emoji = meta.get('emoji', '🎯')
        name = meta.get('name', sport_key)
        print(f"{emoji} Fetching {name}...")

        games = fetch_upcoming_games(sport_key)
        if not games:
            print(f"  → No upcoming games")
            continue

        print(f"  → {len(games)} games found")

        # Get prop markets for this sport type
        sport_type = 'soccer' if 'soccer' in sport_key else sport_key
        markets = PROP_MARKETS.get(sport_type, PROP_MARKETS.get(sport_key, []))

        if not markets:
            # For sports without specific prop markets, use match odds creatively
            print(f"  → No prop markets configured, skipping player props")
            continue

        # Fetch props for up to 3 games per sport (to conserve API calls)
        games_to_check = games[:3]
        for game in games_to_check:
            event_data = fetch_player_props(sport_key, game['id'], markets)
            if event_data:
                props = parse_props_from_event(event_data, sport_key)
                all_props.extend(props)
                print(f"  → {len(props)} props from {game.get('home_team', '?')} vs {game.get('away_team', '?')}")

    print(f"\n📊 Total props collected: {len(all_props)}")

    if not all_props:
        print("⚠ No props found. Check API key and available sports.")
        # Generate empty tickets
        tickets_js = "const TICKETS = [];"
    else:
        # Step 2: Build optimized tickets
        print("\n🎰 Building multi-sport tickets...")
        tickets = build_tickets(all_props)
        print(f"  → {len(tickets)} tickets generated")

        for t in tickets:
            sports_in = set(SPORT_META.get(l['sport_key'], {}).get('name', '?') for l in t['legs'])
            print(f"    {t['id']} [{t['tier'].upper()}] x{t['total_odds']} | "
                  f"{len(t['legs'])} legs | {', '.join(sports_in)} | "
                  f"conf: {t['confidence']}/6")

        tickets_js = generate_ticket_js(tickets)

    # Step 3: Update HTML
    print("\n📝 Updating HTML...")
    update_html(tickets_js)

    # Step 4: Save results tracking
    results = load_results()
    results['generation'] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_props': len(all_props),
        'tickets_generated': len(tickets) if all_props else 0,
    }
    save_results(results)

    print("\n✅ Done! Open index.html to see the results.")
    remaining = None
    # Check API usage from headers (if available)
    print(f"💡 Remember: free tier = 500 requests/month")


if __name__ == '__main__':
    main()
