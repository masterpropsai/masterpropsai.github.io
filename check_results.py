#!/usr/bin/env python3
"""
MasterProps.ai — Results Checker
Checks completed games and marks ticket legs as ✅ won or ❌ lost.
Updates the HTML with result indicators and tracks historical stats.

Usage:
  ODDS_API_KEY=xxx python check_results.py           # check & update
  ODDS_API_KEY=xxx python check_results.py --stats    # show hit-rate stats
"""

import requests
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from difflib import SequenceMatcher

# ── Config ──
API_KEY = os.environ.get('ODDS_API_KEY', '')
BASE_URL = 'https://api.the-odds-api.com/v4'

SCRIPT_DIR = Path(__file__).parent
RESULTS_FILE = SCRIPT_DIR / 'results.json'
INDEX_FILE = SCRIPT_DIR / 'index.html'
TEMPLATE_FILE = SCRIPT_DIR / 'template.html'
STATS_FILE = SCRIPT_DIR / 'stats.json'

# Odds API sport keys to check for scores
SPORTS_TO_CHECK = [
    # Football / Soccer
    'soccer_fifa_world_cup',
    'soccer_epl', 'soccer_spain_la_liga', 'soccer_italy_serie_a',
    'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_argentina_primera_division', 'soccer_brazil_campeonato',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league',
    'soccer_conmebol_copa_libertadores',
    # Other sports
    'basketball_nba',
    'baseball_mlb',
    'icehockey_nhl',
]

# ── Team name aliases: Spanish → English (for matching) ──
TEAM_ALIASES = {
    'méxico': 'mexico', 'sudáfrica': 'south africa', 'brasil': 'brazil',
    'marruecos': 'morocco', 'ee.uu.': 'usa', 'estados unidos': 'usa',
    'haití': 'haiti', 'escocia': 'scotland', 'catar': 'qatar',
    'suiza': 'switzerland', 'rep. checa': 'czech republic',
    'república checa': 'czech republic',
    'corea del sur': 'south korea', 'canadá': 'canada',
    'bosnia': 'bosnia and herzegovina', 'alemania': 'germany',
    'españa': 'spain', 'francia': 'france', 'italia': 'italy',
    'inglaterra': 'england', 'países bajos': 'netherlands',
    'holanda': 'netherlands', 'bélgica': 'belgium',
    'argentina': 'argentina', 'uruguay': 'uruguay', 'colombia': 'colombia',
    'chile': 'chile', 'perú': 'peru', 'paraguay': 'paraguay',
    'ecuador': 'ecuador', 'venezuela': 'venezuela', 'bolivia': 'bolivia',
    'japón': 'japan', 'australia': 'australia',
    'nueva zelanda': 'new zealand',
    'arabia saudita': 'saudi arabia', 'irán': 'iran', 'irak': 'iraq',
    'nigeria': 'nigeria', 'senegal': 'senegal', 'camerún': 'cameroon',
    'gales': 'wales', 'croacia': 'croatia', 'serbia': 'serbia',
    'dinamarca': 'denmark', 'suecia': 'sweden', 'noruega': 'norway',
    'polonia': 'poland', 'turquía': 'turkey', 'grecia': 'greece',
    'rumania': 'romania', 'hungría': 'hungary', 'austria': 'austria',
    'ucrania': 'ukraine', 'costa rica': 'costa rica',
    'honduras': 'honduras', 'panamá': 'panama', 'jamaica': 'jamaica',
    'ghana': 'ghana', 'costa de marfil': 'ivory coast',
    'egipto': 'egypt', 'túnez': 'tunisia', 'argelia': 'algeria',
    'gana': 'ghana',  # "Gana" can also be the verb — context matters
    'corea': 'south korea', 'rusia': 'russia',
}


# ═══════════════════════════════════════════════════
#  1. FETCH SCORES FROM ODDS API
# ═══════════════════════════════════════════════════

