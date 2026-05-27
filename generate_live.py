#!/usr/bin/env python3
"""
MasterProps.ai — LIVE Ticket Generator v4
Fetches real odds from DBbet Marketing API, builds high-value prop tickets.
Replaces the hardcoded PROP_POOL with real-time data.
"""

import random
import math
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
TEMPLATE_FILE = BASE_DIR / 'template.html'
OUTPUT_FILE = BASE_DIR / 'index.html'
COUPONS_FILE = BASE_DIR / 'coupons.json'

# ── DBbet API Config ──
TOKEN_URL = "https://cpservm.com/gateway/token"
API_BASE = "https://cpservm.com/gateway/marketing/datafeed/prematch/api/v2"
CLIENT_ID = "partners-3151f4df3df18d1d17e3eae7a6c43792"
CLIENT_SECRET = "LDnyHnPGpVdar!gId431qn&YQRAZg!D5A1R010T5rk0F3ciWT1CHreULFN2Ly3Ck"
REF = "164"
PARTNER_LINK = "refpa1800.com"
LOGO_BASE = "https://nimblecd.com/sfiles/logo_teams/"

# ── Sport config ──
SPORT_MAP = {1: 'futbol', 2: 'hockey', 3: 'nba', 4: 'tenis', 5: 'mlb', 189: 'ufc'}
SPORT_NAMES = {
    'futbol': 'Fútbol', 'hockey': 'NHL', 'nba': 'NBA',
    'tenis': 'Tenis', 'mlb': 'MLB', 'ufc': 'UFC'
}

# ── Team abbreviations ──
TEAM_ABBREVS = {
    'Real Madrid': 'RMA', 'Barcelona': 'BAR', 'Atletico Madrid': 'ATM',
    'Manchester City': 'MCI', 'Manchester United': 'MUN', 'Liverpool': 'LIV',
    'Arsenal': 'ARS', 'Chelsea': 'CHE', 'Tottenham': 'TOT', 'Everton': 'EVE',
    'Bayern': 'BAY', 'Dortmund': 'BVB', 'Juventus': 'JUV',
    'Internazionale': 'INT', 'AC Milan': 'MIL', 'Paris': 'PSG',
    'Fiorentina': 'FIO', 'Atalanta': 'ATA', 'Roma': 'ROM',
    'Napoli': 'NAP', 'Lazio': 'LAZ', 'Bologna': 'BOL',
    'Colorado Avalanche': 'COL', 'Vegas Golden Knights': 'VGK',
    'Germany': 'GER', 'Brazil': 'BRA', 'Spain': 'ESP', 'France': 'FRA',
    'Argentina': 'ARG', 'England': 'ENG', 'Italy': 'ITA', 'Portugal': 'POR',
    'Crystal Palace': 'CRY', 'Brighton': 'BHA', 'Wolverhampton': 'WOL',
    'Burnley': 'BUR', 'Sunderland': 'SUN', 'Brentford': 'BRE',
    'Aston Villa': 'AVL', 'West Ham': 'WHU', 'Newcastle': 'NEW',
}

# ── Tournament filtering ──
# Exclude friendlies — too unpredictable, low motivation
EXCLUDED_TOURNAMENT_KEYWORDS = [
    'friendl',          # Friendlies. National Teams / Friendlies U19
    'amistos',          # Spanish variants if any
    'club friendl',
]
# Boost factor for preferred tournaments (Conmebol focus)
PREFERRED_TOURNAMENT_KEYWORDS = {
    'libertadores': 4,      # Copa Libertadores → 4x weight
    'sudamericana': 4,      # Copa Sudamericana → 4x weight
    'brasileiro': 2,        # Brazilian Serie A → 2x weight
    'copa argentina': 3,    # Copa Argentina → 3x weight
}

# ── Interesting market keywords ──
INTERESTING_KEYWORDS = [
    'Handicap', 'Total', 'Both Teams', 'HT-FT', 'Win And Total',
    'Individual Total', 'Race To', 'W1', 'W2', 'To Win',
    'Next Goal', 'Clean Sheet', 'Win To Nil', 'To Score',
    'Corners', 'Cards', 'Yellow', 'Odd', 'Even',
    'Not To Lose', 'Difference', 'Any Team', 'Neither',
    'Draw', 'No Draw', 'Half', 'Penalty',
    'Win By', 'Exact Score', 'Double Chance',
]

# Markets that imply a specific team winning — used to avoid contradictions
TEAM_WINNER_MARKETS = {'W1', 'W2', '1X', 'X2', '12'}

