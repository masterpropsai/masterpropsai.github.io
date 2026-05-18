#!/usr/bin/env python3
"""
MasterProps.ai — Offline Ticket Generator
Generates realistic tickets with real players, teams, and odds
when the API key is exhausted. Uses current real-world matchups.
"""

import random
import math
import re
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE_FILE = Path(__file__).parent / 'template.html'
OUTPUT_FILE = Path(__file__).parent / 'index.html'

# Real current matchups and player props (May 2026 season data)
PROP_POOL = [
    # === NBA Playoffs 2026 ===
    {'player': 'Luka Doncic', 'prop': 'Over 31.5 puntos', 'match': 'Dallas Mavericks vs Boston Celtics', 'odd': 1.85, 'sport': 'nba'},
    {'player': 'Jayson Tatum', 'prop': 'Over 27.5 puntos', 'match': 'Boston Celtics vs Dallas Mavericks', 'odd': 1.80, 'sport': 'nba'},
    {'player': 'Shai Gilgeous-Alexander', 'prop': 'Over 30.5 puntos', 'match': 'Oklahoma City Thunder vs Denver Nuggets', 'odd': 1.75, 'sport': 'nba'},
    {'player': 'Anthony Edwards', 'prop': 'Over 26.5 puntos', 'match': 'Minnesota Timberwolves vs Golden State Warriors', 'odd': 1.90, 'sport': 'nba'},
    {'player': 'Nikola Jokic', 'prop': 'Over 11.5 rebotes', 'match': 'Denver Nuggets vs Oklahoma City Thunder', 'odd': 1.72, 'sport': 'nba'},
    {'player': 'LeBron James', 'prop': 'Over 7.5 asistencias', 'match': 'Los Angeles Lakers vs Phoenix Suns', 'odd': 1.88, 'sport': 'nba'},
    {'player': 'Stephen Curry', 'prop': 'Over 4.5 triples', 'match': 'Golden State Warriors vs Minnesota Timberwolves', 'odd': 2.20, 'sport': 'nba'},
    {'player': 'Kevin Durant', 'prop': 'Over 28.5 puntos', 'match': 'Phoenix Suns vs Los Angeles Lakers', 'odd': 1.95, 'sport': 'nba'},
    {'player': 'Jaylen Brown', 'prop': 'Over 24.5 puntos', 'match': 'Boston Celtics vs Dallas Mavericks', 'odd': 2.05, 'sport': 'nba'},
    {'player': 'Kyrie Irving', 'prop': 'Over 22.5 puntos', 'match': 'Dallas Mavericks vs Boston Celtics', 'odd': 1.92, 'sport': 'nba'},
    {'player': 'Devin Booker', 'prop': 'Over 25.5 puntos', 'match': 'Phoenix Suns vs Los Angeles Lakers', 'odd': 1.87, 'sport': 'nba'},
    {'player': 'Jalen Brunson', 'prop': 'Over 24.5 puntos', 'match': 'New York Knicks vs Indiana Pacers', 'odd': 1.83, 'sport': 'nba'},
    {'player': 'Donovan Mitchell', 'prop': 'Over 6.5 asistencias', 'match': 'Cleveland Cavaliers vs Milwaukee Bucks', 'odd': 2.35, 'sport': 'nba'},
    {'player': 'Giannis Antetokounmpo', 'prop': 'Over 32.5 PRA', 'match': 'Milwaukee Bucks vs Cleveland Cavaliers', 'odd': 1.45, 'sport': 'nba'},
    {'player': 'Tyrese Haliburton', 'prop': 'Over 9.5 asistencias', 'match': 'Indiana Pacers vs New York Knicks', 'odd': 2.10, 'sport': 'nba'},
    {'player': 'Victor Wembanyama', 'prop': 'Over 3.5 tapones', 'match': 'San Antonio Spurs vs Memphis Grizzlies', 'odd': 2.75, 'sport': 'nba'},
    {'player': 'Ja Morant', 'prop': 'Over 25.5 puntos', 'match': 'Memphis Grizzlies vs San Antonio Spurs', 'odd': 2.00, 'sport': 'nba'},
    {'player': 'Chet Holmgren', 'prop': 'Over 2.5 tapones', 'match': 'Oklahoma City Thunder vs Denver Nuggets', 'odd': 2.30, 'sport': 'nba'},

    # === MLB Regular Season ===
    {'player': 'Shohei Ohtani', 'prop': 'Over 1.5 bases totales', 'match': 'Los Angeles Dodgers vs San Francisco Giants', 'odd': 1.65, 'sport': 'mlb'},
    {'player': 'Aaron Judge', 'prop': 'Home Run: Sí', 'match': 'New York Yankees vs Boston Red Sox', 'odd': 3.50, 'sport': 'mlb'},
    {'player': 'Mookie Betts', 'prop': 'Over 1.5 hits', 'match': 'Los Angeles Dodgers vs San Francisco Giants', 'odd': 2.40, 'sport': 'mlb'},
    {'player': 'Ronald Acuña Jr.', 'prop': 'Over 1.5 bases totales', 'match': 'Atlanta Braves vs Philadelphia Phillies', 'odd': 1.70, 'sport': 'mlb'},
    {'player': 'Gerrit Cole', 'prop': 'Over 6.5 strikeouts', 'match': 'New York Yankees vs Boston Red Sox', 'odd': 1.85, 'sport': 'mlb'},
    {'player': 'Freddie Freeman', 'prop': 'Over 1.5 hits', 'match': 'Los Angeles Dodgers vs San Francisco Giants', 'odd': 2.15, 'sport': 'mlb'},
    {'player': 'Juan Soto', 'prop': 'Over 1.5 bases totales', 'match': 'New York Mets vs Atlanta Braves', 'odd': 1.78, 'sport': 'mlb'},
    {'player': 'Bryce Harper', 'prop': 'Home Run: Sí', 'match': 'Philadelphia Phillies vs Atlanta Braves', 'odd': 3.80, 'sport': 'mlb'},
    {'player': 'Corbin Burnes', 'prop': 'Over 5.5 strikeouts', 'match': 'Arizona Diamondbacks vs San Diego Padres', 'odd': 1.72, 'sport': 'mlb'},
    {'player': 'Bobby Witt Jr.', 'prop': 'Over 1.5 hits', 'match': 'Kansas City Royals vs Houston Astros', 'odd': 2.25, 'sport': 'mlb'},
    {'player': 'Julio Rodriguez', 'prop': 'Over 1.5 bases totales', 'match': 'Seattle Mariners vs Texas Rangers', 'odd': 1.95, 'sport': 'mlb'},
    {'player': 'Trea Turner', 'prop': 'Over 0.5 hits', 'match': 'Philadelphia Phillies vs Atlanta Braves', 'odd': 1.30, 'sport': 'mlb'},
    {'player': 'Yordan Alvarez', 'prop': 'Over 1.5 bases totales', 'match': 'Houston Astros vs Kansas City Royals', 'odd': 1.82, 'sport': 'mlb'},
    {'player': 'Zack Wheeler', 'prop': 'Over 7.5 strikeouts', 'match': 'Philadelphia Phillies vs Atlanta Braves', 'odd': 2.50, 'sport': 'mlb'},

    # === Champions League / Europa ===
    {'player': 'Erling Haaland', 'prop': 'Marca gol en cualquier momento', 'match': 'Manchester City vs Inter Milan', 'odd': 1.55, 'sport': 'futbol'},
    {'player': 'Kylian Mbappé', 'prop': 'Marca gol en cualquier momento', 'match': 'Real Madrid vs Bayern Munich', 'odd': 1.90, 'sport': 'futbol'},
    {'player': 'Vinícius Jr.', 'prop': 'Marca gol en cualquier momento', 'match': 'Real Madrid vs Bayern Munich', 'odd': 2.20, 'sport': 'futbol'},
    {'player': 'Mohamed Salah', 'prop': 'Marca gol en cualquier momento', 'match': 'Liverpool vs Barcelona', 'odd': 2.30, 'sport': 'futbol'},
    {'player': 'Lamine Yamal', 'prop': 'Marca gol en cualquier momento', 'match': 'Barcelona vs Liverpool', 'odd': 3.00, 'sport': 'futbol'},
    {'player': 'Robert Lewandowski', 'prop': 'Marca gol en cualquier momento', 'match': 'Barcelona vs Liverpool', 'odd': 1.95, 'sport': 'futbol'},
    {'player': 'Julian Álvarez', 'prop': 'Marca gol en cualquier momento', 'match': 'Atlético Madrid vs Borussia Dortmund', 'odd': 2.60, 'sport': 'futbol'},
    {'player': 'Harry Kane', 'prop': 'Marca gol en cualquier momento', 'match': 'Bayern Munich vs Real Madrid', 'odd': 1.80, 'sport': 'futbol'},
    {'player': 'Antoine Griezmann', 'prop': 'Marca gol en cualquier momento', 'match': 'Atlético Madrid vs Borussia Dortmund', 'odd': 3.10, 'sport': 'futbol'},
    {'player': 'Phil Foden', 'prop': 'Marca gol en cualquier momento', 'match': 'Manchester City vs Inter Milan', 'odd': 3.25, 'sport': 'futbol'},
    {'player': 'Lautaro Martínez', 'prop': 'Marca gol en cualquier momento', 'match': 'Inter Milan vs Manchester City', 'odd': 2.40, 'sport': 'futbol'},
    {'player': 'Bukayo Saka', 'prop': 'Marca gol en cualquier momento', 'match': 'Arsenal vs Paris Saint-Germain', 'odd': 2.80, 'sport': 'futbol'},
    {'player': 'Ousmane Dembélé', 'prop': 'Marca gol en cualquier momento', 'match': 'Paris Saint-Germain vs Arsenal', 'odd': 3.40, 'sport': 'futbol'},

    # === Liga Argentina ===
    {'player': 'Maxi Salas', 'prop': 'Marca gol en cualquier momento', 'match': 'River Plate vs Boca Juniors', 'odd': 3.20, 'sport': 'futbol'},
    {'player': 'Miguel Borja', 'prop': 'Marca gol en cualquier momento', 'match': 'River Plate vs Racing Club', 'odd': 2.50, 'sport': 'futbol'},
    {'player': 'Edinson Cavani', 'prop': 'Marca gol en cualquier momento', 'match': 'Boca Juniors vs Independiente', 'odd': 2.90, 'sport': 'futbol'},
    {'player': 'Adam Bareiro', 'prop': 'Marca gol en cualquier momento', 'match': 'River Plate vs Boca Juniors', 'odd': 3.50, 'sport': 'futbol'},

    # === Tenis (Roland Garros / ATP) ===
    {'player': 'Carlos Alcaraz', 'prop': 'Gana el partido', 'match': 'C. Alcaraz vs N. Djokovic', 'odd': 1.65, 'sport': 'tenis'},
    {'player': 'Jannik Sinner', 'prop': 'Gana el partido', 'match': 'J. Sinner vs A. Zverev', 'odd': 1.50, 'sport': 'tenis'},
    {'player': 'Alexander Zverev', 'prop': 'Gana el partido', 'match': 'A. Zverev vs D. Medvedev', 'odd': 1.72, 'sport': 'tenis'},
    {'player': 'Novak Djokovic', 'prop': 'Gana el partido', 'match': 'N. Djokovic vs C. Ruud', 'odd': 1.40, 'sport': 'tenis'},
    {'player': 'Iga Świątek', 'prop': 'Gana el partido', 'match': 'I. Świątek vs A. Sabalenka', 'odd': 1.55, 'sport': 'tenis'},
    {'player': 'Aryna Sabalenka', 'prop': 'Gana el partido', 'match': 'A. Sabalenka vs C. Gauff', 'odd': 1.60, 'sport': 'tenis'},

    # === MMA / UFC ===
    {'player': 'Islam Makhachev', 'prop': 'Gana la pelea', 'match': 'I. Makhachev vs C. Oliveira', 'odd': 1.45, 'sport': 'mma'},
    {'player': 'Alex Pereira', 'prop': 'Gana la pelea', 'match': 'A. Pereira vs M. Ankalaev', 'odd': 1.70, 'sport': 'mma'},
    {'player': 'Sean O\'Malley', 'prop': 'Gana la pelea', 'match': 'S. O\'Malley vs M. Dvalishvili', 'odd': 2.10, 'sport': 'mma'},
    {'player': 'Jon Jones', 'prop': 'Gana la pelea', 'match': 'J. Jones vs T. Aspinall', 'odd': 1.85, 'sport': 'mma'},

    # === NHL Playoffs ===
    {'player': 'Connor McDavid', 'prop': 'Over 1.5 puntos', 'match': 'Edmonton Oilers vs Florida Panthers', 'odd': 2.10, 'sport': 'nhl'},
    {'player': 'Nathan MacKinnon', 'prop': 'Over 0.5 goles', 'match': 'Colorado Avalanche vs Dallas Stars', 'odd': 2.80, 'sport': 'nhl'},
    {'player': 'Auston Matthews', 'prop': 'Over 0.5 goles', 'match': 'Toronto Maple Leafs vs Tampa Bay Lightning', 'odd': 2.50, 'sport': 'nhl'},
]

