#!/usr/bin/env python3
"""
MasterProps — Historial persistente
===================================
Archiva billetes terminados (ganados/perdidos) en history.json y los inyecta
como `const HISTORY = [...]` en el HTML para la sección HISTORIAL del sitio.

Usado por: generate.py (carryover + inyección), check_results.py y
auto_resolve.py (archivado tras resolver). history.json es la fuente de verdad
y sobrevive a las regeneraciones del pipeline.
"""
import json, re, os
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE, 'history.json')

MONTHS = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,
          'Sep':9,'Sept':9,'Oct':10,'Nov':11,'Dec':12,'Ene':1,'Abr':4,'Ago':8,'Dic':12}

TICKET_BLOCK_RE = re.compile(r"\{ id:'([^']+)',.*?legs:\[(.*?)\n\s*\]\},?", re.DOTALL)
LEG_OBJ_RE = re.compile(r"\{[^{}]*\}")


def _field(src, name, default=''):
    m = re.search(name + r":'((?:[^'\\]|\\.)*)'", src)
    return m.group(1).replace("\\'", "'") if m else default


def _num(src, name, default=0.0):
    m = re.search(name + r":([\d.]+)", src)
    return float(m.group(1)) if m else default


def parse_tickets(html):
    """Parsea los bloques de TICKETS del HTML → lista de dicts (con bloque raw)."""
    m = re.search(r"const TICKETS = \[(.*?)\n\];", html, re.DOTALL)
    if not m:
        return []
    out = []
    for tm in TICKET_BLOCK_RE.finditer(m.group(1)):
        raw = tm.group(0)
        head = raw.split('legs:[')[0]
        legs = []
        for lm in LEG_OBJ_RE.finditer(tm.group(2)):
            ls = lm.group(0)
            legs.append({
                'player': _field(ls, 'player'),
                'prop':   _field(ls, 'prop'),
                'match':  _field(ls, 'match'),
                'odd':    _num(ls, 'odd'),
                'date':   _field(ls, 'date'),
                'sport':  _field(ls, 'sport'),
            })
        out.append({
            'id': tm.group(1),
            'tier': _field(head, 'tier'),
            'sport': _field(head, 'sport'),
            'title': _field(head, 'title'),
            'confidence': int(_num(head, 'confidence', 0)),
            'totalOdds': _num(head, 'totalOdds'),
            'publishedAt': _field(head, 'publishedAt'),
            'legs': legs,
            '_raw': raw.rstrip(','),
        })
    return out


def parse_leg_results(html):
    """Entradas de LEG_RESULTS → {clave: resultado}. Soporta formato JSON y con comillas simples."""
    m = re.search(r"const LEG_RESULTS = \{(.*?)\};", html, re.DOTALL)
    if not m:
        return {}
    return dict(re.findall(r"[\"']([\w-]+_\d+)[\"']\s*:\s*[\"'](\w+)[\"']", m.group(1)))


def leg_date_passed(date_str, grace_days=2, now=None):
    """True si una fecha estilo 'Jun 14 · 01:00' ya pasó claramente (con margen)."""
    now = now or datetime.now(timezone.utc)
    m = re.match(r"([A-Za-z]+)\.?\s+(\d{1,2})", date_str or '')
    if not m or m.group(1) not in MONTHS:
        return False
    cand = datetime(now.year, MONTHS[m.group(1)], int(m.group(2)), tzinfo=timezone.utc)
    if (cand - now).days > 180:
        cand = cand.replace(year=now.year - 1)
    elif (now - cand).days > 180:
        cand = cand.replace(year=now.year + 1)
    return (now - cand).days >= grace_days


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            data = json.loads(open(HISTORY_FILE, encoding='utf-8').read())
            if isinstance(data, dict) and isinstance(data.get('tickets'), list):
                return data
        except json.JSONDecodeError:
            pass
    return {'tickets': []}