# ── Spanish translations for prop display ──
TRANSLATIONS = {
    'Over': 'Más de', 'Under': 'Menos de', 'Handicap': 'Hándicap',
    'Both Teams To Score - Yes': 'Ambos anotan - Sí',
    'Both Teams To Score - No': 'Ambos anotan - No',
    'Individual Total': 'Total Individual',
    'Race To': 'Primero en',
    'Goals': 'goles', 'Clean Sheet': 'Valla invicta',
    'Win To Nil': 'Gana sin goles en contra',
    'Team 1': 'Local', 'Team 2': 'Visitante',
    'Win And Total': 'Gana y Total',
    'Not To Lose': 'No pierde',
    'To Score Next Goal': 'Anota próximo gol',
    'Neither Team': 'Ninguno',
    ' And Total': ' y Total',
    ' To Win ': ' Gana ',
    'Any Team To': 'Algún equipo',
    ' Or More ': ' o más ',
    ' With Difference Of': ' por diferencia de',
    'Total Odd': 'Total Impar',
    'Total Even': 'Total Par',
    ' - Yes': ' - Sí',
    ' Wins ': ' Gana ',
    ' By ': ' por ',
    'Goal': 'Gol',
    'Corners': 'Córners',
    'Cards': 'Tarjetas',
    'Yellow': 'Amarilla',
    'Red': 'Roja',
    'Half Time': '1er Tiempo',
    'Full Time': 'Final',
    'Next ': 'Próximo ',
    'Score': 'Marca',
    'First': 'Primer',
    'Last': 'Último',
    'penalty': 'penal',
    'Penalty': 'Penal',
    'Draw': 'Empate',
    'No Draw': 'Sin Empate',
}

# ── Team/Country name translations (EN → ES) ──
TEAM_NAME_ES = {
    # Selecciones
    'Spain': 'España', 'France': 'Francia', 'Germany': 'Alemania',
    'England': 'Inglaterra', 'Netherlands': 'Holanda', 'Brazil': 'Brasil',
    'Mexico': 'México', 'Switzerland': 'Suiza', 'Sweden': 'Suecia',
    'Scotland': 'Escocia', 'Japan': 'Japón', 'South Korea': 'Corea del Sur',
    'Turkey': 'Turquía', 'South Africa': 'Sudáfrica',
    'Bosnia and Herzegovina': 'Bosnia', 'Czech Republic': 'Rep. Checa',
    'Cape Verde': 'Cabo Verde', 'Curacao': 'Curazao',
    'DR Congo': 'RD Congo', 'Saudi Arabia': 'Arabia Saudita',
    'Haiti': 'Haití', 'Iraq': 'Irak', 'Tunisia': 'Túnez',
    'Belgium': 'Bélgica', 'Egypt': 'Egipto', 'Panama': 'Panamá',
    'Morocco': 'Marruecos', 'Croatia': 'Croacia',
    'United States': 'EE.UU.', 'USA': 'EE.UU.', 'Costa Rica': 'Costa Rica',
    'North Korea': 'Corea del Norte', 'Ivory Coast': 'Costa de Marfil',
    'Denmark': 'Dinamarca', 'Poland': 'Polonia', 'Norway': 'Noruega',
    'Finland': 'Finlandia', 'Greece': 'Grecia', 'Romania': 'Rumania',
    'Hungary': 'Hungría', 'Serbia': 'Serbia', 'Slovakia': 'Eslovaquia',
    'Slovenia': 'Eslovenia', 'Albania': 'Albania', 'Iceland': 'Islandia',
    'Wales': 'Gales', 'Ireland': 'Irlanda', 'Russia': 'Rusia',
    'Ukraine': 'Ucrania', 'Peru': 'Perú', 'Chile': 'Chile',
    'Colombia': 'Colombia', 'Ecuador': 'Ecuador', 'Bolivia': 'Bolivia',
    'Venezuela': 'Venezuela', 'Honduras': 'Honduras',
    'Jamaica': 'Jamaica', 'Canada': 'Canadá', 'Uzbekistan': 'Uzbekistán',
    'Azerbaijan': 'Azerbaiyán', 'Kazakhstan': 'Kazajistán',
    'Cameroon': 'Camerún', 'Nigeria': 'Nigeria', 'Algeria': 'Argelia',
    'China': 'China', 'Iran': 'Irán', 'New Zealand': 'Nueva Zelanda',
    # Clubes — acortar nombres largos
    'Brighton & Hove Albion': 'Brighton', 'VfB Stuttgart': 'Stuttgart',
    'Nottingham Forest': 'Nott. Forest', 'Bologna 1909': 'Bologna',
    'Sassuolo Calcio': 'Sassuolo', 'Internazionale Milano': 'Inter de Milán',
    'Udinese Calcio': 'Udinese', 'Bayern Munich': 'Bayern Múnich',
    'Manchester United': 'Man. United', 'Manchester City': 'Man. City',
    'Tottenham Hotspur': 'Tottenham', 'West Ham United': 'West Ham',
    'Newcastle United': 'Newcastle', 'Hellas Verona': 'Verona',
    'Levante UD': 'Levante', 'Leeds United': 'Leeds',
    'Spartak Moscow': 'Spartak Moscú', 'Crystal Palace': 'C. Palace',
    'Wolverhampton Wanderers': 'Wolverhampton',
    'Paris Saint-Germain': 'PSG',
    'Cremonese': 'Cremonese',
}