def fetch_scores(sport_key, days_from=3):
    """Fetch completed game scores from the Odds API."""
    try:
        resp = requests.get(
            f'{BASE_URL}/sports/{sport_key}/scores',
            params={
                'apiKey': API_KEY,
                'daysFrom': days_from,
                'dateFormat': 'iso',
            },
            timeout=15,
        )
        if resp.status_code == 200:
            remaining = resp.headers.get('x-requests-remaining', '?')
            print(f"    ✅ {sport_key}: {len(resp.json())} games (API calls left: {remaining})")
            return resp.json()
        elif resp.status_code == 422:
            # Sport not in-season or not supported
            return []
        else:
            print(f"    ⚠️  {sport_key}: HTTP {resp.status_code}")
            return []
    except Exception as e:
        print(f"    ❌ {sport_key}: {e}")
        return []


def fetch_all_completed_games():
    """Fetch completed games across all tracked sports."""
    completed = {}
    print("📡 Fetching scores from Odds API...")

    for sport in SPORTS_TO_CHECK:
        games = fetch_scores(sport)
        for game in games:
            if game.get('completed'):
                completed[game['id']] = game

    print(f"\n📊 {len(completed)} completed games found\n")
    return completed


# ═══════════════════════════════════════════════════
#  2. PARSE TICKETS FROM HTML
# ═══════════════════════════════════════════════════

def parse_tickets_from_html(filepath):
    """Parse the TICKETS JS array from an HTML file into Python dicts."""
    if not filepath.exists():
        return []

    content = filepath.read_text(encoding='utf-8')
    m = re.search(r'const TICKETS = \[([\s\S]*?)\];', content)
    if not m:
        return []

    tickets_str = m.group(1)
    tickets = []

    # Match each ticket block: { id:'...', ... legs:[...] }
    ticket_pattern = r"\{\s*id:'([^']*)'.*?tier:'([^']*)'.*?sport:'([^']*)'.*?legs:\[(.*?)\]\s*\}"
    for tm in re.finditer(ticket_pattern, tickets_str, re.DOTALL):
        ticket_id = tm.group(1)
        tier = tm.group(2)
        sport = tm.group(3)
        legs_str = tm.group(4)

        legs = []
        # Match each leg object
        leg_pattern = r"\{([^}]+)\}"
        for lm in re.finditer(leg_pattern, legs_str):
            leg_inner = lm.group(1)
            leg = {}

            # Extract string fields
            for key in ['player', 'prop', 'match', 'team', 'date', 'link', 'sport', 'logo']:
                km = re.search(rf"{key}:'((?:[^'\\]|\\.)*)'", leg_inner)
                if km:
                    leg[key] = km.group(1)

            # Extract numeric odd
            om = re.search(r"odd:([\d.]+)", leg_inner)
            if om:
                leg['odd'] = float(om.group(1))

            # Extract edge (can be null, negative, or positive)
            em = re.search(r"edge:([-\d.]+|null)", leg_inner)
            if em:
                leg['edge'] = None if em.group(1) == 'null' else float(em.group(1))

            if leg.get('prop'):
                legs.append(leg)

        tickets.append({
            'id': ticket_id,
            'tier': tier,
            'sport': sport,
            'legs': legs,
        })

    return tickets


# ═══════════════════════════════════════════════════
#  3. TEAM NAME MATCHING
# ═══════════════════════════════════════════════════

def normalize_team(name):
    """Normalize a team name for comparison."""
    n = name.strip().lower()
    # Remove parenthetical prefixes: "(MAR vs)" → ""
    n = re.sub(r'\([^)]*\)', '', n).strip()
    # Check direct alias
    if n in TEAM_ALIASES:
        return TEAM_ALIASES[n]
    return n


def extract_teams_from_link(link):
    """Extract team names from the DBbet link URL.
    Link format: .../290917081-Mexico-South-Africa
    Returns lowercased string with hyphens replaced by spaces.
    """
    m = re.search(r'/\d+-([A-Za-z-]+)$', link)
    if m:
        return m.group(1).replace('-', ' ').lower()
    return ''