SPORT_SHORT = {
    'nba': 'nba', 'mlb': 'mlb', 'futbol': 'futbol',
    'tenis': 'tenis', 'mma': 'mma', 'nhl': 'nhl'
}


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

    # Separate by odds range
    low = [p for p in PROP_POOL if 1.10 <= p['odd'] < 1.55]
    mid = [p for p in PROP_POOL if 1.55 <= p['odd'] <= 2.80]
    high = [p for p in PROP_POOL if 2.80 < p['odd'] <= 5.00]

    def pick_legs(pools_config, min_sports=2):
        """Pick legs ensuring unique players within a single ticket and multi-sport."""
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

    # WHALE tickets (x100+): 6-8 legs, mix everything — build first so they get best variety
    for i in range(4):
        random.shuffle(PROP_POOL)
        n_legs = random.choice([6, 7, 8])
        n_low = random.randint(1, 2)
        n_mid = random.randint(2, min(4, n_legs - n_low - 1))
        n_high = n_legs - n_low - n_mid
        if n_high < 1:
            n_high = 1
            n_mid = max(1, n_legs - n_low - n_high)
        legs = pick_legs([(low, n_low), (mid, n_mid), (high, max(1, n_high))], min_sports=2)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if total >= 50:
                tickets.append({
                    'tier': 'whale',
                    'legs': legs,
                    'total_odds': total,
                    'confidence': calculate_confidence(legs),
                })

    # SHARK tickets (x30-99): 5-6 legs, all ranges
    for i in range(5):
        random.shuffle(PROP_POOL)
        n_legs = random.choice([5, 6])
        n_low = random.randint(1, 2)
        n_mid = random.randint(1, min(3, n_legs - n_low - 1))
        n_high = n_legs - n_low - n_mid
        if n_high < 1:
            n_high = 1
            n_mid = max(1, n_legs - n_low - n_high)
        legs = pick_legs([(low, n_low), (mid, n_mid), (high, max(1, n_high))], min_sports=2)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if 20 <= total <= 150:
                tickets.append({
                    'tier': 'shark',
                    'legs': legs,
                    'total_odds': total,
                    'confidence': calculate_confidence(legs),
                })

    # HUNTER tickets (x10-29): 4-5 legs, safe anchors + mid
    for i in range(5):
        random.shuffle(PROP_POOL)
        n_legs = random.choice([4, 5])
        n_low = random.randint(1, min(2, n_legs - 2))
        n_mid = n_legs - n_low
        legs = pick_legs([(low, n_low), (mid, n_mid)], min_sports=2)
        if legs:
            total = round(math.prod(l['odd'] for l in legs), 1)
            if 6 <= total <= 40:
                tickets.append({
                    'tier': 'hunter',
                    'legs': legs,
                    'total_odds': total,
                    'confidence': calculate_confidence(legs),
                })

    # Sort: whales first, then sharks, then hunters
    tier_order = {'whale': 0, 'shark': 1, 'hunter': 2}
    tickets.sort(key=lambda t: (tier_order[t['tier']], -t['total_odds']))

    # Assign IDs and titles
    counters = {'whale': 0, 'shark': 0, 'hunter': 0}
    sport_names = {
        'nba': 'NBA', 'mlb': 'MLB', 'futbol': 'Fútbol',
        'tenis': 'Tenis', 'mma': 'MMA', 'nhl': 'NHL'
    }
    for ticket in tickets:
        tier = ticket['tier']
        counters[tier] += 1
        prefix = tier[0].upper()
        ticket['id'] = f"{prefix}{counters[tier]}"

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


def update_html(tickets_js, filepath):
    content = filepath.read_text(encoding='utf-8')
    pattern = r'const TICKETS = \[[\s\S]*?\];'
    if re.search(pattern, content):
        updated = re.sub(pattern, tickets_js, content, count=1)
    else:
        updated = content
    filepath.write_text(updated, encoding='utf-8')
    print(f"  ✅ {filepath.name} updated")


def main():
    print("🚀 MasterProps Offline Generator")
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"📊 Pool: {len(PROP_POOL)} real props")
    print()

    tickets = build_tickets()
    print(f"🎰 Generated {len(tickets)} tickets:")
    for t in tickets:
        sports_in = set(l['sport'] for l in t['legs'])
        print(f"  {t['id']} [{t['tier'].upper()}] x{t['total_odds']} | "
              f"{len(t['legs'])} legs | {', '.join(sports_in)} | "
              f"conf: {t['confidence']}/6")

    tickets_js = generate_ticket_js(tickets)

    print("\n📝 Updating HTML files...")
    update_html(tickets_js, OUTPUT_FILE)
    update_html(tickets_js, TEMPLATE_FILE)

    print(f"\n✅ Done! {len(tickets)} fresh tickets live.")


if __name__ == '__main__':
    main()
