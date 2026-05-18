#!/usr/bin/env python3
"""
MasterProps.ai — Offline Ticket Generator v2
Uses REAL matchups and results from current 2026 seasons.
Mixes already-resolved selections (with known results) and upcoming ones.
"""

import random
import math
import re
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE_FILE = Path(__file__).parent / 'template.html'
OUTPUT_FILE = Path(__file__).parent / 'index.html'

# ============================================================
# PROP POOL — REAL matchups May 2026
# Each prop has an optional 'result': 'won' or 'lost'
# If absent, selection is still pending (⏳)
# ============================================================
PROP_POOL = [
    # ── NBA CONFERENCE FINALS (starting May 19) ──
    # Thunder vs Spurs (West)
    {'player': 'Shai Gilgeous-Alexander', 'prop': 'Over 30.5 puntos', 'match': 'Oklahoma City Thunder vs San Antonio Spurs', 'odd': 1.82, 'sport': 'nba'},
    {'player': 'Victor Wembanyama', 'prop': 'Over 3.5 tapones', 'match': 'San Antonio Spurs vs Oklahoma City Thunder', 'odd': 2.45, 'sport': 'nba'},
    {'player': 'Chet Holmgren', 'prop': 'Over 2.5 tapones', 'match': 'Oklahoma City Thunder vs San Antonio Spurs', 'odd': 2.30, 'sport': 'nba'},
    {'player': 'Jalen Williams', 'prop': 'Over 20.5 puntos', 'match': 'Oklahoma City Thunder vs San Antonio Spurs', 'odd': 1.90, 'sport': 'nba'},
    {'player': 'Chris Paul', 'prop': 'Over 8.5 asistencias', 'match': 'San Antonio Spurs vs Oklahoma City Thunder', 'odd': 2.15, 'sport': 'nba'},
    {'player': 'Keldon Johnson', 'prop': 'Over 16.5 puntos', 'match': 'San Antonio Spurs vs Oklahoma City Thunder', 'odd': 2.05, 'sport': 'nba'},
    # Knicks vs Cavaliers (East)
    {'player': 'Jalen Brunson', 'prop': 'Over 26.5 puntos', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 1.78, 'sport': 'nba'},
    {'player': 'Donovan Mitchell', 'prop': 'Over 27.5 puntos', 'match': 'Cleveland Cavaliers vs New York Knicks', 'odd': 1.85, 'sport': 'nba'},
    {'player': 'James Harden', 'prop': 'Over 8.5 asistencias', 'match': 'Cleveland Cavaliers vs New York Knicks', 'odd': 2.10, 'sport': 'nba'},
    {'player': 'Karl-Anthony Towns', 'prop': 'Over 10.5 rebotes', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 1.95, 'sport': 'nba'},
    {'player': 'Evan Mobley', 'prop': 'Over 8.5 rebotes', 'match': 'Cleveland Cavaliers vs New York Knicks', 'odd': 1.88, 'sport': 'nba'},
    {'player': 'OG Anunoby', 'prop': 'Over 14.5 puntos', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 2.00, 'sport': 'nba'},
    {'player': 'Darius Garland', 'prop': 'Over 18.5 puntos', 'match': 'Cleveland Cavaliers vs New York Knicks', 'odd': 2.20, 'sport': 'nba'},
    {'player': 'Mikal Bridges', 'prop': 'Over 15.5 puntos', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 1.92, 'sport': 'nba'},

    # ── CHAMPIONS LEAGUE — ALREADY PLAYED (with results) ──
    # QF: Bayern beat Real Madrid 6-4 agg (Apr 7 & 15)
    {'player': 'Harry Kane', 'prop': 'Marca gol en cualquier momento', 'match': 'Bayern Munich vs Real Madrid', 'odd': 1.80, 'sport': 'futbol', 'result': 'won'},
    {'player': 'Kylian Mbappé', 'prop': 'Marca gol en cualquier momento', 'match': 'Real Madrid vs Bayern Munich', 'odd': 1.90, 'sport': 'futbol', 'result': 'won'},
    {'player': 'Vinícius Jr.', 'prop': 'Marca gol en cualquier momento', 'match': 'Real Madrid vs Bayern Munich', 'odd': 2.20, 'sport': 'futbol', 'result': 'lost'},
    # SF: Arsenal beat Atletico 2-1 agg (May 5)
    {'player': 'Bukayo Saka', 'prop': 'Marca gol en cualquier momento', 'match': 'Arsenal vs Atlético Madrid', 'odd': 2.80, 'sport': 'futbol', 'result': 'won'},
    {'player': 'Antoine Griezmann', 'prop': 'Marca gol en cualquier momento', 'match': 'Atlético Madrid vs Arsenal', 'odd': 3.10, 'sport': 'futbol', 'result': 'lost'},
    {'player': 'Julian Álvarez', 'prop': 'Marca gol en cualquier momento', 'match': 'Atlético Madrid vs Arsenal', 'odd': 2.60, 'sport': 'futbol', 'result': 'lost'},
    # SF: PSG beat Bayern 6-5 agg (May 6-7)
    {'player': 'Ousmane Dembélé', 'prop': 'Marca gol en cualquier momento', 'match': 'PSG vs Bayern Munich', 'odd': 2.50, 'sport': 'futbol', 'result': 'won'},

    # ── CHAMPIONS LEAGUE FINAL (May 30) — PENDING ──
    {'player': 'Bukayo Saka', 'prop': 'Marca gol en cualquier momento', 'match': 'Arsenal vs PSG — Final UCL', 'odd': 2.90, 'sport': 'futbol'},
    {'player': 'Ousmane Dembélé', 'prop': 'Marca gol en cualquier momento', 'match': 'PSG vs Arsenal — Final UCL', 'odd': 2.75, 'sport': 'futbol'},
    {'player': 'Kai Havertz', 'prop': 'Marca gol en cualquier momento', 'match': 'Arsenal vs PSG — Final UCL', 'odd': 3.30, 'sport': 'futbol'},
    {'player': 'Bradley Barcola', 'prop': 'Marca gol en cualquier momento', 'match': 'PSG vs Arsenal — Final UCL', 'odd': 3.00, 'sport': 'futbol'},
    {'player': 'Martin Ødegaard', 'prop': 'Marca gol en cualquier momento', 'match': 'Arsenal vs PSG — Final UCL', 'odd': 3.50, 'sport': 'futbol'},
    {'player': 'Marco Asensio', 'prop': 'Marca gol en cualquier momento', 'match': 'PSG vs Arsenal — Final UCL', 'odd': 3.80, 'sport': 'futbol'},
    {'player': 'Gabriel Jesus', 'prop': 'Marca gol en cualquier momento', 'match': 'Arsenal vs PSG — Final UCL', 'odd': 3.20, 'sport': 'futbol'},

    # ── LIGA ARGENTINA — ALREADY PLAYED ──
    {'player': 'Adam Bareiro', 'prop': 'Marca gol en cualquier momento', 'match': 'River Plate vs Boca Juniors', 'odd': 3.50, 'sport': 'futbol', 'result': 'lost'},
    {'player': 'Maxi Salas', 'prop': 'Marca gol en cualquier momento', 'match': 'River Plate vs Boca Juniors', 'odd': 3.20, 'sport': 'futbol', 'result': 'lost'},

    # ── MLB (this week, upcoming) ──
    # May 18: Dodgers @ San Diego, Yankees @ Toronto, Reds @ Phillies, etc.
    {'player': 'Shohei Ohtani', 'prop': 'Over 1.5 bases totales', 'match': 'Los Angeles Dodgers vs San Diego Padres', 'odd': 1.65, 'sport': 'mlb'},
    {'player': 'Mookie Betts', 'prop': 'Over 1.5 hits', 'match': 'Los Angeles Dodgers vs San Diego Padres', 'odd': 2.40, 'sport': 'mlb'},
    {'player': 'Freddie Freeman', 'prop': 'Over 0.5 hits', 'match': 'Los Angeles Dodgers vs San Diego Padres', 'odd': 1.25, 'sport': 'mlb'},
    {'player': 'Aaron Judge', 'prop': 'Home Run: Sí', 'match': 'New York Yankees vs Toronto Blue Jays', 'odd': 3.50, 'sport': 'mlb'},
    {'player': 'Juan Soto', 'prop': 'Over 1.5 bases totales', 'match': 'New York Mets vs Washington Nationals', 'odd': 1.78, 'sport': 'mlb'},
    {'player': 'Bryce Harper', 'prop': 'Over 1.5 hits', 'match': 'Cincinnati Reds vs Philadelphia Phillies', 'odd': 2.25, 'sport': 'mlb'},
    {'player': 'Ronald Acuña Jr.', 'prop': 'Over 1.5 bases totales', 'match': 'Atlanta Braves vs Miami Marlins', 'odd': 1.70, 'sport': 'mlb'},
    {'player': 'Yordan Alvarez', 'prop': 'Over 1.5 bases totales', 'match': 'Houston Astros vs Minnesota Twins', 'odd': 1.82, 'sport': 'mlb'},
    {'player': 'Bobby Witt Jr.', 'prop': 'Over 1.5 hits', 'match': 'Boston Red Sox vs Kansas City Royals', 'odd': 2.15, 'sport': 'mlb'},
    {'player': 'Gerrit Cole', 'prop': 'Over 6.5 strikeouts', 'match': 'New York Yankees vs Toronto Blue Jays', 'odd': 1.85, 'sport': 'mlb'},
    {'player': 'Corbin Burnes', 'prop': 'Over 5.5 strikeouts', 'match': 'Arizona Diamondbacks vs San Francisco Giants', 'odd': 1.72, 'sport': 'mlb'},
    {'player': 'Corey Seager', 'prop': 'Over 1.5 bases totales', 'match': 'Texas Rangers vs Colorado Rockies', 'odd': 1.80, 'sport': 'mlb'},

    # ── ROLAND GARROS (starts ~May 25) ──
    {'player': 'Jannik Sinner', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros 2026 — 1ra Ronda', 'odd': 1.08, 'sport': 'tenis'},
    {'player': 'Carlos Alcaraz', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros 2026 — 1ra Ronda', 'odd': 1.12, 'sport': 'tenis'},
    {'player': 'Alexander Zverev', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros 2026 — 1ra Ronda', 'odd': 1.10, 'sport': 'tenis'},
    {'player': 'Novak Djokovic', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros 2026 — 1ra Ronda', 'odd': 1.15, 'sport': 'tenis'},
    {'player': 'Iga Świątek', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros 2026 — 1ra Ronda', 'odd': 1.05, 'sport': 'tenis'},
    {'player': 'Aryna Sabalenka', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros 2026 — 1ra Ronda', 'odd': 1.08, 'sport': 'tenis'},
    {'player': 'Coco Gauff', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros 2026 — 1ra Ronda', 'odd': 1.10, 'sport': 'tenis'},

    # ── NHL CONFERENCE FINALS (starts May 20) ──
    {'player': 'Nathan MacKinnon', 'prop': 'Over 1.5 puntos', 'match': 'Colorado Avalanche vs Vegas Golden Knights', 'odd': 1.85, 'sport': 'nhl'},
    {'player': 'Cale Makar', 'prop': 'Over 0.5 goles', 'match': 'Colorado Avalanche vs Vegas Golden Knights', 'odd': 2.80, 'sport': 'nhl'},
    {'player': 'Jack Eichel', 'prop': 'Over 0.5 goles', 'match': 'Vegas Golden Knights vs Colorado Avalanche', 'odd': 2.60, 'sport': 'nhl'},
    {'player': 'Mikko Rantanen', 'prop': 'Over 0.5 goles', 'match': 'Colorado Avalanche vs Vegas Golden Knights', 'odd': 2.30, 'sport': 'nhl'},
    {'player': 'Mark Stone', 'prop': 'Over 0.5 puntos', 'match': 'Vegas Golden Knights vs Colorado Avalanche', 'odd': 1.70, 'sport': 'nhl'},

    # ── UFC FREEDOM 250 (June 14) ──
    {'player': 'Alex Pereira', 'prop': 'Gana la pelea', 'match': 'A. Pereira vs C. Gane — UFC Freedom 250', 'odd': 1.70, 'sport': 'mma'},
]


def _esc(s):
    return str(s).replace("'", "\\'").replace("\n", " ")


def calculate_confidence(legs):
    probs = [1/leg['odd'] for leg in legs]
    avg_prob = sum(probs) / len(probs)
    n_legs = len(legs)
    if avg_prob > 0.55: base = 5
    elif avg_prob > 0.45: base = 4
    elif avg_prob > 0.35: base = 3
    elif avg_prob > 0.25: base = 2
    else: base = 1
    if n_legs >= 6: base = max(1, base - 2)
    elif n_legs >= 5: base = max(1, base - 1)
    variance = sum((p - avg_prob) ** 2 for p in probs) / len(probs)
    if variance < 0.01: base = min(6, base + 1)
    return min(6, max(1, base))


def build_tickets():
    tickets = []

    # Separate pools
    resolved_won = [p for p in PROP_POOL if p.get('result') == 'won']
    resolved_lost = [p for p in PROP_POOL if p.get('result') == 'lost']
    pending = [p for p in PROP_POOL if 'result' not in p]

    low = [p for p in pending if 1.01 <= p['odd'] < 1.55]
    mid = [p for p in pending if 1.55 <= p['odd'] <= 2.80]
    high = [p for p in pending if 2.80 < p['odd'] <= 5.00]

    def pick_legs(pools_config, min_sports=2):
        selected = []
        sports_used = set()
        players_used = set()
        for pool, count in pools_config:
            available = [p for p in pool if p['player'] not in players_used]
            random.shuffle(available)
            picked = 0
            for p in available:
                if picked >= count:
                    break
                selected.append(p)
                sports_used.add(p['sport'])
                players_used.add(p['player'])
                picked += 1
        total_needed = sum(c for _, c in pools_config)
        if len(selected) >= total_needed and len(sports_used) >= min_sports:
            return selected
        return None

    # Strategy: build tickets that MIX resolved legs with pending legs
    # This makes heat system visible immediately

    # === WHALE TICKETS: long tickets with some resolved anchors ===
    for i in range(3):
        random.shuffle(pending)
        # Include 1-2 resolved won legs as "heat anchors"
        anchor_won = random.sample(resolved_won, min(2, len(resolved_won)))
        n_pending = random.choice([5, 6])
        n_low = random.randint(1, min(2, n_pending))
        n_mid = random.randint(1, min(3, n_pending - n_low))
        n_high = n_pending - n_low - n_mid
        if n_high < 1: n_high = 1; n_mid = max(1, n_pending - n_low - n_high)
        pending_legs = pick_legs([(low, n_low), (mid, n_mid), (high, max(1, n_high))], min_sports=1)
        if pending_legs:
            legs = anchor_won + pending_legs
            # Ensure multi-sport
            sports = set(l['sport'] for l in legs)
            if len(sports) >= 2:
                total = round(math.prod(l['odd'] for l in legs), 1)
                if total >= 40:
                    tickets.append({
                        'tier': 'whale',
                        'legs': legs,
                        'total_odds': total,
                        'confidence': calculate_confidence(legs),
                    })

    # === SHARK TICKETS: mix resolved + pending ===
    for i in range(4):
        random.shuffle(pending)
        # 1 resolved won anchor
        anchor_won = random.sample(resolved_won, min(1, len(resolved_won)))
        n_pending = random.choice([4, 5])
        n_low = random.randint(0, min(1, n_pending))
        n_mid = random.randint(1, min(3, n_pending - n_low))
        n_high = n_pending - n_low - n_mid
        if n_high < 0: n_high = 0
        pools = []
        if n_low > 0: pools.append((low, n_low))
        if n_mid > 0: pools.append((mid, n_mid))
        if n_high > 0: pools.append((high, n_high))
        pending_legs = pick_legs(pools, min_sports=1)
        if pending_legs:
            legs = anchor_won + pending_legs
            sports = set(l['sport'] for l in legs)
            if len(sports) >= 2:
                total = round(math.prod(l['odd'] for l in legs), 1)
                if 15 <= total <= 120:
                    tickets.append({
                        'tier': 'shark',
                        'legs': legs,
                        'total_odds': total,
                        'confidence': calculate_confidence(legs),
                    })

    # === HUNTER TICKETS: safer, some all-pending ===
    for i in range(5):
        random.shuffle(pending)
        n_legs = random.choice([4, 5])
        n_low = random.randint(1, min(2, n_legs - 1))
        n_mid = n_legs - n_low
        legs = pick_legs([(low, n_low), (mid, n_mid)], min_sports=2)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if 5 <= total <= 40:
                tickets.append({
                    'tier': 'hunter',
                    'legs': legs,
                    'total_odds': total,
                    'confidence': calculate_confidence(legs),
                })

    # === BONUS: one "dead" ticket with a lost leg for visual contrast ===
    random.shuffle(pending)
    dead_anchor = random.sample(resolved_lost, min(1, len(resolved_lost)))
    dead_pending = pick_legs([(mid, 3), (high, 1)], min_sports=1)
    if dead_pending and dead_anchor:
        legs = dead_anchor + dead_pending
        sports = set(l['sport'] for l in legs)
        if len(sports) >= 2:
            total = round(math.prod(l['odd'] for l in legs), 1)
            tickets.append({
                'tier': 'shark',
                'legs': legs,
                'total_odds': total,
                'confidence': calculate_confidence(legs),
            })

    # Sort: whales first, then sharks, then hunters
    tier_order = {'whale': 0, 'shark': 1, 'hunter': 2}
    tickets.sort(key=lambda t: (tier_order[t['tier']], -t['total_odds']))

    # Assign IDs and titles
    sport_names = {
        'nba': 'NBA', 'mlb': 'MLB', 'futbol': 'Fútbol',
        'tenis': 'Tenis', 'mma': 'MMA', 'nhl': 'NHL'
    }
    counters = {'whale': 0, 'shark': 0, 'hunter': 0}
    for ticket in tickets:
        tier = ticket['tier']
        counters[tier] += 1
        ticket['id'] = f"{tier[0].upper()}{counters[tier]}"
        sports_in = list(set(l['sport'] for l in ticket['legs']))
        if len(sports_in) == 1:
            ticket['title'] = f"{sport_names.get(sports_in[0], 'Multi')} Props Mix"
        elif len(sports_in) == 2:
            ticket['title'] = f"{sport_names.get(sports_in[0], '?')} + {sport_names.get(sports_in[1], '?')}"
        else:
            ticket['title'] = f"Multi-Sport x{len(sports_in)}"

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
                f"odd:{leg['odd']}, sport:'{leg['sport']}'}}"
            )
        sport_counts = {}
        for leg in ticket['legs']:
            sport_counts[leg['sport']] = sport_counts.get(leg['sport'], 0) + 1
        primary_sport = max(sport_counts, key=sport_counts.get)
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


def generate_results_js(tickets):
    """Generate LEG_RESULTS from resolved props."""
    results = {}
    for ticket in tickets:
        for j, leg in enumerate(ticket['legs']):
            if 'result' in leg:
                key = f"{ticket['id']}_{j}"
                results[key] = leg['result']
    if not results:
        return "const LEG_RESULTS = {};"
    entries = ", ".join(f"'{k}':'{v}'" for k, v in results.items())
    return f"const LEG_RESULTS = {{{entries}}};"


def update_html(tickets_js, results_js, filepath):
    content = filepath.read_text(encoding='utf-8')
    # Replace TICKETS
    pattern = r'const TICKETS = \[[\s\S]*?\];'
    if re.search(pattern, content):
        content = re.sub(pattern, tickets_js, content, count=1)
    # Replace LEG_RESULTS
    pattern2 = r'const LEG_RESULTS = \{[^}]*\};'
    if re.search(pattern2, content):
        content = re.sub(pattern2, results_js, content, count=1)
    filepath.write_text(content, encoding='utf-8')
    print(f"  ✅ {filepath.name} updated")


def main():
    print("🚀 MasterProps Offline Generator v2 — REAL DATA")
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    resolved = [p for p in PROP_POOL if 'result' in p]
    pending = [p for p in PROP_POOL if 'result' not in p]
    print(f"📊 Pool: {len(PROP_POOL)} props ({len(resolved)} resolved, {len(pending)} pending)")
    print()

    tickets = build_tickets()
    print(f"🎰 Generated {len(tickets)} tickets:")
    for t in tickets:
        sports_in = set(l['sport'] for l in t['legs'])
        won = sum(1 for l in t['legs'] if l.get('result') == 'won')
        lost = sum(1 for l in t['legs'] if l.get('result') == 'lost')
        heat = f"🔥 {won}✅" if won > 0 else ""
        dead = f"💀 {lost}❌" if lost > 0 else ""
        print(f"  {t['id']} [{t['tier'].upper()}] x{t['total_odds']} | "
              f"{len(t['legs'])} legs | {', '.join(sports_in)} | "
              f"conf: {t['confidence']}/6 {heat} {dead}")

    tickets_js = generate_ticket_js(tickets)
    results_js = generate_results_js(tickets)

    print(f"\n📝 LEG_RESULTS: {results_js[:100]}...")
    print("\n📝 Updating HTML files...")
    update_html(tickets_js, results_js, OUTPUT_FILE)
    update_html(tickets_js, results_js, TEMPLATE_FILE)

    print(f"\n✅ Done! {len(tickets)} tickets with REAL data.")


if __name__ == '__main__':
    main()
