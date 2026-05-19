#!/usr/bin/env python3
"""
MasterProps.ai — Offline Ticket Generator v3
REAL matchups, ZERO duplicate selections across tickets, team badges.
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
# 'result': 'won'/'lost' = already resolved, absent = pending
# 'team': team abbreviation for badge display
# ============================================================
PROP_POOL = [
    # ── NBA CONFERENCE FINALS (May 19+) ──
    # Thunder vs Spurs — Game 1: May 19
    {'player': 'Shai Gilgeous-Alexander', 'prop': 'Over 30.5 puntos', 'match': 'Oklahoma City Thunder vs San Antonio Spurs', 'odd': 1.82, 'sport': 'nba', 'team': 'OKC', 'date': 'May 19'},
    {'player': 'Shai Gilgeous-Alexander', 'prop': 'Over 5.5 asistencias', 'match': 'Oklahoma City Thunder vs San Antonio Spurs', 'odd': 2.10, 'sport': 'nba', 'team': 'OKC', 'date': 'May 19'},
    {'player': 'Victor Wembanyama', 'prop': 'Over 3.5 tapones', 'match': 'San Antonio Spurs vs Oklahoma City Thunder', 'odd': 2.45, 'sport': 'nba', 'team': 'SAS', 'date': 'May 19'},
    {'player': 'Victor Wembanyama', 'prop': 'Over 22.5 puntos', 'match': 'San Antonio Spurs vs Oklahoma City Thunder', 'odd': 1.90, 'sport': 'nba', 'team': 'SAS', 'date': 'May 19'},
    {'player': 'Chet Holmgren', 'prop': 'Over 2.5 tapones', 'match': 'Oklahoma City Thunder vs San Antonio Spurs', 'odd': 2.30, 'sport': 'nba', 'team': 'OKC', 'date': 'May 19'},
    {'player': 'Jalen Williams', 'prop': 'Over 20.5 puntos', 'match': 'Oklahoma City Thunder vs San Antonio Spurs', 'odd': 1.90, 'sport': 'nba', 'team': 'OKC', 'date': 'May 19'},
    {'player': 'Jalen Williams', 'prop': 'Over 5.5 rebotes', 'match': 'Oklahoma City Thunder vs San Antonio Spurs', 'odd': 2.25, 'sport': 'nba', 'team': 'OKC', 'date': 'May 19'},
    {'player': 'Chris Paul', 'prop': 'Over 8.5 asistencias', 'match': 'San Antonio Spurs vs Oklahoma City Thunder', 'odd': 2.15, 'sport': 'nba', 'team': 'SAS', 'date': 'May 19'},
    {'player': 'Keldon Johnson', 'prop': 'Over 16.5 puntos', 'match': 'San Antonio Spurs vs Oklahoma City Thunder', 'odd': 2.05, 'sport': 'nba', 'team': 'SAS', 'date': 'May 19'},
    {'player': 'Devin Vassell', 'prop': 'Over 14.5 puntos', 'match': 'San Antonio Spurs vs Oklahoma City Thunder', 'odd': 2.10, 'sport': 'nba', 'team': 'SAS', 'date': 'May 19'},
    {'player': 'Lu Dort', 'prop': 'Over 10.5 puntos', 'match': 'Oklahoma City Thunder vs San Antonio Spurs', 'odd': 2.00, 'sport': 'nba', 'team': 'OKC', 'date': 'May 19'},
    # Knicks vs Cavaliers — Game 1: May 20
    {'player': 'Jalen Brunson', 'prop': 'Over 26.5 puntos', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 1.78, 'sport': 'nba', 'team': 'NYK', 'date': 'May 20'},
    {'player': 'Jalen Brunson', 'prop': 'Over 6.5 asistencias', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 2.20, 'sport': 'nba', 'team': 'NYK', 'date': 'May 20'},
    {'player': 'Donovan Mitchell', 'prop': 'Over 27.5 puntos', 'match': 'Cleveland Cavaliers vs New York Knicks', 'odd': 1.85, 'sport': 'nba', 'team': 'CLE', 'date': 'May 20'},
    {'player': 'James Harden', 'prop': 'Over 8.5 asistencias', 'match': 'Cleveland Cavaliers vs New York Knicks', 'odd': 2.10, 'sport': 'nba', 'team': 'CLE', 'date': 'May 20'},
    {'player': 'James Harden', 'prop': 'Over 18.5 puntos', 'match': 'Cleveland Cavaliers vs New York Knicks', 'odd': 1.95, 'sport': 'nba', 'team': 'CLE', 'date': 'May 20'},
    {'player': 'Karl-Anthony Towns', 'prop': 'Over 10.5 rebotes', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 1.95, 'sport': 'nba', 'team': 'NYK', 'date': 'May 20'},
    {'player': 'Karl-Anthony Towns', 'prop': 'Over 22.5 puntos', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 2.05, 'sport': 'nba', 'team': 'NYK', 'date': 'May 20'},
    {'player': 'Evan Mobley', 'prop': 'Over 8.5 rebotes', 'match': 'Cleveland Cavaliers vs New York Knicks', 'odd': 1.88, 'sport': 'nba', 'team': 'CLE', 'date': 'May 20'},
    {'player': 'OG Anunoby', 'prop': 'Over 14.5 puntos', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 2.00, 'sport': 'nba', 'team': 'NYK', 'date': 'May 20'},
    {'player': 'Darius Garland', 'prop': 'Over 18.5 puntos', 'match': 'Cleveland Cavaliers vs New York Knicks', 'odd': 2.20, 'sport': 'nba', 'team': 'CLE', 'date': 'May 20'},
    {'player': 'Mikal Bridges', 'prop': 'Over 15.5 puntos', 'match': 'New York Knicks vs Cleveland Cavaliers', 'odd': 1.92, 'sport': 'nba', 'team': 'NYK', 'date': 'May 20'},

    # ── CHAMPIONS LEAGUE — ALREADY PLAYED ──
    {'player': 'Harry Kane', 'prop': 'Marca gol en cualquier momento', 'match': 'Bayern Munich vs Real Madrid — QF', 'odd': 1.80, 'sport': 'futbol', 'result': 'won', 'team': 'BAY', 'date': 'Abr 15'},
    {'player': 'Kylian Mbappé', 'prop': 'Marca gol en cualquier momento', 'match': 'Real Madrid vs Bayern Munich — QF', 'odd': 1.90, 'sport': 'futbol', 'result': 'won', 'team': 'RMA', 'date': 'Abr 7'},
    {'player': 'Vinícius Jr.', 'prop': 'Marca gol en cualquier momento', 'match': 'Real Madrid vs Bayern Munich — QF', 'odd': 2.20, 'sport': 'futbol', 'result': 'lost', 'team': 'RMA', 'date': 'Abr 7'},
    {'player': 'Bukayo Saka', 'prop': 'Marca gol vs Atlético', 'match': 'Arsenal vs Atlético Madrid — SF', 'odd': 2.80, 'sport': 'futbol', 'result': 'won', 'team': 'ARS', 'date': 'May 5'},
    {'player': 'Antoine Griezmann', 'prop': 'Marca gol vs Arsenal', 'match': 'Atlético Madrid vs Arsenal — SF', 'odd': 3.10, 'sport': 'futbol', 'result': 'lost', 'team': 'ATM', 'date': 'May 5'},
    {'player': 'Julian Álvarez', 'prop': 'Marca gol vs Arsenal', 'match': 'Atlético Madrid vs Arsenal — SF', 'odd': 2.60, 'sport': 'futbol', 'result': 'lost', 'team': 'ATM', 'date': 'May 5'},
    {'player': 'Ousmane Dembélé', 'prop': 'Marca gol vs Bayern', 'match': 'PSG vs Bayern Munich — SF', 'odd': 2.50, 'sport': 'futbol', 'result': 'won', 'team': 'PSG', 'date': 'May 6'},

    # ── CHAMPIONS LEAGUE FINAL (May 30) ──
    {'player': 'Bukayo Saka', 'prop': 'Marca gol en la Final', 'match': 'Arsenal vs PSG — Final UCL', 'odd': 2.90, 'sport': 'futbol', 'team': 'ARS', 'date': 'May 30'},
    {'player': 'Ousmane Dembélé', 'prop': 'Marca gol en la Final', 'match': 'PSG vs Arsenal — Final UCL', 'odd': 2.75, 'sport': 'futbol', 'team': 'PSG', 'date': 'May 30'},
    {'player': 'Kai Havertz', 'prop': 'Marca gol en la Final', 'match': 'Arsenal vs PSG — Final UCL', 'odd': 3.30, 'sport': 'futbol', 'team': 'ARS', 'date': 'May 30'},
    {'player': 'Bradley Barcola', 'prop': 'Marca gol en la Final', 'match': 'PSG vs Arsenal — Final UCL', 'odd': 3.00, 'sport': 'futbol', 'team': 'PSG', 'date': 'May 30'},
    {'player': 'Martin Ødegaard', 'prop': 'Marca gol en la Final', 'match': 'Arsenal vs PSG — Final UCL', 'odd': 3.50, 'sport': 'futbol', 'team': 'ARS', 'date': 'May 30'},
    {'player': 'Marco Asensio', 'prop': 'Marca gol en la Final', 'match': 'PSG vs Arsenal — Final UCL', 'odd': 3.80, 'sport': 'futbol', 'team': 'PSG', 'date': 'May 30'},
    {'player': 'Gabriel Jesus', 'prop': 'Marca gol en la Final', 'match': 'Arsenal vs PSG — Final UCL', 'odd': 3.20, 'sport': 'futbol', 'team': 'ARS', 'date': 'May 30'},
    {'player': 'Leandro Trossard', 'prop': 'Marca gol en la Final', 'match': 'Arsenal vs PSG — Final UCL', 'odd': 3.60, 'sport': 'futbol', 'team': 'ARS', 'date': 'May 30'},
    {'player': 'Gonçalo Ramos', 'prop': 'Marca gol en la Final', 'match': 'PSG vs Arsenal — Final UCL', 'odd': 2.80, 'sport': 'futbol', 'team': 'PSG', 'date': 'May 30'},

    # ── LIGA ARGENTINA — ALREADY PLAYED ──
    {'player': 'Adam Bareiro', 'prop': 'Marca gol en cualquier momento', 'match': 'River Plate 0-1 Boca Juniors', 'odd': 3.50, 'sport': 'futbol', 'result': 'lost', 'team': 'RIV', 'date': 'Abr 19'},
    {'player': 'Maxi Salas', 'prop': 'Marca gol en cualquier momento', 'match': 'River Plate 0-1 Boca Juniors', 'odd': 3.20, 'sport': 'futbol', 'result': 'lost', 'team': 'RIV', 'date': 'Abr 19'},

    # ── MLB (May 18-19 real schedule) ──
    {'player': 'Shohei Ohtani', 'prop': 'Over 1.5 bases totales', 'match': 'Dodgers vs Padres', 'odd': 1.65, 'sport': 'mlb', 'team': 'LAD', 'date': 'May 18'},
    {'player': 'Mookie Betts', 'prop': 'Over 1.5 hits', 'match': 'Dodgers vs Padres', 'odd': 2.40, 'sport': 'mlb', 'team': 'LAD', 'date': 'May 18'},
    {'player': 'Freddie Freeman', 'prop': 'Over 0.5 hits', 'match': 'Dodgers vs Padres', 'odd': 1.25, 'sport': 'mlb', 'team': 'LAD', 'date': 'May 18'},
    {'player': 'Aaron Judge', 'prop': 'Home Run: Sí', 'match': 'Blue Jays vs Yankees', 'odd': 3.50, 'sport': 'mlb', 'team': 'NYY', 'date': 'May 18'},
    {'player': 'Juan Soto', 'prop': 'Over 1.5 bases totales', 'match': 'Mets vs Nationals', 'odd': 1.78, 'sport': 'mlb', 'team': 'NYM', 'date': 'May 18'},
    {'player': 'Bryce Harper', 'prop': 'Over 1.5 hits', 'match': 'Reds vs Phillies', 'odd': 2.25, 'sport': 'mlb', 'team': 'PHI', 'date': 'May 18'},
    {'player': 'Ronald Acuña Jr.', 'prop': 'Over 1.5 bases totales', 'match': 'Braves vs Marlins', 'odd': 1.70, 'sport': 'mlb', 'team': 'ATL', 'date': 'May 18'},
    {'player': 'Yordan Alvarez', 'prop': 'Over 1.5 bases totales', 'match': 'Astros vs Twins', 'odd': 1.82, 'sport': 'mlb', 'team': 'HOU', 'date': 'May 18'},
    {'player': 'Bobby Witt Jr.', 'prop': 'Over 1.5 hits', 'match': 'Red Sox vs Royals', 'odd': 2.15, 'sport': 'mlb', 'team': 'KC', 'date': 'May 18'},
    {'player': 'Gerrit Cole', 'prop': 'Over 6.5 strikeouts', 'match': 'Blue Jays vs Yankees', 'odd': 1.85, 'sport': 'mlb', 'team': 'NYY', 'date': 'May 19'},
    {'player': 'Corbin Burnes', 'prop': 'Over 5.5 strikeouts', 'match': 'Giants vs Diamondbacks', 'odd': 1.72, 'sport': 'mlb', 'team': 'ARI', 'date': 'May 19'},
    {'player': 'Corey Seager', 'prop': 'Over 1.5 bases totales', 'match': 'Rangers vs Rockies', 'odd': 1.80, 'sport': 'mlb', 'team': 'TEX', 'date': 'May 19'},
    {'player': 'Rafael Devers', 'prop': 'Over 1.5 bases totales', 'match': 'Red Sox vs Royals', 'odd': 1.75, 'sport': 'mlb', 'team': 'BOS', 'date': 'May 19'},
    {'player': 'Manny Machado', 'prop': 'Over 0.5 hits', 'match': 'Dodgers vs Padres', 'odd': 1.30, 'sport': 'mlb', 'team': 'SD', 'date': 'May 19'},
    {'player': 'Trea Turner', 'prop': 'Over 0.5 hits', 'match': 'Reds vs Phillies', 'odd': 1.28, 'sport': 'mlb', 'team': 'PHI', 'date': 'May 19'},
    {'player': 'Pete Alonso', 'prop': 'Home Run: Sí', 'match': 'Mets vs Nationals', 'odd': 3.80, 'sport': 'mlb', 'team': 'NYM', 'date': 'May 19'},
    {'player': 'Marcus Semien', 'prop': 'Over 1.5 bases totales', 'match': 'Rangers vs Rockies', 'odd': 1.85, 'sport': 'mlb', 'team': 'TEX', 'date': 'May 19'},
    {'player': 'Kyle Tucker', 'prop': 'Over 1.5 hits', 'match': 'Astros vs Twins', 'odd': 2.30, 'sport': 'mlb', 'team': 'HOU', 'date': 'May 19'},

    # ── ROLAND GARROS (starts May 25) ──
    {'player': 'Jannik Sinner', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros — 1ra Ronda', 'odd': 1.08, 'sport': 'tenis', 'team': 'ATP', 'date': 'May 25'},
    {'player': 'Carlos Alcaraz', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros — 1ra Ronda', 'odd': 1.12, 'sport': 'tenis', 'team': 'ATP', 'date': 'May 25'},
    {'player': 'Alexander Zverev', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros — 1ra Ronda', 'odd': 1.10, 'sport': 'tenis', 'team': 'ATP', 'date': 'May 26'},
    {'player': 'Novak Djokovic', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros — 1ra Ronda', 'odd': 1.15, 'sport': 'tenis', 'team': 'ATP', 'date': 'May 26'},
    {'player': 'Iga Świątek', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros — 1ra Ronda', 'odd': 1.05, 'sport': 'tenis', 'team': 'WTA', 'date': 'May 25'},
    {'player': 'Aryna Sabalenka', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros — 1ra Ronda', 'odd': 1.08, 'sport': 'tenis', 'team': 'WTA', 'date': 'May 26'},
    {'player': 'Coco Gauff', 'prop': 'Gana su 1er partido', 'match': 'Roland Garros — 1ra Ronda', 'odd': 1.10, 'sport': 'tenis', 'team': 'WTA', 'date': 'May 25'},

    # ── NHL CONFERENCE FINALS (May 20+) ──
    {'player': 'Nathan MacKinnon', 'prop': 'Over 1.5 puntos', 'match': 'Avalanche vs Golden Knights', 'odd': 1.85, 'sport': 'nhl', 'team': 'COL', 'date': 'May 20'},
    {'player': 'Cale Makar', 'prop': 'Over 0.5 goles', 'match': 'Avalanche vs Golden Knights', 'odd': 2.80, 'sport': 'nhl', 'team': 'COL', 'date': 'May 20'},
    {'player': 'Jack Eichel', 'prop': 'Over 0.5 goles', 'match': 'Golden Knights vs Avalanche', 'odd': 2.60, 'sport': 'nhl', 'team': 'VGK', 'date': 'May 20'},
    {'player': 'Mikko Rantanen', 'prop': 'Over 0.5 goles', 'match': 'Avalanche vs Golden Knights', 'odd': 2.30, 'sport': 'nhl', 'team': 'COL', 'date': 'May 22'},
    {'player': 'Mark Stone', 'prop': 'Over 0.5 puntos', 'match': 'Golden Knights vs Avalanche', 'odd': 1.70, 'sport': 'nhl', 'team': 'VGK', 'date': 'May 22'},

    # ── UFC FREEDOM 250 (June 14) ──
    {'player': 'Alex Pereira', 'prop': 'Gana la pelea', 'match': 'Pereira vs Gane — UFC Freedom 250', 'odd': 1.70, 'sport': 'mma', 'team': 'UFC', 'date': 'Jun 14'},
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


def prop_key(p):
    """Unique key for a selection = player + prop text."""
    return f"{p['player']}|{p['prop']}"


def build_tickets():
    tickets = []
    used_keys = set()  # GLOBAL tracker — no selection appears in more than one ticket

    resolved_won = [p for p in PROP_POOL if p.get('result') == 'won']
    resolved_lost = [p for p in PROP_POOL if p.get('result') == 'lost']
    pending = [p for p in PROP_POOL if 'result' not in p]

    low = [p for p in pending if 1.01 <= p['odd'] < 1.55]
    mid = [p for p in pending if 1.55 <= p['odd'] <= 2.80]
    high = [p for p in pending if 2.80 < p['odd'] <= 5.00]

    def pick_legs(pools_config, min_sports=2):
        selected = []
        sports_used = set()
        players_in_ticket = set()
        for pool, count in pools_config:
            available = [p for p in pool
                         if prop_key(p) not in used_keys
                         and p['player'] not in players_in_ticket]
            random.shuffle(available)
            picked = 0
            for p in available:
                if picked >= count:
                    break
                selected.append(p)
                sports_used.add(p['sport'])
                players_in_ticket.add(p['player'])
                picked += 1
        total_needed = sum(c for _, c in pools_config)
        if len(selected) >= total_needed and len(sports_used) >= min_sports:
            # Mark used GLOBALLY
            for s in selected:
                used_keys.add(prop_key(s))
            return selected
        return None

    def pick_resolved(pool, count):
        available = [p for p in pool if prop_key(p) not in used_keys]
        random.shuffle(available)
        picked = []
        for p in available:
            if len(picked) >= count:
                break
            picked.append(p)
            used_keys.add(prop_key(p))
        return picked

    # === WHALE TICKETS: long tickets with resolved anchors ===
    for i in range(3):
        random.shuffle(pending)
        anchors = pick_resolved(resolved_won, 2)
        if len(anchors) < 1:
            anchors = []
        n_pending = random.choice([5, 6])
        n_low = random.randint(1, min(2, n_pending))
        n_mid = random.randint(1, min(3, n_pending - n_low))
        n_high = max(1, n_pending - n_low - n_mid)
        pending_legs = pick_legs([(low, n_low), (mid, n_mid), (high, n_high)], min_sports=1)
        if pending_legs:
            legs = anchors + pending_legs
            sports = set(l['sport'] for l in legs)
            if len(sports) >= 2:
                total = round(math.prod(l['odd'] for l in legs), 1)
                if total >= 40:
                    tickets.append({
                        'tier': 'whale', 'legs': legs,
                        'total_odds': total, 'confidence': calculate_confidence(legs),
                    })

    # === SHARK TICKETS ===
    for i in range(4):
        random.shuffle(pending)
        anchors = pick_resolved(resolved_won, 1)
        n_pending = random.choice([4, 5])
        n_low = random.randint(0, min(1, n_pending))
        n_mid = random.randint(1, min(3, n_pending - max(n_low, 1)))
        n_high = max(0, n_pending - n_low - n_mid)
        pools = []
        if n_low > 0: pools.append((low, n_low))
        if n_mid > 0: pools.append((mid, n_mid))
        if n_high > 0: pools.append((high, n_high))
        if not pools:
            pools = [(mid, 3)]
        pending_legs = pick_legs(pools, min_sports=1)
        if pending_legs:
            legs = anchors + pending_legs
            sports = set(l['sport'] for l in legs)
            if len(sports) >= 2:
                total = round(math.prod(l['odd'] for l in legs), 1)
                if 15 <= total <= 150:
                    tickets.append({
                        'tier': 'shark', 'legs': legs,
                        'total_odds': total, 'confidence': calculate_confidence(legs),
                    })

    # === HUNTER TICKETS ===
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
                    'tier': 'hunter', 'legs': legs,
                    'total_odds': total, 'confidence': calculate_confidence(legs),
                })

    # === BONUS: one dead ticket (with lost leg) ===
    random.shuffle(pending)
    dead_anchor = pick_resolved(resolved_lost, 1)
    dead_pending = pick_legs([(mid, 3)], min_sports=1)
    if dead_pending and dead_anchor:
        legs = dead_anchor + dead_pending
        sports = set(l['sport'] for l in legs)
        if len(sports) >= 2:
            total = round(math.prod(l['odd'] for l in legs), 1)
            tickets.append({
                'tier': 'shark', 'legs': legs,
                'total_odds': total, 'confidence': calculate_confidence(legs),
            })

    # Sort
    # Promote whale tickets with x1000+ to megalodon
    for t in tickets:
        if t['tier'] == 'whale' and t['total_odds'] >= 1000:
            t['tier'] = 'megalodon'
    tier_order = {'megalodon': 0, 'whale': 1, 'shark': 2, 'hunter': 3}
    tickets.sort(key=lambda t: (tier_order[t['tier']], -t['total_odds']))

    # Assign IDs
    sport_names = {
        'nba': 'NBA', 'mlb': 'MLB', 'futbol': 'Fútbol',
        'tenis': 'Tenis', 'mma': 'MMA', 'nhl': 'NHL'
    }
    counters = {'megalodon': 0, 'whale': 0, 'shark': 0, 'hunter': 0}
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

    # Verify zero duplicates
    all_keys = []
    for t in tickets:
        for l in t['legs']:
            all_keys.append(prop_key(l))
    assert len(all_keys) == len(set(all_keys)), f"DUPLICATE FOUND! {len(all_keys)} vs {len(set(all_keys))}"

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
                f"team:'{_esc(leg['team'])}', date:'{leg.get('date', '')}'}}"
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
    pattern = r'const TICKETS = \[[\s\S]*?\];'
    if re.search(pattern, content):
        content = re.sub(pattern, tickets_js, content, count=1)
    pattern2 = r'const LEG_RESULTS = \{[^}]*\};'
    if re.search(pattern2, content):
        content = re.sub(pattern2, results_js, content, count=1)
    filepath.write_text(content, encoding='utf-8')
    print(f"  ✅ {filepath.name} updated")


def main():
    print("🚀 MasterProps Offline Generator v3 — ZERO DUPLICATES")
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
        heat = f"🔥{won}✅" if won > 0 else ""
        dead = f"💀{lost}❌" if lost > 0 else ""
        print(f"  {t['id']} [{t['tier'].upper()}] x{t['total_odds']} | "
              f"{len(t['legs'])} legs | {', '.join(sports_in)} | "
              f"conf: {t['confidence']}/6 {heat} {dead}")

    # Verify
    all_sels = []
    for t in tickets:
        for l in t['legs']:
            all_sels.append(f"{l['player']}|{l['prop']}")
    print(f"\n🔍 Selecciones totales: {len(all_sels)}, únicas: {len(set(all_sels))}")
    if len(all_sels) != len(set(all_sels)):
        print("❌ ERROR: HAY DUPLICADOS!")
        return
    print("✅ CERO duplicados confirmado")

    tickets_js = generate_ticket_js(tickets)
    results_js = generate_results_js(tickets)

    print(f"\n📝 LEG_RESULTS: {results_js[:80]}...")
    print("\n📝 Updating HTML files...")
    update_html(tickets_js, results_js, OUTPUT_FILE)
    update_html(tickets_js, results_js, TEMPLATE_FILE)

    print(f"\n✅ Done! {len(tickets)} tickets, zero duplicates, team badges ready.")


if __name__ == '__main__':
    main()
