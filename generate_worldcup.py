#!/usr/bin/env python3
"""
MasterProps.ai — World Cup 2026 Ticket Generator
Builds dedicated World Cup tickets organized by matchday.
Imports core logic from generate_live.py.
"""

import random
import math
import re
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from generate_live import (
    get_token, fetch_events, build_prop_pool, generate_ticket_js,
    generate_results_js, update_html, calculate_confidence,
    prop_key, abbrev, translate, translate_name, short_name,
    translate_match, fit_match_lambdas, model_probability,
    SPORT_MAP, SPORT_NAMES, TEAM_ABBREVS, TEAM_NAME_ES,
    INTERESTING_KEYWORDS, GENERIC_MARKET_TYPES, TEAM_WINNER_MARKETS,
    TRANSLATIONS, LOGO_BASE,
    HAS_INTEL, _esc,
)

BASE_DIR = Path(__file__).parent
TEMPLATE_FILE = BASE_DIR / 'template.html'
OUTPUT_FILE = BASE_DIR / 'index.html'
COUPONS_FILE = BASE_DIR / 'coupons.json'
AR_OFFSET = timedelta(hours=-3)


def wc_build_prop_pool(data, start_ts_min, start_ts_max, day_label, intel=None):
    """Build prop pool from ONLY World Cup 2026 events."""
    props = []
    for event in data.get('items', []):
        tournament = event.get('tournamentNameLocalization', '')
        if tournament != 'World Cup 2026':
            continue
        start_ts = event.get('startDate', 0)
        if start_ts and (start_ts > start_ts_max or start_ts < start_ts_min):
            continue
        sport_id = event.get('sportId', 0)
        if sport_id != 1:
            continue

        t1 = event.get('opponent1NameLocalization', 'Team A')
        t2 = event.get('opponent2NameLocalization', 'Team B')
        link = event.get('link', '')
        lambdas = fit_match_lambdas(event)
        date_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime('%b %d · %H:%M') if start_ts else 'TBD'
        ab1, ab2 = abbrev(t1), abbrev(t2)
        img1_list = event.get('imageOpponent1', [])
        img2_list = event.get('imageOpponent2', [])
        logo1 = f"{LOGO_BASE}{img1_list[0]}" if img1_list else ''
        logo2 = f"{LOGO_BASE}{img2_list[0]}" if img2_list else ''

        for odd in event.get('oddsLocalization', []):
            if odd.get('isBlocked', False):
                continue
            odds_val = odd.get('oddsMarket', 0)
            if odds_val < 1.20:
                continue
            display = odd.get('display', '')
            if not any(kw.lower() in display.lower() for kw in INTERESTING_KEYWORDS):
                continue

            otype = odd.get('type', 0)
            if otype in GENERIC_MARKET_TYPES:
                player, rival, team, logo = None, None, '', ''
                is_generic = True
            else:
                display_core = re.sub(r'\([^)]*\)', '', display)
                if '1' in display_core and '2' not in display_core:
                    player, rival, team, logo = t1, t2, ab1, logo1
                elif '2' in display_core and '1' not in display_core:
                    player, rival, team, logo = t2, t1, ab2, logo2
                else:
                    player, rival, team, logo = t1, t2, ab1, logo1
                is_generic = False

            if is_generic:
                player_display = f"{short_name(t1)} vs {short_name(t2)}"
            else:
                player_display = f"({abbrev(short_name(rival))} vs) {short_name(player)}"

            # UNIQUE match identifier per actual match
            match_display = f"Mundial · {short_name(t1)} vs {short_name(t2)}"

            is_winner_pick = (not is_generic) and any(wm in display for wm in TEAM_WINNER_MARKETS)
            side = 'home' if (not is_generic and player == t1) else 'away'

            n1, n2 = short_name(t1), short_name(t2)
            translated_prop = translate(display)
            p = translated_prop
            p = p.replace('Hándicap 1 ', f'Hándicap {n1} ')
            p = p.replace('Hándicap 2 ', f'Hándicap {n2} ')
            p = p.replace('Total Individual 1 ', f'Total {n1} ')
            p = p.replace('Total Individual 2 ', f'Total {n2} ')
            p = p.replace('Local ', f'{n1} ').replace('Visitante ', f'{n2} ')
            p = p.replace(' - Local', f' - {n1}').replace(' - Visitante', f' - {n2}')
            p = re.sub(r'^W1$', f'Gana {n1}', p)
            p = re.sub(r'^W2$', f'Gana {n2}', p)
            p = re.sub(r'^1X$', f'Gana {n1} o Empate', p)
            p = re.sub(r'^X2$', f'Empate o Gana {n2}', p)
            p = re.sub(r'^12$', f'{n1} o {n2}', p)
            p = re.sub(r'Total (' + re.escape(n1) + r'|' + re.escape(n2) + r') Más de \((-?\d+(?:\.\d+)?)\)',
                       lambda m: f'Más de {m.group(2)} goles de {m.group(1)}', p)
            p = re.sub(r'Total (' + re.escape(n1) + r'|' + re.escape(n2) + r') Menos de \((-?\d+(?:\.\d+)?)\)',
                       lambda m: f'Menos de {m.group(2)} goles de {m.group(1)}', p)
            p = re.sub(r'Total Más de \((-?\d+(?:\.\d+)?)\)', lambda m: f'Más de {m.group(1)} goles', p)
            p = re.sub(r'Total Menos de \((-?\d+(?:\.\d+)?)\)', lambda m: f'Menos de {m.group(1)} goles', p)
            p = re.sub(r'Total > \((-?\d+(?:\.\d+)?)\)', lambda m: f'Más de {m.group(1)} goles', p)
            p = re.sub(r'Total < \((-?\d+(?:\.\d+)?)\)', lambda m: f'Menos de {m.group(1)} goles', p)
            def _fmt_hcp(m):
                nm, val, sets = m.group(1), m.group(2), m.group(3) or ''
                pfx = '+' if not val.startswith('-') and val not in ('0', '0.0') else ''
                return f'HÁ {nm} {pfx}{val}{sets}'
            p = re.sub(r'Hándicap (.+?) \((-?\d+(?:\.\d+)?)\)( Sets)?', _fmt_hcp, p)
            p = re.sub(r'\s+', ' ', p).strip()

            edge_val = model_p = sharp_edge = None
            if HAS_INTEL and intel:
                from market_intelligence import odds_api_market_from_dbbet
                mapping = odds_api_market_from_dbbet(odd.get('type', 0), odd.get('parameter', 0), t1, t2)
                if mapping:
                    mkt, outcome, param_str = mapping
                    sharp_edge = intel.true_edge(t1, t2, mkt, outcome, param_str, odds_val)
                    if sharp_edge is not None:
                        edge_val = round(max(-0.30, min(0.30, sharp_edge)), 4)
            if edge_val is None and lambdas:
                model_p = model_probability(odd.get('type', 0), odd.get('parameter', 0), lambdas[0], lambdas[1])
                if model_p is not None and 0.04 <= model_p <= 0.96:
                    edge_val = round(max(-0.30, min(0.25, (model_p * odds_val) - 1)), 4)

            props.append({
                'player': player_display, 'prop': p, 'match': match_display,
                'odd': round(odds_val, 2), 'sport': 'futbol', 'team': team,
                'date': date_str, 'link': link, 'logo': logo,
                'is_winner': is_winner_pick, 'side': side,
                'match_key': f"{t1} vs {t2}", 'day': day_label,
                'tournament': tournament, 'edge': edge_val,
                'sharp_edge': sharp_edge, 'model_p': model_p,
                'edge_source': 'sharp' if sharp_edge is not None else ('poisson' if model_p is not None else None),
                'game_id': event.get('sportEventId', 0),
                'type_id': odd.get('type', 0),
                'param': odd.get('parameter', 0),
                'player_id': odd.get('playerId', 0),
            })
    return props


