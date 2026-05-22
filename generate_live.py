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

# ── Interesting market keywords ──
INTERESTING_KEYWORDS = [
    'Handicap', 'Total', 'Both Teams', 'HT-FT', 'Win And Total',
    'Individual Total', 'Race To', 'W1', 'W2', 'To Win',
    'Next Goal', 'Clean Sheet', 'Win To Nil', 'To Score',
]

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
           f"&partnerLink={PARTNER_LINK}")
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req, timeout=30) as resp:
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
    """Build a Spanish-friendly match string."""
    t1_es = translate_name(t1)
    t2_es = translate_name(t2)
    if tournament:
        short = tournament.split('.')[-1].strip() if '.' in tournament else tournament
        # Translate common tournament fragments
        short = short.replace('World Cup', 'Mundial')
        short = short.replace('Champions League', 'Champions')
        short = short.replace('Premier League', 'Premier League')
        short = short.replace('Germany DFB Pokal', 'Copa de Alemania')
        short = short.replace('Coupe de France', 'Copa de Francia')
        short = short.replace('Russian Cup', 'Copa de Rusia')
        return f"{t1_es} vs {t2_es} — {short}"
    return f"{t1_es} vs {t2_es}"


def build_prop_pool(data):
    """Convert API events into a PROP_POOL compatible format."""
    props = []

    for event in data.get('items', []):
        sport_id = event.get('sportId', 0)
        sport = SPORT_MAP.get(sport_id, 'futbol')
        t1 = event.get('opponent1NameLocalization', 'Team A')
        t2 = event.get('opponent2NameLocalization', 'Team B')
        match = f"{t1} vs {t2}"
        tournament = event.get('tournamentNameLocalization', '')
        link = event.get('link', '')
        start_ts = event.get('startDate', 0)
        date_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime('%b %d') if start_ts else 'TBD'
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
                player, team, logo = t1, ab1, logo1
            elif '2' in display and '1' not in display:
                player, team, logo = t2, ab2, logo2
            else:
                player, team, logo = t1, ab1, logo1

            # Translate names and match
            player_es = translate_name(player)
            match_display = translate_match(t1, t2, tournament)

            props.append({
                'player': player_es,
                'prop': translate(display),
                'match': match_display,
                'odd': round(odds_val, 2),
                'sport': sport,
                'team': team,
                'date': date_str,
                'link': link,
                'logo': logo,
            })

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
    tickets = []
    used_keys = set()

    # Split pool by odds range
    low = [p for p in pool if 1.30 <= p['odd'] < 1.55]
    mid = [p for p in pool if 1.55 <= p['odd'] <= 2.80]
    high = [p for p in pool if 2.80 < p['odd'] <= 5.00]
    very_high = [p for p in pool if 5.00 < p['odd'] <= 15.0]

    print(f"   low(1.3-1.55): {len(low)}, mid(1.55-2.8): {len(mid)}, "
          f"high(2.8-5): {len(high)}, vhigh(5-15): {len(very_high)}")

    def pick_legs(pools_config, min_sports=2):
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
                selected.append(p)
                sports_used.add(p['sport'])
                matches_used.add(p['match'])
                picked += 1
        total_needed = sum(c for _, c in pools_config)
        if len(selected) >= total_needed and len(sports_used) >= min_sports:
            for s in selected:
                used_keys.add(prop_key(s))
            return selected
        return None

    # === MEGALODON: very high odds legs ===
    for _ in range(2):
        random.shuffle(very_high)
        legs = pick_legs([(very_high, 3), (high, 2)], min_sports=1)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if total >= 500:
                tickets.append({
                    'tier': 'megalodon', 'legs': legs,
                    'total_odds': total,
                    'confidence': calculate_confidence(legs),
                })

    # === WHALE TICKETS: 5-7 legs, high total odds ===
    for _ in range(3):
        n_high = random.randint(2, 3)
        n_mid = random.randint(2, 3)
        n_low = random.randint(1, 2)
        legs = pick_legs([(low, n_low), (mid, n_mid), (high, n_high)], min_sports=1)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if total >= 40:
                tickets.append({
                    'tier': 'whale', 'legs': legs,
                    'total_odds': total,
                    'confidence': calculate_confidence(legs),
                })

    # === SHARK TICKETS: 4-5 legs, medium total odds ===
    for _ in range(5):
        n_mid = random.randint(2, 3)
        n_high = random.randint(1, 2)
        legs = pick_legs([(mid, n_mid), (high, n_high)], min_sports=1)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if 15 <= total <= 200:
                tickets.append({
                    'tier': 'shark', 'legs': legs,
                    'total_odds': total,
                    'confidence': calculate_confidence(legs),
                })

    # === HUNTER TICKETS: 4 legs, safer ===
    for _ in range(5):
        n_low = random.randint(1, 2)
        n_mid = random.randint(2, 3)
        legs = pick_legs([(low, n_low), (mid, n_mid)], min_sports=1)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if 5 <= total <= 40:
                tickets.append({
                    'tier': 'hunter', 'legs': legs,
                    'total_odds': total,
                    'confidence': calculate_confidence(legs),
                })

    # Promote whales with x1000+ to megalodon
    for t in tickets:
        if t['tier'] == 'whale' and t['total_odds'] >= 1000:
            t['tier'] = 'megalodon'

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

    # Verify zero duplicates
    all_keys = []
    for t in tickets:
        for l in t['legs']:
            all_keys.append(prop_key(l))
    assert len(all_keys) == len(set(all_keys)), "DUPLICATE FOUND!"

    return tickets