def get_token():
    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, headers={
        'Content-Type': 'application/x-www-form-urlencoded'
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())['access_token']


def fetch_events(token):
    url = (f"{API_BASE}/sportevents?"
           f"ref={REF}&SchemeOfGettingOddsOperations=GetAllOdds"
           f"&partnerLink={PARTNER_LINK}&count=1000")
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def abbrev(name):
    for full, ab in TEAM_ABBREVS.items():
        if full.lower() in name.lower():
            return ab
    words = name.split()
    return (words[0][:3]).upper() if words else 'UNK'


def translate(display):
    d = display
    # Phase 1: Multi-word phrases first (order matters!)
    multi_word = [
        ('Any Team To Win With Difference Of', 'Algún equipo gana por diferencia de'),
        ('Any Team To Win', 'Algún equipo gana'),
        ('Any Team To', 'Algún equipo'),
        ('Both Teams To Score - Yes', 'Ambos anotan - Sí'),
        ('Both Teams To Score - No', 'Ambos anotan - No'),
        ('Win And Total', 'Gana y Total'),
        ('Win To Nil', 'Gana sin goles en contra'),
        ('Not To Lose', 'No pierde'),
        ('To Score Next Goal', 'Anota próximo gol'),
        ('Neither Team', 'Ninguno'),
        ('Individual Total', 'Total Individual'),
        ('Race To', 'Primero en'),
        ('Clean Sheet', 'Valla invicta'),
        ('Half Time', '1er Tiempo'),
        ('Full Time', 'Final'),
        ('No Draw', 'Sin Empate'),
    ]
    for en, es in multi_word:
        d = d.replace(en, es)
    # Phase 2: Single-word translations
    for en, es in TRANSLATIONS.items():
        d = d.replace(en, es)
    # Phase 3: Clean up leftover English fragments
    d = d.replace(' To Gana', ' Gana')
    d = d.replace(' To No pierde', ' No pierde')
    d = d.replace(' To Valla invicta', ' Valla invicta')
    d = d.replace('Any Team ', 'Algún equipo ')
    d = d.replace(' Wins ', ' Gana ')
    d = d.replace(' By ', ' por ')
    d = d.replace('Goals', 'Goles')
    d = d.replace('Goal', 'Gol')
    d = d.replace('Corners', 'Córners')
    d = d.replace(' Or More', ' o más')
    d = d.replace(' Of ', ' de ')
    d = d.replace('To Nil', 'sin goles en contra')
    d = d.replace(' To ', ' ')
    d = d.replace('goles en contra -', 'goles en contra -')
    # Double-space cleanup
    while '  ' in d:
        d = d.replace('  ', ' ')
    return d.strip()


def translate_name(name):
    """Translate team/country names to Spanish."""
    # Try exact match first
    if name in TEAM_NAME_ES:
        return TEAM_NAME_ES[name]
    # Try partial match for club names
    for en, es in TEAM_NAME_ES.items():
        if en.lower() == name.lower():
            return es
    return name


def translate_match(t1, t2, tournament):
    """Build a Spanish-friendly match string — just tournament since player has rival context."""
    t1_es = translate_name(t1)
    t2_es = translate_name(t2)
    if tournament:
        short = tournament.split('.')[-1].strip() if '.' in tournament else tournament
        short = short.replace('World Cup', 'Mundial')
        short = short.replace('Champions League', 'Champions')
        short = short.replace('Premier League', 'Premier League')
        short = short.replace('Germany DFB Pokal', 'Copa de Alemania')
        short = short.replace('Coupe de France', 'Copa de Francia')
        short = short.replace('Russian Cup', 'Copa de Rusia')
        return f"{short}"
    return f"{t1_es} vs {t2_es}"