def build_wc_tickets(pool):
    """Build World Cup tickets. Max 1 leg per match, edge-sorted."""
    tickets = []
    used_keys = set()
    winner_side = {}

    unique_matches = list(set(p['match'] for p in pool))
    n_matches = len(unique_matches)
    print(f"   🏟️  {n_matches} partidos WC disponibles")

    ultra = [p for p in pool if 1.20 <= p['odd'] <= 1.50]
    low = [p for p in pool if 1.50 < p['odd'] <= 1.80]
    mid = [p for p in pool if 1.80 < p['odd'] <= 2.30]
    high = [p for p in pool if 2.30 < p['odd'] <= 3.00]
    very_high = [p for p in pool if 3.00 < p['odd'] <= 10.0]
    print(f"   ultra: {len(ultra)}, low: {len(low)}, mid: {len(mid)}, high: {len(high)}, wc: {len(very_high)}")

    def _edge_key(p):
        e = p.get('edge')
        return -(e if e is not None else -1.0) - random.uniform(-0.02, 0.02)

    def pick_legs(pools_config):
        selected, matches_used = [], set()
        for pool_list, count in pools_config:
            avail = [p for p in pool_list if prop_key(p) not in used_keys and p['match'] not in matches_used]
            avail.sort(key=_edge_key)
            picked = 0
            for p in avail:
                if picked >= count or p['match'] in matches_used:
                    continue
                if p.get('is_winner') and p.get('match_key'):
                    mk = p['match_key']
                    if mk in winner_side and winner_side[mk] != p['side']:
                        continue
                selected.append(p)
                matches_used.add(p['match'])
                picked += 1
        if len(selected) >= sum(c for _, c in pools_config):
            for s in selected:
                used_keys.add(prop_key(s))
                if s.get('is_winner') and s.get('match_key'):
                    winner_side[s['match_key']] = s['side']
            return selected
        return None

    combos = []
    if n_matches >= 6:
        combos = [
            ((very_high, 1), (high, 2), (mid, 3), (low, 2), (ultra, 2)),
            ((very_high, 1), (high, 2), (mid, 2), (low, 2), (ultra, 2)),
            ((very_high, 1), (high, 1), (mid, 3), (low, 2), (ultra, 2)),
            ((very_high, 1), (mid, 2), (low, 2), (ultra, 2)),
            ((very_high, 1), (high, 1), (mid, 2), (low, 1), (ultra, 2)),
            ((high, 1), (mid, 2), (low, 2), (ultra, 2)),
            ((very_high, 1), (mid, 2), (low, 1), (ultra, 2)),
            ((very_high, 1), (low, 2), (ultra, 3)),
            ((high, 1), (mid, 1), (low, 2), (ultra, 2)),
            ((low, 2), (ultra, 4)),
            ((low, 3), (ultra, 3)),
            ((ultra, 6),),
            ((low, 1), (ultra, 5)),
        ]
    elif n_matches >= 4:
        combos = [
            ((very_high, 1), (mid, 1), (low, 1), (ultra, 1)),
            ((very_high, 1), (low, 1), (ultra, 2)),
            ((high, 1), (mid, 1), (ultra, 2)),
            ((mid, 1), (low, 1), (ultra, 2)),
            ((low, 2), (ultra, 2)),
            ((ultra, 4),),
        ]
    elif n_matches >= 2:
        combos = [
            ((very_high, 1), (ultra, 1)),
            ((mid, 1), (low, 1)),
            ((high, 1), (ultra, 1)),
            ((low, 2),), ((ultra, 2),),
        ]
    else:
        combos = [((very_high, 1),), ((mid, 1),), ((low, 1),)]

    for combo in combos:
        for _ in range(8):
            for pl, _ in combo:
                random.shuffle(pl)
            legs = pick_legs(list(combo))
            if legs:
                total = round(math.prod(l['odd'] for l in legs), 1)
                if total >= 3.0:
                    edges = [l.get('edge') for l in legs if l.get('edge') is not None]
                    avg_e = sum(edges) / len(edges) if edges else None
                    cov = len(edges) / len(legs) if edges else 0
                    ms = round(max(0.0, min(10.0, (avg_e + 0.15) / 0.25 * 10)) * cov + 5 * (1 - cov), 1) if avg_e is not None else None
                    tickets.append({
                        'tier': 'pending', 'legs': legs, 'total_odds': total,
                        'confidence': calculate_confidence(legs),
                        'model_score': ms,
                        'avg_edge': round(avg_e, 4) if avg_e is not None else None,
                        'model_coverage': round(cov, 2),
                    })

    tickets = [t for t in tickets if t['confidence'] >= 3]
    for t in tickets:
        o, all_low = t['total_odds'], all(l['odd'] <= 1.80 for l in t['legs'])
        if o >= 1000: t['tier'] = 'megalodon'
        elif o >= 100: t['tier'] = 'whale'
        elif o >= 10: t['tier'] = 'shark'
        elif all_low and o <= 6: t['tier'], t['confidence'] = 'segura', 6
        elif all_low and o <= 9: t['tier'], t['confidence'] = 'confiable', 5
        else: t['tier'] = 'hunter'

    caps = {'megalodon': 4, 'whale': 5, 'shark': 4, 'hunter': 3, 'confiable': 3, 'segura': 3}
    order = {'megalodon': 0, 'whale': 1, 'shark': 2, 'hunter': 3, 'confiable': 4, 'segura': 5}
    by_tier = {k: [] for k in caps}
    for t in tickets:
        if t['tier'] in by_tier:
            by_tier[t['tier']].append(t)
    capped = []
    for tier, mx in caps.items():
        capped.extend(sorted(by_tier[tier], key=lambda t: (-t['confidence'], -t['total_odds']))[:mx])
    tickets = sorted(capped, key=lambda t: (order.get(t['tier'], 99), -t['total_odds']))

    counters = {k: 0 for k in caps}
    for t in tickets:
        counters[t['tier']] += 1
        t['id'] = f"WC-{t['tier'][0].upper()}{counters[t['tier']]}"
        t['title'] = "🏆 Mundial · Fútbol Props Mix"
    return tickets


