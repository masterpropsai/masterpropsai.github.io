#!/usr/bin/env python3
"""
MasterProps Auto-Resolver
=========================
Two modes:
  1) --pending    → prints JSON of unique matches with pending legs
  2) --resolve    → reads match results from stdin JSON, resolves legs, updates index.html

Convention: in "(X vs) Y" format:
  Y = Local (Team 1 in props)
  X = Visitante (Team 2 in props)
  "1" in props = Y (Local), "2" = X (Visitante)
"""

import re, json, sys, os, shutil
from datetime import datetime, timedelta

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(REPO_DIR, 'index.html')
TEMPLATE_FILE = os.path.join(REPO_DIR, 'template.html')


def read_index():
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def get_existing_keys(content):
    """Get all already-resolved leg keys from LEG_RESULTS."""
    return set(re.findall(r"'([A-Z]+-[A-Z]\d+_\d+)'", content))


def parse_tickets(content):
    """Parse all tickets and their legs from the HTML."""
    ticket_pattern = r"\{ id:'([^']+)',\s*tier:'([^']+)',\s*sport:'([^']+)',\s*title:'([^']*)'.*?legs:\[\s*(.*?)\s*\]\}"
    tickets_raw = re.findall(ticket_pattern, content, re.DOTALL)

    leg_pattern = r"\{player:'([^']*)',\s*prop:'([^']*)',\s*match:'([^']*)',\s*odd:([^,]+).*?date:'([^']*)'.*?\}"

    tickets = []
    for tid, tier, sport, title, legs_str in tickets_raw:
        legs = re.findall(leg_pattern, legs_str)
        for i, (player, prop, match_comp, odd, date) in enumerate(legs):
            tickets.append({
                'key': f"{tid}_{i}",
                'ticket_id': tid,
                'player': player,
                'prop': prop,
                'match': match_comp,
                'odd': float(odd),
                'date': date,
                'sport': sport,
            })
    return tickets


def parse_player(player_str):
    """Parse '(X vs) Y' → (visitor_code, local_name)"""
    m = re.match(r'\((\w+)\s+vs\)\s+(.*)', player_str)
    if m:
        return m.group(1), m.group(2).strip()
    return None, None


def get_pending_matches(content):
    """Get unique matches that have pending (unresolved) legs."""
    existing = get_existing_keys(content)
    tickets = parse_tickets(content)

    matches = {}
    for leg in tickets:
        if leg['key'] in existing:
            continue

        visitor_code, local_name = parse_player(leg['player'])
        if not local_name:
            continue

        # Group by a normalized match identifier
        match_id = f"{visitor_code}_{local_name}".lower().replace(' ', '_')

        if match_id not in matches:
            matches[match_id] = {
                'match_id': match_id,
                'player_example': leg['player'],
                'local_name': local_name,
                'visitor_code': visitor_code,
                'competition': leg['match'],
                'date': leg['date'],
                'sport': leg['sport'],
                'pending_legs': [],
                'props': [],
            }

        matches[match_id]['pending_legs'].append(leg['key'])
        matches[match_id]['props'].append(leg['prop'])

    return list(matches.values())