def teams_match(api_team, ticket_team, link=''):
    """Check if an API team name matches a ticket team name."""
    api_n = api_team.strip().lower()
    ticket_n = normalize_team(ticket_team)

    # Direct match
    if api_n == ticket_n:
        return True

    # Containment
    if len(api_n) > 3 and len(ticket_n) > 3:
        if api_n in ticket_n or ticket_n in api_n:
            return True

    # Alias lookup
    for alias, canonical in TEAM_ALIASES.items():
        if ticket_n == alias and (api_n == canonical or canonical in api_n):
            return True

    # Check link URL
    if link:
        link_text = extract_teams_from_link(link)
        if link_text:
            # Both team names should be findable in the link
            if api_n in link_text:
                return True
            # Check last-name portion
            api_parts = api_n.split()
            if any(part in link_text for part in api_parts if len(part) > 3):
                return True

    # Fuzzy match (high threshold)
    ratio = SequenceMatcher(None, api_n, ticket_n).ratio()
    if ratio > 0.75:
        return True

    return False


def extract_match_teams(match_str):
    """Extract home and away team names from a match string.
    Format: "Mundial · México vs Sudáfrica" → ("México", "Sudáfrica")
    """
    # Strip tournament prefix
    teams_part = match_str.split('·')[-1].strip() if '·' in match_str else match_str
    parts = re.split(r'\s+vs\s+', teams_part, flags=re.IGNORECASE)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, None


def find_matching_game(leg, completed_games):
    """Find the completed game that matches a ticket leg."""
    match_str = leg.get('match', '')
    link = leg.get('link', '')

    home_ticket, away_ticket = extract_match_teams(match_str)
    if not home_ticket or not away_ticket:
        return None

    for game_id, game in completed_games.items():
        home_api = game.get('home_team', '')
        away_api = game.get('away_team', '')

        # Check if both teams match (order may differ between APIs)
        h_matches_h = teams_match(home_api, home_ticket, link)
        h_matches_a = teams_match(home_api, away_ticket, link)
        a_matches_h = teams_match(away_api, home_ticket, link)
        a_matches_a = teams_match(away_api, away_ticket, link)

        if (h_matches_h and a_matches_a) or (h_matches_a and a_matches_h):
            return game

    return None


# ═══════════════════════════════════════════════════
#  4. PROP RESOLUTION (determine won/lost from scores)
# ═══════════════════════════════════════════════════

def get_scores_from_game(game):
    """Extract (home_score, away_score) from a game dict."""
    scores = game.get('scores', [])
    home_team = game.get('home_team', '')
    away_team = game.get('away_team', '')

    home_score = away_score = 0
    for s in scores:
        if s.get('name') == home_team:
            try:
                home_score = int(s.get('score', 0))
            except (ValueError, TypeError):
                home_score = 0
        elif s.get('name') == away_team:
            try:
                away_score = int(s.get('score', 0))
            except (ValueError, TypeError):
                away_score = 0

    return home_score, away_score