def main():
    print("🏆 MasterProps — World Cup 2026 Ticket Generator")
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

    print("🔑 Authenticating...")
    token = get_token()
    print("📡 Fetching events...")
    data = fetch_events(token)
    print(f"✅ {data.get('count', 0)} events loaded")

    intel = None
    if HAS_INTEL:
        odds_key = os.environ.get('ODDS_API_KEY', '')
        fb_key = os.environ.get('FOOTBALL_API_KEY', '')
        if odds_key or fb_key:
            from market_intelligence import MarketIntel
            print("\n📈 Market Intelligence...")
            intel = MarketIntel(odds_api_key=odds_key, football_api_key=fb_key)
            intel.fetch_sharp_odds()
            pairs = [(ev.get('opponent1NameLocalization', ''), ev.get('opponent2NameLocalization', ''))
                     for ev in data.get('items', []) if ev.get('tournamentNameLocalization') == 'World Cup 2026']
            if pairs:
                intel.fetch_team_stats(pairs[:50])
            intel.fetch_all()
            build_prop_pool._intel = intel
        else:
            build_prop_pool._intel = None
    else:
        build_prop_pool._intel = None

    now_ar = datetime.now(timezone.utc) + AR_OFFSET
    from collections import defaultdict
    by_date = defaultdict(list)
    for ev in data.get('items', []):
        if ev.get('tournamentNameLocalization') != 'World Cup 2026' or ev.get('sportId') != 1:
            continue
        ts = ev.get('startDate', 0)
        if ts:
            by_date[(datetime.fromtimestamp(ts, tz=timezone.utc) + AR_OFFSET).date()].append(ev)

    sorted_dates = sorted(by_date.keys())
    print(f"\n🏆 {sum(len(v) for v in by_date.values())} partidos en {len(sorted_dates)} jornadas")
    for d in sorted_dates[:10]:
        ms = [f"{e.get('opponent1NameLocalization','')} vs {e.get('opponent2NameLocalization','')}" for e in by_date[d]]
        print(f"  📅 {d.strftime('%a %d/%m')}: {len(ms)} — {', '.join(ms[:3])}{'...' if len(ms)>3 else ''}")

    all_tickets = []
    upcoming = [d for d in sorted_dates if d >= now_ar.date()][:5]

    for i, md in enumerate(upcoming[:3]):
        ds = (datetime.combine(md, datetime.min.time(), tzinfo=timezone.utc) - AR_OFFSET).timestamp()
        de = (datetime.combine(md, datetime.max.time(), tzinfo=timezone.utc) - AR_OFFSET).timestamp()
        dn = md.strftime('%a %d/%m')
        print(f"\n🎯 Jornada {i+1}: {dn} ({len(by_date[md])} partidos)")
        pool = wc_build_prop_pool(data, ds, de, f'wc{i+1}', intel)
        if intel and intel.sharp_odds:
            pool = [p for p in pool if p.get('sharp_edge') is None or p['sharp_edge'] > -0.05]
        print(f"  ✅ {len(pool)} props")
        if pool:
            tix = build_wc_tickets(pool)
            for t in tix:
                t['id'] = f"WC{i+1}-{t['id'].split('-',1)[1]}"
                t['title'] = f"🏆 {dn} · Fútbol Props Mix"
            all_tickets.extend(tix)
            print(f"  🎫 {len(tix)} billetes")

    if len(upcoming) >= 2:
        ms, me = upcoming[0], upcoming[min(2, len(upcoming)-1)]
        mss = (datetime.combine(ms, datetime.min.time(), tzinfo=timezone.utc) - AR_OFFSET).timestamp()
        mee = (datetime.combine(me, datetime.max.time(), tzinfo=timezone.utc) - AR_OFFSET).timestamp()
        print(f"\n🎯 Multi: {ms.strftime('%d/%m')}—{me.strftime('%d/%m')}")
        pool_m = wc_build_prop_pool(data, mss, mee, 'wcm', intel)
        if intel and intel.sharp_odds:
            pool_m = [p for p in pool_m if p.get('sharp_edge') is None or p['sharp_edge'] > -0.05]
        print(f"  ✅ {len(pool_m)} props")
        if pool_m:
            mtix = build_wc_tickets(pool_m)
            big = [t for t in mtix if t['tier'] in ('megalodon', 'whale', 'shark')]
            for t in big:
                t['id'] = f"WCM-{t['id'].split('-',1)[1]}"
                t['title'] = f"🏆 Multi-Jornada · Fútbol Props Mix"
            all_tickets.extend(big)
            print(f"  🎫 {len(big)} multi-jornada (shark+)")

    tickets = sorted(all_tickets, key=lambda t: ({'megalodon':0,'whale':1,'shark':2,'hunter':3,'confiable':4,'segura':5}.get(t['tier'],99), -t['total_odds']))

    print(f"\n📊 RESUMEN: {len(tickets)} billetes mundialistas")
    for t in tickets:
        print(f"  {t['id']:15s} [{t['tier'].upper():10s}] x{t['total_odds']:>8.1f} | {len(t['legs'])} legs | conf: {t['confidence']}/6")

    if not tickets:
        print("\n⚠️  No tickets generated")
        return

    # Read existing tickets, remove old WC ones, prepend new WC
    existing = OUTPUT_FILE.read_text(encoding='utf-8')
    m = re.search(r'const TICKETS = \[([\s\S]*?)\];', existing)
    non_wc = []
    if m:
        blocks = re.findall(r'  \{ id:.*?legs:\[.*?\]\},?', m.group(1), re.DOTALL)
        for b in blocks:
            if not re.search(r"id:'WC[^']*'", b):
                non_wc.append(b.rstrip(','))

    published_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    wc_lines = []
    for t in tickets:
        legs_js = []
        for l in t['legs']:
            lk = l.get('link', '').replace('/en/', '/es/')
            ej = f"{l.get('edge')}" if l.get('edge') is not None else "null"
            legs_js.append(f"    {{player:'{_esc(l['player'])}', prop:'{_esc(l['prop'])}', match:'{_esc(l['match'])}', odd:{l['odd']}, sport:'{l['sport']}', team:'{_esc(l['team'])}', date:'{l.get('date','')}', logo:'{_esc(l.get('logo',''))}', edge:{ej}, link:'{_esc(lk)}'}}")
        ms = f"{t.get('model_score')}" if t.get('model_score') is not None else "null"
        ae = f"{t.get('avg_edge')}" if t.get('avg_edge') is not None else "null"
        wc_lines.append(f"  {{ id:'{t['id']}', tier:'{t['tier']}', sport:'futbol', title:'{_esc(t['title'])}', confidence:{t['confidence']}, totalOdds:{t['total_odds']}, modelScore:{ms}, avgEdge:{ae}, publishedAt:'{published_at}', couponCode:'', legs:[\n" + ",\n".join(legs_js) + "\n  ]}")

    final = "const TICKETS = [\n" + ",\n".join(wc_lines + non_wc) + "\n];"
    results = "const LEG_RESULTS = {};"

    print("\n📝 Updating HTML...")
    import shutil
    shutil.copy2(TEMPLATE_FILE, OUTPUT_FILE)
    for f in [OUTPUT_FILE, TEMPLATE_FILE]:
        c = f.read_text(encoding='utf-8')
        c = re.sub(r'const TICKETS = \[[\s\S]*?\];', final, c, count=1)
        c = re.sub(r'const LEG_RESULTS = \{[^}]*\};', results, c, count=1)
        f.write_text(c, encoding='utf-8')
        print(f"  ✅ {f.name}")

    # Coupon codes
    td = [{'ticket_id': t['id'], 'events': [{'GameId': l.get('game_id',0), 'Type': l.get('type_id',0), 'Coef': l['odd'], 'Param': l.get('param',0), 'PlayerId': l.get('player_id',0)} for l in t['legs']]} for t in tickets]
    (BASE_DIR / 'tickets_data.json').write_text(json.dumps(td, indent=2), encoding='utf-8')

    coupons = {}
    try:
        from generate_coupons import generate_coupon_codes
        print("\n🎫 Generating coupons...")
        coupons = generate_coupon_codes(td)
        print(f"✅ {len(coupons)} coupons")
    except Exception as e:
        print(f"\n⚠️  Coupons failed: {e}")

    if coupons:
        for f in [OUTPUT_FILE, TEMPLATE_FILE]:
            c = f.read_text(encoding='utf-8')
            for tid, code in coupons.items():
                if code:
                    c = re.sub(f"(id:'{re.escape(tid)}'.*?couponCode:')[^']*(')", f"\\g<1>{code}\\2", c, flags=re.DOTALL)
            f.write_text(c, encoding='utf-8')

    print(f"\n🏆 DONE — {len(tickets)} billetes mundialistas!")


if __name__ == '__main__':
    main()