def resolve_prop(prop, local_goals, visitor_goals, total, ht_local, ht_visitor,
                 goals_1h, goals_2h, goal_sequence):
    """
    Resolve a betting prop. Returns 'won', 'lost', or 'SKIP'.

    goal_sequence: list of 'local' or 'visitor' for each goal in order.
    """
    p = prop.strip()

    # === MATCH RESULT ===
    if p == 'W1':
        return 'won' if local_goals > visitor_goals else 'lost'
    if p == 'W2':
        return 'won' if visitor_goals > local_goals else 'lost'
    if p == 'X':
        return 'won' if local_goals == visitor_goals else 'lost'

    # === DOUBLE CHANCE ===
    if p == '1X':
        return 'won' if local_goals >= visitor_goals else 'lost'
    if p == '2X':
        return 'won' if visitor_goals >= local_goals else 'lost'
    if p == '12':
        return 'won' if local_goals != visitor_goals else 'lost'

    # === HANDICAP ===
    m_h = re.match(r'Hándicap ([12]) \(([+-]?[\d.]+)\)', p)
    if m_h:
        team_num = int(m_h.group(1))
        handicap = float(m_h.group(2))
        if team_num == 1:
            adjusted = local_goals + handicap
            return 'won' if adjusted > visitor_goals else ('lost' if adjusted < visitor_goals else 'won')  # push = won
        else:
            adjusted = visitor_goals + handicap
            return 'won' if adjusted > local_goals else ('lost' if adjusted < local_goals else 'won')  # push = won

    # === TOTAL MÁS/MENOS ===
    m_t = re.match(r'Total Más de \(([\d.]+)\)', p)
    if m_t:
        line = float(m_t.group(1))
        return 'won' if total > line else ('lost' if total < line else 'won')

    m_t = re.match(r'Total Menos de \(([\d.]+)\)', p)
    if m_t:
        line = float(m_t.group(1))
        return 'won' if total < line else ('lost' if total > line else 'won')

    # === TOTAL INDIVIDUAL ===
    m_ti = re.match(r'Total Individual ([12]) Más de \(([\d.]+)\)', p)
    if m_ti:
        team_num = int(m_ti.group(1))
        line = float(m_ti.group(2))
        goals = local_goals if team_num == 1 else visitor_goals
        return 'won' if goals > line else ('lost' if goals < line else 'won')

    m_ti = re.match(r'Total Individual ([12]) Menos de \(([\d.]+)\)', p)
    if m_ti:
        team_num = int(m_ti.group(1))
        line = float(m_ti.group(2))
        goals = local_goals if team_num == 1 else visitor_goals
        return 'won' if goals < line else ('lost' if goals > line else 'won')

    # === AMBOS ANOTAN ===
    if p == 'Ambos anotan - Sí':
        return 'won' if local_goals > 0 and visitor_goals > 0 else 'lost'
    if p == 'Ambos anotan - No':
        return 'won' if local_goals == 0 or visitor_goals == 0 else 'lost'

    # === HT-FT ===
    if p.startswith('HT-FT'):
        ht_ft_code = p.replace('HT-FT ', '')
        ht_res = 'W1' if ht_local > ht_visitor else ('W2' if ht_local < ht_visitor else 'X')
        ft_res = 'W1' if local_goals > visitor_goals else ('W2' if local_goals < visitor_goals else 'X')
        actual = ht_res + ft_res

        ht_ft_map = {
            'W1W1': 'W1W1', 'W2W2': 'W2W2', 'XX': 'XX',
            'XW1': 'XW1', 'XW2': 'XW2', 'W1X': 'W1X',
            'W2X': 'W2X', 'W1W2': 'W1W2', 'W2W1': 'W2W1',
        }
        if ht_ft_code in ht_ft_map:
            return 'won' if actual == ht_ft_map[ht_ft_code] else 'lost'

        # Formats like "1/2X" → HT=any non-draw, FT=draw? Skip these edge cases
        return 'SKIP'

    # === LOCAL/VISITANTE GANA POR DIFERENCIA ===
    m_g = re.match(r'Local Gana por (\d+) - (\d+) goles - (Sí|No)', p)
    if m_g:
        low, high, si = int(m_g.group(1)), int(m_g.group(2)), m_g.group(3)
        diff = local_goals - visitor_goals
        condition = local_goals > visitor_goals and low <= diff <= high
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    m_g = re.match(r'Visitante Gana por (\d+) - (\d+) goles - (Sí|No)', p)
    if m_g:
        low, high, si = int(m_g.group(1)), int(m_g.group(2)), m_g.group(3)
        diff = visitor_goals - local_goals
        condition = visitor_goals > local_goals and low <= diff <= high
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    m_g = re.match(r'Local Gana por \((\d+)\) goles - (Sí|No)', p)
    if m_g:
        n, si = int(m_g.group(1)), m_g.group(2)
        diff = local_goals - visitor_goals
        condition = local_goals > visitor_goals and diff == n
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    m_g = re.match(r'Visitante Gana por \((\d+)\) goles - (Sí|No)', p)
    if m_g:
        n, si = int(m_g.group(1)), m_g.group(2)
        diff = visitor_goals - local_goals
        condition = visitor_goals > local_goals and diff == n
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    # === ALGÚN EQUIPO GANA POR DIFERENCIA ===
    m_g = re.match(r'Algún equipo gana por diferencia de \((\d+)\) Gol\(s\) - (Sí|No)', p)
    if m_g:
        n, si = int(m_g.group(1)), m_g.group(2)
        diff = abs(local_goals - visitor_goals)
        condition = diff == n and local_goals != visitor_goals
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    m_g = re.match(r'Algún equipo gana por diferencia de \((\d+)\) o más goles - (Sí|No)', p)
    if m_g:
        n, si = int(m_g.group(1)), m_g.group(2)
        diff = abs(local_goals - visitor_goals)
        condition = diff >= n
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    # === ALGÚN EQUIPO GANA SIN GOLES EN CONTRA ===
    m_g = re.match(r'Algún equipo gana sin goles en contra - (Sí|No)', p)
    if m_g:
        si = m_g.group(1)
        condition = (local_goals > 0 and visitor_goals == 0) or (visitor_goals > 0 and local_goals == 0)
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    # === COMPOUND: TEAM WINS/DOESN'T LOSE + TOTAL ===
    compound_patterns = [
        (r'Local Gana y Total > \(([\d.]+)\) - (Sí|No)', 'local_win', '>'),
        (r'Local Gana y Total < \(([\d.]+)\) - (Sí|No)', 'local_win', '<'),
        (r'Visitante Gana y Total > \(([\d.]+)\) - (Sí|No)', 'visitor_win', '>'),
        (r'Visitante Gana y Total < \(([\d.]+)\) - (Sí|No)', 'visitor_win', '<'),
        (r'Local No pierde y Total > \(([\d.]+)\) - (Sí|No)', 'local_no_lose', '>'),
        (r'Local No pierde y Total < \(([\d.]+)\) - (Sí|No)', 'local_no_lose', '<'),
        (r'Visitante No pierde y Total > \(([\d.]+)\) - (Sí|No)', 'visitor_no_lose', '>'),
        (r'Visitante No pierde y Total < \(([\d.]+)\) - (Sí|No)', 'visitor_no_lose', '<'),
    ]
    for pat, cond_type, op in compound_patterns:
        m_c = re.match(pat, p)
        if m_c:
            line = float(m_c.group(1))
            si = m_c.group(2)
            if cond_type == 'local_win': team_cond = local_goals > visitor_goals
            elif cond_type == 'visitor_win': team_cond = visitor_goals > local_goals
            elif cond_type == 'local_no_lose': team_cond = local_goals >= visitor_goals
            elif cond_type == 'visitor_no_lose': team_cond = visitor_goals >= local_goals
            total_cond = (total > line) if op == '>' else (total < line)
            condition = team_cond and total_cond
            return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    # === TOTAL PAR/IMPAR ===
    if p == 'Total Par - Sí': return 'won' if total % 2 == 0 else 'lost'
    if p in ('Total Impar - Sí', 'Total Par - No'): return 'won' if total % 2 == 1 else 'lost'
    if p == 'Local Total Impar': return 'won' if local_goals % 2 == 1 else 'lost'
    if p == 'Local Total Par': return 'won' if local_goals % 2 == 0 else 'lost'
    if p == 'Visitante Total Impar': return 'won' if visitor_goals % 2 == 1 else 'lost'
    if p == 'Visitante Total Par': return 'won' if visitor_goals % 2 == 0 else 'lost'

    # === 1st HALF vs 2nd HALF ===
    if p == '1st Half > 2nd Half': return 'won' if goals_1h > goals_2h else 'lost'
    if p == '1st Half < 2nd Half': return 'won' if goals_1h < goals_2h else 'lost'
    if p == '1st Half = 2nd Half': return 'won' if goals_1h == goals_2h else 'lost'

    # === PRIMERO EN (N) GOLES ===
    m_p = re.match(r'Primero en \((\d+)\) goles - (Local|Visitante|Ninguno)', p)
    if m_p:
        n = int(m_p.group(1))
        who = m_p.group(2)
        local_count = 0
        visitor_count = 0
        first_to_n = 'Ninguno'
        for scorer in goal_sequence:
            if scorer == 'local': local_count += 1
            else: visitor_count += 1
            if local_count >= n:
                first_to_n = 'Local'
                break
            if visitor_count >= n:
                first_to_n = 'Visitante'
                break
        return 'won' if first_to_n == who else 'lost'

    # === LOCAL/VISITANTE/NINGUNO ANOTA PRÓXIMO GOL ===
    m_ng = re.match(r'(Local|Visitante|Ninguno) Anota próximo gol \((\d+)\)', p)
    if m_ng:
        who = m_ng.group(1)
        n = int(m_ng.group(2))
        if n > len(goal_sequence):
            return 'won' if who == 'Ninguno' else 'lost'
        scorer = goal_sequence[n - 1]
        if who == 'Ninguno': return 'lost'
        if who == 'Local': return 'won' if scorer == 'local' else 'lost'
        if who == 'Visitante': return 'won' if scorer == 'visitor' else 'lost'

    return 'SKIP'