def identify_prop_team_side(leg, game):
    """Figure out if the prop's target team is home or away in the API game.
    Returns 'home', 'away', or None.
    """
    prop = leg.get('prop', '')
    link = leg.get('link', '')
    home_api = game.get('home_team', '')
    away_api = game.get('away_team', '')

    # Try to extract the team name from the prop text
    prop_team = None

    # Pattern: "goles de TEAM"
    m = re.search(r'goles de (.+?)$', prop, re.IGNORECASE)
    if m:
        prop_team = m.group(1).strip()

    # Pattern: "HÁ TEAM +/-X"
    if not prop_team:
        m = re.search(r'HÁ\s+(.+?)\s+[+-][\d.]+$', prop, re.IGNORECASE)
        if m:
            prop_team = m.group(1).strip()

    # Pattern: "Gana TEAM"
    if not prop_team:
        m = re.search(r'Gana\s+(.+?)$', prop, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            # Make sure it's not "Gana y ..." (combined market)
            if ' y ' not in candidate:
                prop_team = candidate

    # Pattern: "TEAM Gana" or "TEAM No pierde"
    if not prop_team:
        m = re.match(r'^(.+?)\s+(?:Gana|No pierde)', prop, re.IGNORECASE)
        if m:
            prop_team = m.group(1).strip()

    if prop_team:
        if teams_match(home_api, prop_team, link):
            return 'home'
        if teams_match(away_api, prop_team, link):
            return 'away'

    # Fallback: use the `team` field from the leg
    team_code = leg.get('team', '')
    if team_code:
        if teams_match(home_api, team_code, link):
            return 'home'
        if teams_match(away_api, team_code, link):
            return 'away'

    return None


def resolve_prop(leg, game):
    """Resolve a prop bet against actual game results.
    Returns 'won', 'lost', 'push', or None (can't resolve).
    """
    prop = leg.get('prop', '')
    home_score, away_score = get_scores_from_game(game)
    total = home_score + away_score

    # ── TOTAL GOALS (match-level, no team specified) ──
    m = re.match(r'Más de ([\d.]+) goles$', prop)
    if m:
        return 'won' if total > float(m.group(1)) else 'lost'

    m = re.match(r'Menos de ([\d.]+) goles$', prop)
    if m:
        return 'won' if total < float(m.group(1)) else 'lost'

    # ── INDIVIDUAL TEAM TOTALS ──
    m = re.match(r'Más de ([\d.]+) goles de .+$', prop)
    if m:
        line = float(m.group(1))
        side = identify_prop_team_side(leg, game)
        if side == 'home':
            return 'won' if home_score > line else 'lost'
        elif side == 'away':
            return 'won' if away_score > line else 'lost'
        return None

    m = re.match(r'Menos de ([\d.]+) goles de .+$', prop)
    if m:
        line = float(m.group(1))
        side = identify_prop_team_side(leg, game)
        if side == 'home':
            return 'won' if home_score < line else 'lost'
        elif side == 'away':
            return 'won' if away_score < line else 'lost'
        return None

    # ── MATCH WINNER (1X2) ──
    # "Gana TEAM" — but NOT combined markets like "Gana y Más de..."
    if re.search(r'(?:^Gana\s|Gana$)', prop) and ' y ' not in prop:
        side = identify_prop_team_side(leg, game)
        if side == 'home':
            return 'won' if home_score > away_score else 'lost'
        elif side == 'away':
            return 'won' if away_score > home_score else 'lost'
        return None

    # "TEAM Gana" (without combined)
    if re.match(r'^.+\s+Gana$', prop) and ' y ' not in prop:
        side = identify_prop_team_side(leg, game)
        if side == 'home':
            return 'won' if home_score > away_score else 'lost'
        elif side == 'away':
            return 'won' if away_score > home_score else 'lost'
        return None

    # Empate
    if prop.strip().lower() == 'empate':
        return 'won' if home_score == away_score else 'lost'

    # ── BTTS (Both Teams To Score) ──
    if 'Ambos anotan' in prop:
        both_scored = home_score > 0 and away_score > 0
        if 'Sí' in prop or 'Si' in prop:
            return 'won' if both_scored else 'lost'
        elif 'No' in prop:
            return 'won' if not both_scored else 'lost'

    # ── ASIAN HANDICAP ──
    m = re.search(r'HÁ\s+.+?\s+([+-]?[\d.]+)$', prop)
    if m:
        handicap = float(m.group(1))
        side = identify_prop_team_side(leg, game)
        if side == 'home':
            adjusted = home_score + handicap - away_score
        elif side == 'away':
            adjusted = away_score + handicap - home_score
        else:
            return None

        if adjusted > 0:
            return 'won'
        elif adjusted < 0:
            return 'lost'
        else:
            return 'push'

    # ── DOUBLE CHANCE / DNB (No pierde) — solo, without combined ──
    if 'No pierde' in prop and ' y ' not in prop and 'goles' not in prop.lower():
        side = identify_prop_team_side(leg, game)
        if side == 'home':
            return 'won' if home_score >= away_score else 'lost'
        elif side == 'away':
            return 'won' if away_score >= home_score else 'lost'
        return None

    # ── COMBINED MARKETS (win + totals, DNB + totals) ──
    # "TEAM Gana y Más de X goles - Sí/No"
    m = re.search(r'Gana y (?:Más|Menos) de ([\d.]+) goles\s*-\s*(Sí|No|Si)', prop, re.IGNORECASE)
    if m:
        line = float(m.group(1))
        answer = m.group(2).lower()
        side = identify_prop_team_side(leg, game)

        team_wins = False
        if side == 'home':
            team_wins = home_score > away_score
        elif side == 'away':
            team_wins = away_score > home_score

        over_under = 'Más' in prop
        total_check = total > line if over_under else total < line

        combined_true = team_wins and total_check
        if answer in ('sí', 'si'):
            return 'won' if combined_true else 'lost'
        else:
            return 'won' if not combined_true else 'lost'

    # "TEAM No pierde y Más/Menos de X goles - Sí/No"
    m = re.search(r'No pierde y (?:Más|Menos) de ([\d.]+) goles\s*-\s*(Sí|No|Si)', prop, re.IGNORECASE)
    if m:
        line = float(m.group(1))
        answer = m.group(2).lower()
        side = identify_prop_team_side(leg, game)

        dnb = False
        if side == 'home':
            dnb = home_score >= away_score
        elif side == 'away':
            dnb = away_score >= home_score

        over_under = 'Más' in prop
        total_check = total > line if over_under else total < line

        combined_true = dnb and total_check
        if answer in ('sí', 'si'):
            return 'won' if combined_true else 'lost'
        else:
            return 'won' if not combined_true else 'lost'

    # ── FIRST TO SCORE X GOALS ──
    # "Primero en (X) goles - TEAM/Ninguno"
    # Can't resolve with final scores alone (need minute-by-minute data)
    if 'Primero en' in prop:
        return None

    # ── HALF COMPARISON ──
    # "1st Half < 2nd Half" etc. — need half-time scores
    if 'Half' in prop or 'Mitad' in prop:
        return None

    # ── NBA / MLB / NHL specific ──
    # "Más de X puntos" / "Menos de X puntos"
    m = re.match(r'Más de ([\d.]+) puntos$', prop)
    if m:
        return 'won' if total > float(m.group(1)) else 'lost'

    m = re.match(r'Menos de ([\d.]+) puntos$', prop)
    if m:
        return 'won' if total < float(m.group(1)) else 'lost'

    # "Más/Menos de X carreras" (MLB)
    m = re.match(r'Más de ([\d.]+) carreras$', prop)
    if m:
        return 'won' if total > float(m.group(1)) else 'lost'

    m = re.match(r'Menos de ([\d.]+) carreras$', prop)
    if m:
        return 'won' if total < float(m.group(1)) else 'lost'

    # ── Unresolvable ──
    return None


# ═══════════════════════════════════════════════════
#  5. RESULTS PERSISTENCE
# ═══════════════════════════════════════════════════

def load_results():
    """Load previously saved results."""
    if RESULTS_FILE.exists():
        try:
            data = json.loads(RESULTS_FILE.read_text(encoding='utf-8'))
            # Ensure structure
            data.setdefault('legs', {})
            data.setdefault('tickets', {})
            data.setdefault('history', [])
            return data
        except json.JSONDecodeError:
            pass
    return {'legs': {}, 'tickets': {}, 'history': [], 'last_updated': None}


def save_results(data):
    """Save results to JSON file."""
    data['last_updated'] = datetime.now(timezone.utc).isoformat()
    RESULTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


# ═══════════════════════════════════════════════════
#  6. STATS & ANALYTICS
# ═══════════════════════════════════════════════════

def compute_stats(results):
    """Compute hit-rate statistics from resolved legs."""
    legs = results.get('legs', {})
    if not legs:
        return None

    stats = {
        'total_resolved': 0,
        'total_won': 0,
        'total_lost': 0,
        'total_push': 0,
        'hit_rate': 0.0,
        'by_prop_type': {},
        'by_odds_range': {},
        'by_sport': {},
    }

    for rk, info in legs.items():
        result = info.get('result')
        if result not in ('won', 'lost', 'push'):
            continue

        stats['total_resolved'] += 1
        if result == 'won':
            stats['total_won'] += 1
        elif result == 'lost':
            stats['total_lost'] += 1
        else:
            stats['total_push'] += 1

        # By prop type
        ptype = info.get('prop_type', 'unknown')
        pt = stats['by_prop_type'].setdefault(ptype, {'won': 0, 'lost': 0, 'push': 0})
        pt[result] = pt.get(result, 0) + 1

        # By odds range
        odd = info.get('odd', 0)
        if odd < 1.5:
            orange = 'ultra (< 1.50)'
        elif odd < 1.8:
            orange = 'low (1.50-1.80)'
        elif odd < 2.3:
            orange = 'mid (1.80-2.30)'
        elif odd < 3.0:
            orange = 'high (2.30-3.00)'
        else:
            orange = 'very_high (3.00+)'
        orng = stats['by_odds_range'].setdefault(orange, {'won': 0, 'lost': 0, 'push': 0})
        orng[result] = orng.get(result, 0) + 1

        # By sport
        sport = info.get('sport', 'unknown')
        sp = stats['by_sport'].setdefault(sport, {'won': 0, 'lost': 0, 'push': 0})
        sp[result] = sp.get(result, 0) + 1

    if stats['total_resolved'] > 0:
        decided = stats['total_won'] + stats['total_lost']
        stats['hit_rate'] = round(stats['total_won'] / decided * 100, 1) if decided > 0 else 0.0

    return stats


def classify_prop_type(prop):
    """Classify a prop into a category for stats tracking."""
    prop_lower = prop.lower()

    if 'ambos anotan' in prop_lower:
        return 'btts'
    if 'há ' in prop_lower:
        return 'handicap'
    if re.search(r'(más|menos) de .+ goles de', prop_lower):
        return 'team_total'
    if re.search(r'(más|menos) de .+ goles$', prop_lower):
        return 'total'
    if re.search(r'(más|menos) de .+ puntos', prop_lower):
        return 'total'
    if re.search(r'(más|menos) de .+ carreras', prop_lower):
        return 'total'
    if 'gana' in prop_lower and ' y ' not in prop_lower:
        return 'winner'
    if 'empate' in prop_lower:
        return 'draw'
    if 'no pierde' in prop_lower and ' y ' not in prop_lower:
        return 'dnb'
    if ' y ' in prop_lower:
        return 'combined'
    if 'primero en' in prop_lower:
        return 'first_to'
    if 'half' in prop_lower or 'mitad' in prop_lower:
        return 'halftime'

    return 'other'


def print_stats(stats):
    """Print formatted statistics to console."""
    if not stats:
        print("📊 No results tracked yet")
        return

    print("\n" + "═" * 55)
    print("  📊  MASTERPROPS HIT RATE STATS")
    print("═" * 55)
    decided = stats['total_won'] + stats['total_lost']
    print(f"  Resolved: {stats['total_resolved']}  |  Won: {stats['total_won']}  |  Lost: {stats['total_lost']}  |  Push: {stats['total_push']}")
    print(f"  📈 Overall hit rate: {stats['hit_rate']}%  ({stats['total_won']}/{decided})")

    if stats['by_prop_type']:
        print(f"\n  {'Prop Type':<18} {'Won':>5} {'Lost':>5} {'Rate':>7}")
        print(f"  {'─' * 37}")
        for ptype, data in sorted(stats['by_prop_type'].items()):
            w, l = data['won'], data['lost']
            rate = round(w / (w + l) * 100, 1) if (w + l) > 0 else 0
            print(f"  {ptype:<18} {w:>5} {l:>5} {rate:>6.1f}%")

    if stats['by_odds_range']:
        print(f"\n  {'Odds Range':<22} {'Won':>5} {'Lost':>5} {'Rate':>7}")
        print(f"  {'─' * 41}")
        for orange, data in sorted(stats['by_odds_range'].items()):
            w, l = data['won'], data['lost']
            rate = round(w / (w + l) * 100, 1) if (w + l) > 0 else 0
            print(f"  {orange:<22} {w:>5} {l:>5} {rate:>6.1f}%")

    if stats['by_sport']:
        print(f"\n  {'Sport':<18} {'Won':>5} {'Lost':>5} {'Rate':>7}")
        print(f"  {'─' * 37}")
        for sport, data in sorted(stats['by_sport'].items()):
            w, l = data['won'], data['lost']
            rate = round(w / (w + l) * 100, 1) if (w + l) > 0 else 0
            print(f"  {sport:<18} {w:>5} {l:>5} {rate:>6.1f}%")

    print("═" * 55)


# ═══════════════════════════════════════════════════
#  7. HTML INJECTION
# ═══════════════════════════════════════════════════

def inject_results_into_html(results, filepath):
    """Update LEG_RESULTS in the HTML file."""
    if not filepath.exists():
        return

    html = filepath.read_text(encoding='utf-8')
    leg_results = results.get('legs', {})

    # Build the JS object: { "TICKET_LEG": "won"|"lost"|"push" }
    js_obj = {}
    for rk, info in leg_results.items():
        r = info.get('result')
        if r in ('won', 'lost', 'push'):
            js_obj[rk] = r

    if not js_obj:
        return

    results_js_str = json.dumps(js_obj, ensure_ascii=False)

    # Replace existing LEG_RESULTS
    pattern = r'const LEG_RESULTS = \{[^}]*\};'
    replacement = f'const LEG_RESULTS = {results_js_str};'

    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html, count=1)
    else:
        # Insert before TICKETS
        html = html.replace(
            'const TICKETS = [',
            f'{replacement}\nconst TICKETS = ['
        )

    filepath.write_text(html, encoding='utf-8')
    print(f"  ✅ {filepath.name} updated with {len(js_obj)} results")