def save_history(hist):
    hist['updated_at'] = datetime.now(timezone.utc).isoformat()
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(hist, indent=2, ensure_ascii=False))


def ticket_status(ticket, leg_results):
    """→ (estado, terminado). Estado: won | lost | void | pending."""
    res = [leg_results.get(f"{ticket['id']}_{j}") for j in range(len(ticket['legs']))]
    if not res:
        return 'pending', False
    decided = [r for r in res if r in ('won', 'lost', 'void', 'push')]
    has_lost = 'lost' in res
    if len(decided) == len(res):                      # todas las patas resueltas
        if has_lost:
            return 'lost', True
        return ('won' if 'won' in res else 'void'), True
    dates = [l.get('date', '') for l in ticket['legs']]
    if has_lost and all(leg_date_passed(d, 2) for d in dates):
        return 'lost', True                            # muerto y todos los partidos jugados
    if all(leg_date_passed(d, 14) for d in dates):     # vencido sin resolución completa
        return ('lost' if has_lost else 'void'), True
    return ('lost' if has_lost else 'pending'), False


def archive_finished(html, extra_leg_results=None):
    """Archiva en history.json los billetes terminados. → (cambió, ids_terminados)."""
    leg_results = parse_leg_results(html)
    for k, v in (extra_leg_results or {}).items():
        leg_results.setdefault(k, v)
    hist = load_history()
    known = {t['id'] for t in hist['tickets']}
    changed, finished_ids = False, set()
    for tk in parse_tickets(html):
        status, finished = ticket_status(tk, leg_results)
        if not finished:
            continue
        finished_ids.add(tk['id'])
        if tk['id'] in known:
            continue
        legs = []
        for j, leg in enumerate(tk['legs']):
            leg = dict(leg)
            r = leg_results.get(f"{tk['id']}_{j}")
            leg['result'] = 'void' if r == 'push' else r
            legs.append(leg)
        hist['tickets'].append({
            'id': tk['id'], 'tier': tk['tier'], 'sport': tk['sport'],
            'title': tk['title'], 'confidence': tk['confidence'],
            'totalOdds': tk['totalOdds'], 'publishedAt': tk['publishedAt'],
            'status': status,
            'resolvedAt': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'legs': legs,
        })
        changed = True
    if changed:
        save_history(hist)
    return changed, finished_ids


def history_js(hist=None):
    hist = hist or load_history()
    tickets = sorted(hist['tickets'], key=lambda t: t.get('resolvedAt', ''), reverse=True)
    return "const HISTORY = " + json.dumps(tickets, ensure_ascii=False) + ";"


def inject_history(html, hist=None):
    """Reemplaza (o inserta) `const HISTORY = [...]` en el HTML."""
    js = history_js(hist)
    if re.search(r"const HISTORY = ", html):
        return re.sub(r"const HISTORY = .*?\];", js, html, count=1, flags=re.DOTALL)
    m = re.search(r"const LEG_RESULTS = \{.*?\};", html, re.DOTALL)
    if m:
        return html[:m.end()] + "\n\n// === HISTORIAL (billetes terminados) ===\n" + js + html[m.end():]
    return html


def carryover_blocks(old_html, fresh_ids, finished_ids):
    """Bloques raw de billetes aún pendientes que deben sobrevivir a la regeneración."""
    out = []
    for tk in parse_tickets(old_html):
        if tk['id'] in fresh_ids or tk['id'] in finished_ids:
            continue
        out.append(tk['_raw'])
    return out


def carryover_leg_results(old_html, new_html):
    """Copia el bloque LEG_RESULTS del index viejo al nuevo (memoria de resultados)."""
    m = re.search(r"const LEG_RESULTS = \{.*?\};", old_html, re.DOTALL)
    if not m:
        return new_html
    return re.sub(r"const LEG_RESULTS = \{.*?\};", lambda _: m.group(0), new_html, count=1, flags=re.DOTALL)