def resolve_matches(content, match_results):
    """
    Resolve all pending legs for the given match results.

    match_results: list of dicts with:
      - local_name: str (exact name as in player field)
      - local_goals: int
      - visitor_goals: int
      - ht_local: int (halftime goals for local)
      - ht_visitor: int (halftime goals for visitor)
      - goal_scorers: list of 'local'|'visitor' in order

    Returns: dict of {leg_key: 'won'|'lost'}, list of skipped
    """
    existing = get_existing_keys(content)
    tickets = parse_tickets(content)

    # Build lookup: local_name → match_result
    result_map = {}
    for mr in match_results:
        result_map[mr['local_name']] = mr

    results = {}
    skipped = []

    for leg in tickets:
        if leg['key'] in existing:
            continue

        _, local_name = parse_player(leg['player'])
        if not local_name or local_name not in result_map:
            continue

        mr = result_map[local_name]
        local_goals = mr['local_goals']
        visitor_goals = mr['visitor_goals']
        total = local_goals + visitor_goals
        ht_local = mr.get('ht_local', 0)
        ht_visitor = mr.get('ht_visitor', 0)
        goals_1h = ht_local + ht_visitor
        goals_2h = total - goals_1h
        goal_sequence = mr.get('goal_scorers', [])

        result = resolve_prop(
            leg['prop'], local_goals, visitor_goals, total,
            ht_local, ht_visitor, goals_1h, goals_2h, goal_sequence
        )

        if result == 'SKIP':
            skipped.append({
                'key': leg['key'],
                'player': leg['player'],
                'prop': leg['prop'],
                'reason': 'PROP_NOT_HANDLED'
            })
        else:
            results[leg['key']] = {
                'result': result,
                'player': leg['player'],
                'prop': leg['prop'],
            }

    return results, skipped