def build_prop_pool(data, start_ts_min=None, start_ts_max=None, day_label=None):
    """Convert API events into a PROP_POOL compatible format.
    Filters events between start_ts_min and start_ts_max (UTC timestamps).
    Tags each prop with day_label (e.g. 'sat', 'sun').
    """
    props = []
    now = datetime.now(timezone.utc)
    if start_ts_min is None:
        start_ts_min = now.timestamp()
    if start_ts_max is None:
        start_ts_max = now.timestamp() + 24 * 3600
    skipped_future = 0

    for event in data.get('items', []):
        start_ts = event.get('startDate', 0)
        if start_ts and start_ts > start_ts_max:
            skipped_future += 1
            continue
        if start_ts and start_ts < start_ts_min:
            continue  # skip events outside window

        sport_id = event.get('sportId', 0)
        # Only allow recognized sports (skip horse racing, table tennis, snooker, etc.)
        if sport_id not in SPORT_MAP:
            continue
        sport = SPORT_MAP[sport_id]
        t1 = event.get('opponent1NameLocalization', 'Team A')
        t2 = event.get('opponent2NameLocalization', 'Team B')
        match = f"{t1} vs {t2}"
        tournament = event.get('tournamentNameLocalization', '')
        link = event.get('link', '')
        # Skip excluded tournaments (friendlies, etc.)
        tlow = tournament.lower()
        if any(kw in tlow for kw in EXCLUDED_TOURNAMENT_KEYWORDS):
            continue
        # Compute boost weight for preferred tournaments
        boost_weight = 1
        for kw, w in PREFERRED_TOURNAMENT_KEYWORDS.items():
            if kw in tlow:
                boost_weight = max(boost_weight, w)
                break
        date_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime('%b %d · %H:%M') if start_ts else 'TBD'
        ab1, ab2 = abbrev(t1), abbrev(t2)

        # Get logo URLs
        img1_list = event.get('imageOpponent1', [])
        img2_list = event.get('imageOpponent2', [])
        logo1 = f"{LOGO_BASE}{img1_list[0]}" if img1_list else ''
        logo2 = f"{LOGO_BASE}{img2_list[0]}" if img2_list else ''

        for odd in event.get('oddsLocalization', []):
            if odd.get('isBlocked', False):
                continue
            odds_val = odd.get('oddsMarket', 0)
            if odds_val < 1.3:
                continue  # skip near-certain outcomes
            display = odd.get('display', '')

            # Filter interesting markets
            if not any(kw.lower() in display.lower() for kw in INTERESTING_KEYWORDS):
                continue

            # Determine which team and logo
            if '1' in display and '2' not in display:
                player, rival, team, logo = t1, t2, ab1, logo1
            elif '2' in display and '1' not in display:
                player, rival, team, logo = t2, t1, ab2, logo2
            else:
                player, rival, team, logo = t1, t2, ab1, logo1

            # Translate names — format: "(vs Rival) Equipo"
            player_es = translate_name(player)
            rival_es = translate_name(rival)
            player_display = f"({abbrev(rival_es)} vs) {player_es}"
            match_display = translate_match(t1, t2, tournament)

            # Detect if this is a team-winner market (for anti-contradiction)
            is_winner_pick = any(wm in display for wm in TEAM_WINNER_MARKETS)
            side = 'home' if player == t1 else 'away'

            prop_obj = {
                'player': player_display,
                'prop': translate(display),
                'match': match_display,
                'odd': round(odds_val, 2),
                'sport': sport,
                'team': team,
                'date': date_str,
                'link': link,
                'logo': logo,
                'is_winner': is_winner_pick,
                'side': side,
                'match_key': f"{t1} vs {t2}",
                'day': day_label or 'today',
                'tournament': tournament,
                # SaveCoupon fields for coupon code generation
                'game_id': event.get('sportEventId', 0),
                'type_id': odd.get('type', 0),
                'param': odd.get('parameter', 0),
                'player_id': odd.get('playerId', 0),
            }
            # Duplicate prop boost_weight times so build_tickets picks it more often
            for _ in range(boost_weight):
                props.append(prop_obj)

    if skipped_future:
        print(f"   ⏭️  {skipped_future} eventos descartados (fuera de ventana 24h)")
    return props


# ──────────────────────────────────────────────
# Ticket building (same logic as v3, adapted)
# ──────────────────────────────────────────────

def _esc(s):
    return str(s).replace("'", "\\'").replace("\n", " ")


def calculate_confidence(legs):
    probs = [1/leg['odd'] for leg in legs]
    avg_prob = sum(probs) / len(probs)
    n = len(legs)
    if avg_prob > 0.55: base = 5
    elif avg_prob > 0.45: base = 4
    elif avg_prob > 0.35: base = 3
    elif avg_prob > 0.25: base = 2
    else: base = 1
    if n >= 6: base = max(1, base - 2)
    elif n >= 5: base = max(1, base - 1)
    variance = sum((p - avg_prob)**2 for p in probs) / len(probs)
    if variance < 0.01: base = min(6, base + 1)
    return min(6, max(1, base))