def generate_ticket_js(tickets):
    if not tickets:
        return "const TICKETS = [];"
    lines = ["const TICKETS = ["]
    for ticket in tickets:
        legs_js = []
        for leg in ticket['legs']:
            legs_js.append(
                f"    {{player:'{_esc(leg['player'])}', "
                f"prop:'{_esc(leg['prop'])}', "
                f"match:'{_esc(leg['match'])}', "
                f"odd:{leg['odd']}, sport:'{leg['sport']}', "
                f"team:'{_esc(leg['team'])}', date:'{leg.get('date', '')}', "
                f"logo:'{_esc(leg.get('logo', ''))}'}}"
            )
        sport_counts = {}
        for leg in ticket['legs']:
            sport_counts[leg['sport']] = sport_counts.get(leg['sport'], 0) + 1
        primary_sport = max(sport_counts, key=sport_counts.get)
        lines.append(
            f"  {{ id:'{ticket['id']}', tier:'{ticket['tier']}', "
            f"sport:'{primary_sport}', title:'{_esc(ticket['title'])}', "
            f"confidence:{ticket['confidence']}, totalOdds:{ticket['total_odds']}, "
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
    print("🚀 MasterProps LIVE Generator v4 — Real API Data")
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

    # 3. Build prop pool
    print("🎯 Building prop pool from API data...")
    pool = build_prop_pool(data)
    print(f"✅ {len(pool)} props extracted")

    # 4. Generate tickets
    print("\n🎰 Building tickets...")
    tickets = build_tickets(pool)
    print(f"✅ Generated {len(tickets)} tickets:")

    for t in tickets:
        sports_in = set(l['sport'] for l in t['legs'])
        print(f"  {t['id']} [{t['tier'].upper():10s}] x{t['total_odds']:>8.1f} | "
              f"{len(t['legs'])} legs | {', '.join(sports_in)} | conf: {t['confidence']}/6")
        for l in t['legs']:
            print(f"      x{l['odd']:.2f} {l['player'][:20]:20s} {l['prop'][:40]}")

    # 5. Load coupons
    coupons = {}
    if COUPONS_FILE.exists():
        try:
            coupons = json.loads(COUPONS_FILE.read_text(encoding='utf-8'))
            print(f"\n🎫 Loaded {len(coupons)} coupon codes")
        except Exception:
            pass
    for t in tickets:
        t['coupon_code'] = coupons.get(t['id'], '')

    # 6. Verify zero duplicates
    all_sels = [f"{l['player']}|{l['prop']}" for t in tickets for l in t['legs']]
    print(f"\n🔍 Total: {len(all_sels)} selecciones, {len(set(all_sels))} únicas")
    if len(all_sels) != len(set(all_sels)):
        print("❌ ERROR: HAY DUPLICADOS!")
        return
    print("✅ CERO duplicados")

    # 7. Update HTML
    tickets_js = generate_ticket_js(tickets)
    results_js = generate_results_js(tickets)

    print("\n📝 Updating HTML files...")
    update_html(tickets_js, results_js, OUTPUT_FILE)
    update_html(tickets_js, results_js, TEMPLATE_FILE)

    # 8. Update coupons.json template
    coupon_template = {t['id']: coupons.get(t['id'], '') for t in tickets}
    COUPONS_FILE.write_text(json.dumps(coupon_template, indent=2), encoding='utf-8')
    assigned = sum(1 for v in coupon_template.values() if v)
    print(f"🎫 coupons.json saved ({assigned}/{len(coupon_template)} codes assigned)")

    print("\n🎉 DONE — Live tickets generated from DBbet API!")


if __name__ == '__main__':
    main()