def inject_results(content, results, batch_label="AUTO-RESOLVE"):
    """Inject resolved results into LEG_RESULTS in index.html."""
    if not results:
        return content

    # Build the new entries
    entries = []
    won = sum(1 for v in results.values() if v['result'] == 'won')
    lost = sum(1 for v in results.values() if v['result'] == 'lost')

    entries.append(f"  // === {batch_label} ({len(results)} legs: {won} won, {lost} lost) ===")

    for key in sorted(results.keys()):
        r = results[key]
        entries.append(f"  '{key}': '{r['result']}',   // {r['player']} | {r['prop']}")

    new_block = '\n'.join(entries)

    # Find the closing }; of LEG_RESULTS and insert before it
    # Pattern: find the last entry before the closing of LEG_RESULTS
    pattern = r"(const LEG_RESULTS = \{.*?)(^\s*\};)"
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)

    if match:
        insert_pos = match.start(2)
        content = content[:insert_pos] + '\n' + new_block + '\n' + content[insert_pos:]

    return content


def main():
    if len(sys.argv) < 2:
        print("Usage: auto_resolve.py --pending | --resolve")
        sys.exit(1)

    content = read_index()

    if sys.argv[1] == '--pending':
        matches = get_pending_matches(content)
        # Output as JSON for Claude to process
        output = {
            'total_pending_legs': sum(len(m['pending_legs']) for m in matches),
            'total_unique_matches': len(matches),
            'matches': []
        }
        for m in matches:
            output['matches'].append({
                'match_id': m['match_id'],
                'player_format': m['player_example'],
                'local_name': m['local_name'],
                'visitor_code': m['visitor_code'],
                'competition': m['competition'],
                'date': m['date'],
                'sport': m['sport'],
                'pending_count': len(m['pending_legs']),
                'leg_keys': m['pending_legs'],
                'props': list(set(m['props'])),
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))

    elif sys.argv[1] == '--resolve':
        # Read match results from stdin
        input_data = json.load(sys.stdin)
        match_results = input_data.get('match_results', [])
        batch_label = input_data.get('batch_label', 'AUTO-RESOLVE')

        results, skipped = resolve_matches_v2(content, match_results)

        if results:
            new_content = inject_results(content, results, batch_label)

            # \u2500\u2500 HISTORIAL: archivar billetes terminados e inyectar \u2500\u2500
            try:
                import history_lib
                history_lib.archive_finished(new_content)
                new_content = history_lib.inject_history(new_content)
            except Exception as e:
                print(f"\u26a0\ufe0f historial: {e}", file=sys.stderr)

            # Write updated index.html
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                f.write(new_content)

            # Copy to template.html
            shutil.copy2(INDEX_FILE, TEMPLATE_FILE)

            won = sum(1 for v in results.values() if v['result'] == 'won')
            lost = sum(1 for v in results.values() if v['result'] == 'lost')

            print(json.dumps({
                'status': 'updated',
                'resolved': len(results),
                'won': won,
                'lost': lost,
                'skipped': len(skipped),
                'skipped_details': skipped,
                'results': {k: v['result'] for k, v in results.items()},
            }, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({
                'status': 'nothing_to_resolve',
                'skipped': len(skipped),
                'skipped_details': skipped,
            }, indent=2, ensure_ascii=False))

    else:
        print(f"Unknown command: {sys.argv[1]}")
        sys.exit(1)





# ============================================================================
# EXTENDED RESOLVER (handles team-name props used by current generate pipeline)
# ============================================================================

import unicodedata

def _strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def _team_side(team_str, local_name, visitor_name):
    """Return 'local', 'visitor', or None depending on which team the prop string refers to."""
    if team_str is None:
        return None
    t = team_str.strip().lower()
    if local_name and t == local_name.strip().lower():
        return 'local'
    if visitor_name and t == visitor_name.strip().lower():
        return 'visitor'
    # Fuzzy: strip accents and compare
    t2 = _strip_accents(t)
    if local_name and t2 == _strip_accents(local_name.strip().lower()):
        return 'local'
    if visitor_name and t2 == _strip_accents(visitor_name.strip().lower()):
        return 'visitor'
    # Try startswith for cases like "TEAM Gana y ..." vs "Gana TEAM"
    return None


def _asian_handicap(team_goals, other_goals, handicap):
    """
    Resolve an Asian handicap. handicap is from the team's perspective (+/- with .0/.25/.5/.75).
    Returns 'won' or 'lost'. Push portions are counted as 'won' (stake returned).
    """
    # Quarter handicaps: split into two half-handicaps
    # e.g. +0.25 = +0 and +0.5; +0.75 = +0.5 and +1.0
    h_frac = round(handicap - int(handicap), 2) if handicap >= 0 else round(handicap - int(handicap), 2)
    # Use a cleaner approach: multiply by 4 to get quarter integer
    q = round(handicap * 4)
    # q % 2 != 0 means quarter handicap (.25 or .75 fraction)
    if q % 2 != 0:
        # Split into two halves: lower = handicap - 0.25, upper = handicap + 0.25
        h1 = handicap - 0.25
        h2 = handicap + 0.25
        r1 = _asian_handicap(team_goals, other_goals, h1)
        r2 = _asian_handicap(team_goals, other_goals, h2)
        if r1 == 'won' and r2 == 'won':
            return 'won'
        if r1 == 'lost' and r2 == 'lost':
            return 'lost'
        # Mixed: treat as won (half-win or half-push)
        return 'won'
    # Integer or .5 handicap
    diff = team_goals + handicap - other_goals
    if diff > 0:
        return 'won'
    if diff < 0:
        return 'lost'
    # diff == 0: push (only possible on integer handicaps)
    return 'won'  # push = stake returned, treat as won


def _asian_total(total, line, op):
    """
    Resolve an Asian total. op is '>' (Más de) or '<' (Menos de).
    line can have .0, .25, .5, .75 fractions.
    Returns 'won' or 'lost'.
    """
    q = round(line * 4)
    if q % 2 != 0:
        # Quarter line: split
        l1 = line - 0.25
        l2 = line + 0.25
        r1 = _asian_total(total, l1, op)
        r2 = _asian_total(total, l2, op)
        if r1 == 'won' and r2 == 'won':
            return 'won'
        if r1 == 'lost' and r2 == 'lost':
            return 'lost'
        return 'won'  # mixed: half-win or half-push
    # Integer or .5 line
    if op == '>':
        if total > line: return 'won'
        if total < line: return 'lost'
        return 'won'  # push
    else:  # '<'
        if total < line: return 'won'
        if total > line: return 'lost'
        return 'won'  # push


def resolve_prop_v2(prop, local_goals, visitor_goals, total, ht_local, ht_visitor,
                    goals_1h, goals_2h, goal_sequence, local_name, visitor_name):
    """
    Extended resolver handling team-name props.
    Falls back to the original resolve_prop for standard formats.
    """
    p = prop.strip()

    # Try the OLD resolver first (handles HT-FT, W1/W2/X, Hándicap, etc.)
    old_result = resolve_prop(p, local_goals, visitor_goals, total, ht_local, ht_visitor,
                              goals_1h, goals_2h, goal_sequence)
    if old_result != 'SKIP':
        return old_result

    # --- TOTAL GOALS WITHOUT TEAM (Asian totals) ---
    m = re.match(r'Más de ([\d.]+) (?:goles|puntos|carreras)$', p)
    if m:
        return _asian_total(total, float(m.group(1)), '>')
    m = re.match(r'Menos de ([\d.]+) (?:goles|puntos|carreras)$', p)
    if m:
        return _asian_total(total, float(m.group(1)), '<')

    # --- TEAM TOTAL GOALS / PUNTOS / CARRERAS (e.g. "Menos de 2 goles de Cruzeiro") ---
    m = re.match(r'(Más|Menos) de ([\d.]+) (?:goles|puntos|carreras) de (.+)$', p)
    if m:
        op_word, line, team = m.group(1), float(m.group(2)), m.group(3)
        side = _team_side(team, local_name, visitor_name)
        if side is None:
            return 'SKIP'
        team_goals = local_goals if side == 'local' else visitor_goals
        op = '>' if op_word == 'Más' else '<'
        return _asian_total(team_goals, line, op)

    # --- GANA TEAM (team wins) ---
    m = re.match(r'Gana (.+)$', p)
    if m:
        team = m.group(1)
        side = _team_side(team, local_name, visitor_name)
        if side is None:
            return 'SKIP'
        if side == 'local':
            return 'won' if local_goals > visitor_goals else 'lost'
        else:
            return 'won' if visitor_goals > local_goals else 'lost'

    # --- HANDICAP WITH TEAM NAME (HÁ TEAM ±X [Sets]) ---
    m = re.match(r'HÁ (.+?) ([+-]?[\d.]+)(?:\s+Sets)?$', p)
    if m:
        team, h = m.group(1).strip(), float(m.group(2))
        side = _team_side(team, local_name, visitor_name)
        if side is None:
            return 'SKIP'
        if side == 'local':
            return _asian_handicap(local_goals, visitor_goals, h)
        else:
            return _asian_handicap(visitor_goals, local_goals, h)

    # --- TEAM GANA Y MÁS/MENOS DE X GOLES/PUNTOS/CARRERAS - SÍ/NO ---
    m = re.match(r'(.+?) Gana y (Más|Menos) de ([\d.]+) (?:goles|puntos|carreras) - (Sí|No)$', p)
    if m:
        team, op_word, line, si = m.group(1).strip(), m.group(2), float(m.group(3)), m.group(4)
        side = _team_side(team, local_name, visitor_name)
        if side is None:
            return 'SKIP'
        team_wins = (local_goals > visitor_goals) if side == 'local' else (visitor_goals > local_goals)
        op = '>' if op_word == 'Más' else '<'
        total_match = _asian_total(total, line, op)
        condition = team_wins and (total_match == 'won')
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    # --- TEAM NO PIERDE Y MÁS/MENOS DE X GOLES/PUNTOS/CARRERAS - SÍ/NO ---
    m = re.match(r'(.+?) No pierde y (Más|Menos) de ([\d.]+) (?:goles|puntos|carreras)(?: - (Sí|No))?$', p)
    if m:
        team, op_word, line, si = m.group(1).strip(), m.group(2), float(m.group(3)), m.group(4) or 'Sí'
        side = _team_side(team, local_name, visitor_name)
        if side is None:
            return 'SKIP'
        team_no_lose = (local_goals >= visitor_goals) if side == 'local' else (visitor_goals >= local_goals)
        op = '>' if op_word == 'Más' else '<'
        total_match = _asian_total(total, line, op)
        condition = team_no_lose and (total_match == 'won')
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    # --- TEAM TOTAL PAR / IMPAR ---
    m = re.match(r'(.+?) Total (Par|Impar)$', p)
    if m:
        team, parity = m.group(1).strip(), m.group(2)
        side = _team_side(team, local_name, visitor_name)
        if side is None:
            return 'SKIP'
        team_goals = local_goals if side == 'local' else visitor_goals
        is_even = team_goals % 2 == 0
        if parity == 'Par':
            return 'won' if is_even else 'lost'
        else:
            return 'won' if not is_even else 'lost'

    # --- TEAM ANOTA PRÓXIMO GOL (N) ---
    m = re.match(r'(.+?) Anota próximo gol \((\d+)\)$', p)
    if m:
        team, n = m.group(1).strip(), int(m.group(2))
        if team == 'Ninguno':
            # "Ninguno" → goal N didn't happen
            return 'won' if n > len(goal_sequence) else 'lost'
        side = _team_side(team, local_name, visitor_name)
        if side is None:
            return 'SKIP'
        if not goal_sequence:
            return 'SKIP'
        if n > len(goal_sequence):
            return 'lost'  # team's goal N never happened
        scorer = goal_sequence[n - 1]
        return 'won' if scorer == side else 'lost'

    # --- TEAM GANA POR X - Y GOLES - SÍ/NO ---
    m = re.match(r'(.+?) Gana por (\d+) - (\d+) goles - (Sí|No)$', p)
    if m:
        team, low, high, si = m.group(1).strip(), int(m.group(2)), int(m.group(3)), m.group(4)
        side = _team_side(team, local_name, visitor_name)
        if side is None:
            return 'SKIP'
        if side == 'local':
            diff = local_goals - visitor_goals
            condition = local_goals > visitor_goals and low <= diff <= high
        else:
            diff = visitor_goals - local_goals
            condition = visitor_goals > local_goals and low <= diff <= high
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    # --- TEAM GANA POR (N) GOLES - SÍ/NO ---
    m = re.match(r'(.+?) Gana por \((\d+)\) goles - (Sí|No)$', p)
    if m:
        team, n, si = m.group(1).strip(), int(m.group(2)), m.group(3)
        side = _team_side(team, local_name, visitor_name)
        if side is None:
            return 'SKIP'
        if side == 'local':
            diff = local_goals - visitor_goals
            condition = local_goals > visitor_goals and diff == n
        else:
            diff = visitor_goals - local_goals
            condition = visitor_goals > local_goals and diff == n
        return 'won' if (condition and si == 'Sí') or (not condition and si == 'No') else 'lost'

    return 'SKIP'


def resolve_matches_v2(content, match_results):
    """Like resolve_matches but uses resolve_prop_v2 and accepts visitor_name."""
    existing = get_existing_keys(content)
    tickets = parse_tickets(content)

    result_map = {}
    for mr in match_results:
        result_map[mr['local_name']] = mr

    results = {}
    skipped = []

    for leg in tickets:
        if leg['key'] in existing:
            continue
        _, local_name = parse_player(leg['player'])
        if not local_name or local_name not in result_map:
            continue
        mr = result_map[local_name]
        local_goals = mr['local_goals']
        visitor_goals = mr['visitor_goals']
        total = local_goals + visitor_goals
        ht_local = mr.get('ht_local', 0)
        ht_visitor = mr.get('ht_visitor', 0)
        goals_1h = ht_local + ht_visitor
        goals_2h = total - goals_1h
        goal_sequence = mr.get('goal_scorers', [])
        visitor_name = mr.get('visitor_name', '')

        result = resolve_prop_v2(
            leg['prop'], local_goals, visitor_goals, total,
            ht_local, ht_visitor, goals_1h, goals_2h, goal_sequence,
            local_name, visitor_name
        )

        if result == 'SKIP':
            skipped.append({
                'key': leg['key'],
                'player': leg['player'],
                'prop': leg['prop'],
                'reason': 'PROP_NOT_HANDLED'
            })
        else:
            results[leg['key']] = {
                'result': result,
                'player': leg['player'],
                'prop': leg['prop'],
            }
    return results, skipped


if __name__ == '__main__':
    main()