# ═══════════════════════════════════════════════════
#  8. TICKET-LEVEL STATUS
# ═══════════════════════════════════════════════════

def evaluate_tickets(results, tickets):
    """Determine ticket-level status (won/lost/pending) based on legs."""
    ticket_status = results.setdefault('tickets', {})
    legs = results.get('legs', {})

    for ticket in tickets:
        tid = ticket['id']
        num_legs = len(ticket['legs'])
        if num_legs == 0:
            continue

        won_count = 0
        lost_count = 0
        push_count = 0
        pending_count = 0

        for j in range(num_legs):
            rk = f"{tid}_{j}"
            info = legs.get(rk, {})
            r = info.get('result')
            if r == 'won':
                won_count += 1
            elif r == 'lost':
                lost_count += 1
            elif r == 'push':
                push_count += 1
            else:
                pending_count += 1

        # Ticket is lost if ANY leg is lost
        if lost_count > 0:
            status = 'lost'
        elif pending_count > 0:
            status = 'pending'
        elif won_count + push_count == num_legs:
            status = 'won'
        else:
            status = 'pending'

        ticket_status[tid] = {
            'status': status,
            'legs': num_legs,
            'won': won_count,
            'lost': lost_count,
            'push': push_count,
            'pending': pending_count,
            'tier': ticket.get('tier', ''),
        }

    return results