def prop_key(p):
    return f"{p['player']}|{p['prop']}"


def build_tickets(pool):
    """Build tickets. REGLA: máximo 1 apuesta por partido en cada billete."""
    tickets = []
    used_keys = set()

    # Identify unique matches available
    unique_matches = list(set(p['match'] for p in pool))
    n_matches = len(unique_matches)
    print(f"   🏟️  {n_matches} partidos disponibles: {', '.join(unique_matches[:5])}")

    # Split pool by odds range
    # REGLA: máximo 1 selección >x5.00 por billete, todas las demás ≤x5.00
    low = [p for p in pool if 1.30 <= p['odd'] < 1.55]
    mid = [p for p in pool if 1.55 <= p['odd'] <= 2.80]
    high = [p for p in pool if 2.80 < p['odd'] <= 5.00]
    very_high = [p for p in pool if 5.00 < p['odd'] <= 15.0]

    print(f"   low(1.3-1.55): {len(low)}, mid(1.55-2.8): {len(mid)}, "
          f"high(2.8-5): {len(high)}, vhigh(5-15): {len(very_high)}")
    print(f"   ⚠️  REGLA: máx 1 selección >x5.00 por billete")

    # Anti-contradiction: track which side we've committed to per match
    # e.g. winner_side['Lens vs Nice'] = 'home' → never pick 'away wins' for that match
    winner_side = {}  # match_key → 'home' or 'away'

    def pick_legs(pools_config, min_sports=1):
        """Pick legs enforcing MAX 1 leg per match + no contradictions."""
        selected = []
        sports_used = set()
        matches_used = set()
        for pool_list, count in pools_config:
            available = [p for p in pool_list
                         if prop_key(p) not in used_keys
                         and p['match'] not in matches_used]
            random.shuffle(available)
            picked = 0
            for p in available:
                if picked >= count:
                    break
                if p['match'] in matches_used:
                    continue
                # Anti-contradiction: if this is a winner pick, check consistency
                if p.get('is_winner') and p.get('match_key'):
                    mk = p['match_key']
                    committed = winner_side.get(mk)
                    if committed and committed != p['side']:
                        continue  # skip — contradicts a previous ticket
                selected.append(p)
                sports_used.add(p['sport'])
                matches_used.add(p['match'])
                picked += 1
        total_needed = sum(c for _, c in pools_config)
        if len(selected) >= total_needed:
            for s in selected:
                used_keys.add(prop_key(s))
                # Record winner commitment for anti-contradiction
                if s.get('is_winner') and s.get('match_key'):
                    winner_side[s['match_key']] = s['side']
            return selected
        return None

    # Determine ticket sizes based on available matches
    max_legs = min(n_matches, 5)  # Can't exceed number of unique matches

    # ══════════════════════════════════════════════════════════════════
    # REGLA CLAVE: Máximo 1 selección >x5.00 por billete.
    # Todas las demás patas deben ser ≤x5.00.
    # very_high = >x5.00 (máx 1 por billete)
    # high = x2.80-5.00, mid = x1.55-2.80, low = x1.30-1.55
    #
    # TIERS (por cuota total):
    #   Megalodón: x1000+  (4 cifras — necesita 5+ patas con 1 very_high)
    #   Whale:     x100-999
    #   Shark:     x10-99
    #   Hunter:    x3-9.9
    # ══════════════════════════════════════════════════════════════════

    # Build ticket combos — all respect max-1-above-x5 rule
    # We try many combos and let the tier classification happen by odds range
    ticket_combos = []

    if n_matches >= 5:
        ticket_combos = [
            # 5 legs: 1 very_high + 4 high → x12*x4*x4*x4*x3.5 = ~2700 (megalodón!)
            ((very_high, 1), (high, 4)),
            ((very_high, 1), (high, 3), (mid, 1)),
            ((very_high, 1), (high, 2), (mid, 2)),
            # 4 legs
            ((very_high, 1), (high, 3)),
            ((very_high, 1), (high, 2), (mid, 1)),
            ((very_high, 1), (high, 1), (mid, 2)),
            ((high, 3), (mid, 1)),
            # 3 legs
            ((very_high, 1), (high, 2)),
            ((very_high, 1), (high, 1), (mid, 1)),
            ((very_high, 1), (mid, 2)),
            ((high, 2), (mid, 1)),
            ((high, 1), (mid, 2)),
            ((high, 1), (mid, 1), (low, 1)),
            ((mid, 2), (low, 1)),
            ((mid, 3),),
        ]
    elif n_matches >= 3:
        ticket_combos = [
            ((very_high, 1), (high, min(2, n_matches-1))),
            ((very_high, 1), (high, 1), (mid, min(1, n_matches-2))),
            ((very_high, 1), (mid, min(2, n_matches-1))),
            ((high, min(2, n_matches-1)), (mid, 1)),
            ((high, 1), (mid, min(2, n_matches-1))),
            ((high, 1), (mid, min(1, n_matches-1)), (low, min(1, max(0, n_matches-2)))),
            ((mid, min(2, n_matches)), (low, min(1, max(0, n_matches-2)))),
        ]
    else:
        ticket_combos = [
            ((very_high, 1), (high, min(1, n_matches-1))),
            ((high, min(2, n_matches)),),
            ((mid, min(2, n_matches)),),
        ]

    ATTEMPTS_PER_COMBO = 6
    for combo in ticket_combos:
        pools_cfg = list(combo)
        for _ in range(ATTEMPTS_PER_COMBO):
            for pl, _ in pools_cfg:
                random.shuffle(pl)
            legs = pick_legs(pools_cfg)
            if legs:
                total = round(math.prod(l['odd'] for l in legs), 1)
                if total >= 3.0:  # mínimo para cualquier tier
                    tickets.append({
                        'tier': 'pending',  # se clasifica abajo
                        'legs': legs,
                        'total_odds': total,
                        'confidence': calculate_confidence(legs),
                    })

    # Classify tiers by total odds
    for t in tickets:
        odds = t['total_odds']
        if odds >= 1000:
            t['tier'] = 'megalodon'
        elif odds >= 100:
            t['tier'] = 'whale'
        elif odds >= 10:
            t['tier'] = 'shark'
        else:
            t['tier'] = 'hunter'

    tier_order = {'megalodon': 0, 'whale': 1, 'shark': 2, 'hunter': 3}
    tickets.sort(key=lambda t: (tier_order[t['tier']], -t['total_odds']))

    # Assign IDs
    counters = {'megalodon': 0, 'whale': 0, 'shark': 0, 'hunter': 0}
    for ticket in tickets:
        tier = ticket['tier']
        counters[tier] += 1
        ticket['id'] = f"{tier[0].upper()}{counters[tier]}"
        sports_in = list(set(l['sport'] for l in ticket['legs']))
        if len(sports_in) == 1:
            ticket['title'] = f"{SPORT_NAMES.get(sports_in[0], 'Multi')} Props Mix"
        elif len(sports_in) == 2:
            ticket['title'] = f"{SPORT_NAMES.get(sports_in[0], '?')} + {SPORT_NAMES.get(sports_in[1], '?')}"
        else:
            ticket['title'] = f"Multi-Sport x{len(sports_in)}"

    # Verify: zero duplicate props AND max 1 leg per match per ticket AND max 1 leg >x5.00
    all_keys = []
    for t in tickets:
        high_odds_count = sum(1 for l in t['legs'] if l['odd'] > 5.00)
        assert high_odds_count <= 1, \
            f"REGLA VIOLADA en {t['id']}: {high_odds_count} selecciones >x5.00 (máx 1)"
        match_check = set()
        for l in t['legs']:
            all_keys.append(prop_key(l))
            assert l['match'] not in match_check, \
                f"DUPLICATE MATCH in {t['id']}: {l['match']}"
            match_check.add(l['match'])
    assert len(all_keys) == len(set(all_keys)), "DUPLICATE PROP FOUND!"

    return tickets


