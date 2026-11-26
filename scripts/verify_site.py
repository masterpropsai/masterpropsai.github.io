#!/usr/bin/env python3
"""Chequeo despues de publicar: mira masterprops.ai EN PRODUCCION y falla (exit 1) si
lo que se sirve no es lo de hoy. Misma idea que verify-deploy.sh de gambeta.ai:
no dar por bueno un deploy sin medirlo. Uso: python scripts/verify_site.py [url]"""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import history_lib as hl

URL = (sys.argv[1] if len(sys.argv) > 1 else 'https://masterprops.ai').rstrip('/')
fails, oks = [], []


def get(path):
    req = urllib.request.Request(f"{URL}{path}?cb={int(time.time())}", headers={'User-Agent': 'Mozilla/5.0 (verify)'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode('utf-8', 'replace')


def check(nombre, ok, detalle=''):
    (oks if ok else fails).append(nombre)
    print(('  ✅ ' if ok else '  ❌ ') + nombre + (f' — {detalle}' if detalle else ''))


html = get('/')
tks = hl.parse_tickets(html)
legs = [l for t in tks for l in t['legs']]
check('hay billetes publicados', len(tks) >= 5, f'{len(tks)} billetes, {len(legs)} selecciones')

now = datetime.now(timezone.utc)
dias = {(now + timedelta(days=d)).strftime('%b %d') for d in (-1, 0, 1, 2)}
frescas = sum(1 for l in legs if l['date'][:6] in dias)
check('las selecciones son de estos dias', legs and frescas >= 0.9 * len(legs), f'{frescas}/{len(legs)}')

malas = [l['player'] for l in legs if re.search(r'virtual|esport|ecomp|cyber', l['player'] + ' ' + l['match'], re.I)]
check('sin partidos virtuales ni eSports', not malas, ', '.join(malas[:3]))

no_fut = [l['player'] for l in legs if l['sport'] != 'futbol']
check('solo deportes que se pueden verificar', not no_fut, ', '.join(no_fut[:3]))

cup = re.findall(r"couponCode:'([^']*)'", html)
con = sum(1 for c in cup if c)
check('billetes con cupon de DBbet', cup and con >= 0.8 * len(cup), f'{con}/{len(cup)}')

check('historial presente', 'const HISTORY = ' in html and 'const HISTORY_TOTALS = ' in html)
check('afiliado de DBbet presente', 'refpa96317.com' in html)

try:
    td = json.loads(get('/tickets_data.json'))
    check('tickets_data.json valido (lo lee el banner de gambeta.ai)', isinstance(td, list) and len(td) >= 5, f'{len(td)} billetes')
except Exception as e:
    check('tickets_data.json valido (lo lee el banner de gambeta.ai)', False, type(e).__name__)

print(f"\n{len(oks)} pass / {len(fails)} fail")
sys.exit(1 if fails else 0)