# ═══════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════

def main():
    if not API_KEY:
        print("❌ Set ODDS_API_KEY environment variable")
        return

    show_stats_only = '--stats' in sys.argv

    print("🔍 MasterProps Results Checker")
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

    # Load existing results
    results = load_results()
    existing_legs = results.get('legs', {})
    print(f"📂 Loaded {len(existing_legs)} previously tracked legs\n")

    # Parse tickets from HTML
    tickets = parse_tickets_from_html(INDEX_FILE)
    total_legs = sum(len(t['legs']) for t in tickets)
    print(f"🎫 {len(tickets)} tickets with {total_legs} total selections parsed\n")

    if show_stats_only:
        stats = compute_stats(results)
        print_stats(stats)
        return

    # Fetch completed games
    completed_games = fetch_all_completed_games()

    if not completed_games:
        print("ℹ️  No completed games found. Nothing to resolve.\n")
        # Still evaluate ticket status with existing data
        evaluate_tickets(results, tickets)
        save_results(results)
        return

    # Cross-reference each leg with completed games
    new_resolved = 0
    already_resolved = 0
    unresolvable = 0
    no_match = 0

    for ticket in tickets:
        tid = ticket['id']
        for j, leg in enumerate(ticket['legs']):
            rk = f"{tid}_{j}"

            # Skip if already resolved
            if rk in existing_legs and existing_legs[rk].get('result') in ('won', 'lost', 'push'):
                already_resolved += 1
                continue

            # Try to find matching completed game
            game = find_matching_game(leg, completed_games)
            if not game:
                no_match += 1
                continue

            # Resolve the prop
            result = resolve_prop(leg, game)
            prop_type = classify_prop_type(leg.get('prop', ''))

            if result is None:
                unresolvable += 1
                print(f"  ❓ [{tid}] Can't resolve: {leg.get('prop', '?')}")
                continue

            # Store result
            home_score, away_score = get_scores_from_game(game)
            results['legs'][rk] = {
                'result': result,
                'prop': leg.get('prop', ''),
                'prop_type': prop_type,
                'match': leg.get('match', ''),
                'odd': leg.get('odd', 0),
                'sport': leg.get('sport', ''),
                'score': f"{home_score}-{away_score}",
                'game_id': game.get('id', ''),
                'resolved_at': datetime.now(timezone.utc).isoformat(),
            }
            new_resolved += 1

            icon = '✅' if result == 'won' else ('❌' if result == 'lost' else '↩️')
            print(f"  {icon} [{tid}] {leg.get('prop', '?')} → {result.upper()} (score: {home_score}-{away_score})")

    print(f"\n📊 Resolution summary:")
    print(f"   New resolved:     {new_resolved}")
    print(f"   Already resolved: {already_resolved}")
    print(f"   No match found:   {no_match} (game not completed or not in API)")
    print(f"   Unresolvable:     {unresolvable} (prop type needs detailed data)")

    # Evaluate ticket-level status
    evaluate_tickets(results, tickets)

    # Print ticket summary
    ticket_status = results.get('tickets', {})
    won_tickets = sum(1 for v in ticket_status.values() if v['status'] == 'won')
    lost_tickets = sum(1 for v in ticket_status.values() if v['status'] == 'lost')
    pending_tickets = sum(1 for v in ticket_status.values() if v['status'] == 'pending')

    print(f"\n🎫 Ticket summary: {won_tickets} won, {lost_tickets} lost, {pending_tickets} pending")

    for tid, info in sorted(ticket_status.items()):
        icon = {'won': '🏆', 'lost': '💀', 'pending': '⏳'}.get(info['status'], '❓')
        print(f"   {icon} {tid}: {info['won']}W/{info['lost']}L/{info['push']}P/{info['pending']}? ({info['tier']})")

    # Save results
    save_results(results)
    print(f"\n💾 Results saved to {RESULTS_FILE.name}")

    # Inject into HTML files
    inject_results_into_html(results, INDEX_FILE)
    if TEMPLATE_FILE.exists():
        inject_results_into_html(results, TEMPLATE_FILE)

    # ── HISTORIAL: archivar billetes terminados e inyectar en HTML ──
    try:
        import history_lib
        extra = {}
        for rk, info in results.get('legs', {}).items():
            r = info.get('result')
            if r in ('won', 'lost', 'push'):
                extra[rk] = 'void' if r == 'push' else r
        for fp in (INDEX_FILE, TEMPLATE_FILE):
            if fp.exists():
                html = fp.read_text(encoding='utf-8')
                history_lib.archive_finished(html, extra)
                fp.write_text(history_lib.inject_history(html), encoding='utf-8')
        print("  \ud83d\udcdc HISTORIAL actualizado")
    except Exception as e:
        print(f"  \u26a0\ufe0f historial: {e}")

    # Compute and display stats
    stats = compute_stats(results)
    if stats and stats['total_resolved'] > 0:
        print_stats(stats)
        # Save stats to file
        STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding='utf-8')

    print("\n✅ Results check complete")


if __name__ == '__main__':
    main()