def generate_ticket_js(tickets):
    """PRINCIPIO 2: Cada billete lleva publishedAt — lo publicado no se modifica."""
    if not tickets:
        return "const TICKETS = [];"
    published_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    lines = ["const TICKETS = ["]
    for ticket in tickets:
        legs_js = []
        for leg in ticket['legs']:
            # Convert link to Spanish version
            leg_link = leg.get('link', '').replace('/en/', '/es/')
            legs_js.append(
                f"    {{player:'{_esc(leg['player'])}', "
                f"prop:'{_esc(leg['prop'])}', "
                f"match:'{_esc(leg['match'])}', "
                f"odd:{leg['odd']}, sport:'{leg['sport']}', "
                f"team:'{_esc(leg['team'])}', date:'{leg.get('date', '')}', "
                f"logo:'{_esc(leg.get('logo', ''))}', "
                f"link:'{_esc(leg_link)}'}}"
            )
        sport_counts = {}
        for leg in ticket['legs']:
            sport_counts[leg['sport']] = sport_counts.get(leg['sport'], 0) + 1
        primary_sport = max(sport_counts, key=sport_counts.get)
        lines.append(
            f"  {{ id:'{ticket['id']}', tier:'{ticket['tier']}', "
            f"sport:'{primary_sport}', title:'{_esc(ticket['title'])}', "
            f"confidence:{ticket['confidence']}, totalOdds:{ticket['total_odds']}, "
            f"publishedAt:'{published_at}', "
            f"couponCode:'{_esc(ticket.get('coupon_code', ''))}', legs:[\n" +
            ",\n".join(legs_js) +
            "\n  ]},"
        )
    lines.append("];")
    return "\n".join(lines)


def generate_results_js(tickets):
    # In live mode, no resolved results yet
    return "const LEG_RESULTS = {};"


def update_html(tickets_js, results_js, filepath):
    content = filepath.read_text(encoding='utf-8')
    pattern = r'const TICKETS = \[[\s\S]*?\];'
    if re.search(pattern, content):
        content = re.sub(pattern, tickets_js, content, count=1)
    pattern2 = r'const LEG_RESULTS = \{[^}]*\};'
    if re.search(pattern2, content):
        content = re.sub(pattern2, results_js, content, count=1)
    filepath.write_text(content, encoding='utf-8')
    print(f"  ✅ {filepath.name} updated")


def main():
    print("🚀 MasterProps LIVE Generator v5 — Weekend Edition")
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    # 1. Get token
    print("🔑 Authenticating with DBbet API...")
    token = get_token()
    print("✅ Token obtained")

    # 2. Fetch events
    print("📡 Fetching events with odds...")
    data = fetch_events(token)
    event_count = data.get('count', 0)
    print(f"✅ {event_count} events loaded")

    # 3. Build prop pools — Saturday, Sunday, Combined
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    # Dynamic: HOY (today) and MAÑANA (tomorrow) in Argentina TZ (UTC-3)
    ar_offset = timedelta(hours=-3)
    now_ar = now + ar_offset
    today_ar = now_ar.date()
    tomorrow_ar = today_ar + timedelta(days=1)
    # Convert Argentina day boundaries back to UTC timestamps
    sat_start = (datetime.combine(today_ar, datetime.min.time(), tzinfo=timezone.utc) - ar_offset).timestamp()
    sat_end = (datetime.combine(today_ar, datetime.max.time(), tzinfo=timezone.utc) - ar_offset).timestamp()
    sun_start = (datetime.combine(tomorrow_ar, datetime.min.time(), tzinfo=timezone.utc) - ar_offset).timestamp()
    sun_end = (datetime.combine(tomorrow_ar, datetime.max.time(), tzinfo=timezone.utc) - ar_offset).timestamp()

    print("\n🎯 Building prop pools...")

    print("  📅 HOY:")
    pool_sat = build_prop_pool(data, start_ts_min=sat_start, start_ts_max=sat_end, day_label='sat')
    print(f"     ✅ {len(pool_sat)} props")

    print("  📅 MAÑANA:")
    pool_sun = build_prop_pool(data, start_ts_min=sun_start, start_ts_max=sun_end, day_label='sun')
    print(f"     ✅ {len(pool_sun)} props")

    print("  📅 HOY+MAÑANA (combinado):")
    pool_weekend = build_prop_pool(data, start_ts_min=sat_start, start_ts_max=sun_end, day_label='weekend')
    print(f"     ✅ {len(pool_weekend)} props")

    # 4. Generate tickets for each group
    all_tickets = []

    # Saturday tickets (sharks, hunters, whales)
    if pool_sat:
        print("\n🎰 === HOY — Building tickets ===")
        sat_tickets = build_tickets(pool_sat)
        # Re-prefix IDs to avoid collisions: SAT-M1, SAT-W1, etc.
        for t in sat_tickets:
            t['id'] = f"SAT-{t['id']}"
            t['title'] = f"Hoy · {t['title']}"
        all_tickets.extend(sat_tickets)
        print(f"  ✅ {len(sat_tickets)} tickets hoy")
    else:
        print("\n⚠️  No props for HOY")

    # Sunday tickets (sharks, hunters, whales)
    if pool_sun:
        print("\n🎰 === MAÑANA — Building tickets ===")
        sun_tickets = build_tickets(pool_sun)
        for t in sun_tickets:
            t['id'] = f"SUN-{t['id']}"
            t['title'] = f"Mañ · {t['title']}"
        all_tickets.extend(sun_tickets)
        print(f"  ✅ {len(sun_tickets)} tickets mañana")
    else:
        print("\n⚠️  No props for MAÑANA")

    # Combined weekend — Megalodones and Whales ONLY (x100+)
    if pool_weekend:
        print("\n🎰 === HOY+MAÑANA — Megalodones & Whales ===")
        weekend_tickets = build_tickets(pool_weekend)
        # Only keep megalodones and whales from the combined pool
        mega_whale = [t for t in weekend_tickets if t['tier'] in ('megalodon', 'whale')]
        for t in mega_whale:
            t['id'] = f"WKD-{t['id']}"
            t['title'] = f"Wkd · {t['title']}"
        all_tickets.extend(mega_whale)
        print(f"  ✅ {len(mega_whale)} megalodones/whales 48h")
    else:
        print("\n⚠️  No props for HOY+MAÑANA")

    tickets = all_tickets

    # Sort: megalodones first, then whales, sharks, hunters
    tier_order = {'megalodon': 0, 'whale': 1, 'shark': 2, 'hunter': 3}
    tickets.sort(key=lambda t: (tier_order[t['tier']], -t['total_odds']))

    print(f"\n📊 RESUMEN TOTAL: {len(tickets)} tickets")
    for t in tickets:
        sports_in = set(l['sport'] for l in t['legs'])
        print(f"  {t['id']:12s} [{t['tier'].upper():10s}] x{t['total_odds']:>8.1f} | "
              f"{len(t['legs'])} legs | {', '.join(sports_in)} | conf: {t['confidence']}/6")
        for l in t['legs']:
            print(f"      x{l['odd']:.2f} {l['player'][:20]:20s} {l['prop'][:40]}")

    # 5. Generate tickets_data.json for coupon code generation
    tickets_data = []
    for t in tickets:
        events = []
        for leg in t['legs']:
            events.append({
                'GameId': leg.get('game_id', 0),
                'Type': leg.get('type_id', 0),
                'Coef': leg['odd'],
                'Param': leg.get('param', 0),
                'PlayerId': leg.get('player_id', 0),
            })
        tickets_data.append({
            'ticket_id': t['id'],
            'events': events,
        })

    TICKETS_DATA_FILE = BASE_DIR / 'tickets_data.json'
    TICKETS_DATA_FILE.write_text(json.dumps(tickets_data, indent=2), encoding='utf-8')
    print(f"\n📋 tickets_data.json saved ({len(tickets_data)} tickets)")

    # 5b. Generate coupon codes via Playwright (if available)
    coupons = {}
    try:
        from generate_coupons import generate_coupon_codes
        print("\n🎫 Generating coupon codes via Playwright...")
        coupons = generate_coupon_codes(tickets_data)
        print(f"✅ Generated {len(coupons)} coupon codes")
    except ImportError:
        print("\n⚠️  Playwright not available — skipping coupon generation")
        print("   Run: pip install playwright && playwright install chromium")
        print("   Then: python generate_coupons.py")
        if COUPONS_FILE.exists():
            try:
                coupons = json.loads(COUPONS_FILE.read_text(encoding='utf-8'))
                print(f"   📋 Loaded {len(coupons)} existing coupon codes")
            except Exception:
                pass
    except Exception as e:
        print(f"\n⚠️  Coupon generation failed: {e}")
        if COUPONS_FILE.exists():
            try:
                coupons = json.loads(COUPONS_FILE.read_text(encoding='utf-8'))
                print(f"   📋 Loaded {len(coupons)} existing coupon codes")
            except Exception:
                pass

    for t in tickets:
        t['coupon_code'] = coupons.get(t['id'], '')

    # 6. Verify zero duplicates within each group
    # Note: props CAN repeat across groups (sat vs sun vs weekend) — that's expected
    # But within each group, no duplicates allowed
    all_sels = [f"{l['player']}|{l['prop']}" for t in tickets for l in t['legs']]
    unique_sels = len(set(all_sels))
    print(f"\n🔍 Total: {len(all_sels)} selecciones, {unique_sels} únicas")
    # Duplicates across groups (SAT vs WKD) are OK since they share the same pool
    print("✅ Cross-group overlap is expected (weekend reuses sat+sun props)")

    # 7. Copy template → index.html, then inject data
    tickets_js = generate_ticket_js(tickets)
    results_js = generate_results_js(tickets)

    print("\n📝 Updating HTML files...")
    import shutil
    shutil.copy2(TEMPLATE_FILE, OUTPUT_FILE)
    print(f"  📋 template.html → index.html")
    update_html(tickets_js, results_js, OUTPUT_FILE)
    update_html(tickets_js, results_js, TEMPLATE_FILE)

    # 8. Update coupons.json template
    coupon_template = {t['id']: coupons.get(t['id'], '') for t in tickets}
    COUPONS_FILE.write_text(json.dumps(coupon_template, indent=2), encoding='utf-8')
    assigned = sum(1 for v in coupon_template.values() if v)
    print(f"🎫 coupons.json saved ({assigned}/{len(coupon_template)} codes assigned)")

    print("\n🎉 DONE — Weekend tickets generated from DBbet API!")


if __name__ == '__main__':
    main()
