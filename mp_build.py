#!/usr/bin/env python3
"""MasterProps stage 1/2 — build tickets + HTML, defer coupon codes.
Runs generate_live.main() but stubs the SaveCoupon network so the run finishes
well within the Cowork 45s shell budget. Coupon codes are filled in afterwards
by mp_publish_coupons.py. Writes index.html, template.html, tickets_data.json.
"""
import json, time
import generate_live as g

class _Resp:
    @staticmethod
    def json():
        return {'Success': False, 'Value': '', 'Error': 'deferred-to-mp_publish_coupons'}

# Defer coupon generation (filled by stage 2) and drop courtesy sleeps
g.requests.post = lambda *a, **k: _Resp()
time.sleep = lambda *a, **k: None

# Los ids de billete (WKD-W1, SAT-S2...) se repiten todos los dias: un cupon viejo
# guardado en coupons.json apuntaria a OTRO billete. Se arranca siempre de cero.
(g.Path(__file__).parent / 'coupons.json').write_text('{}', encoding='utf-8')

# Solo se publica lo que despues se puede verificar (26-nov-2026): futbol, y solo
# partidos que el scoreboard publico de ESPN ya tiene cargados a esa hora. Asi cada
# seleccion publicada termina con resultado y el historial no queda con huecos.
import os
from datetime import datetime, timedelta, timezone
import mp_diario

_fetch = g.fetch_events

def _fetch_verificable(token):
    data = _fetch(token)
    items = data['items'] if isinstance(data, dict) else data
    now = datetime.now(timezone.utc)
    keep, ids = [], set()
    for e in items:
        ts = e.get('startDate') or 0
        if e.get('sportId') != 1 or not ts:
            continue
        ko = datetime.fromtimestamp(ts, tz=timezone.utc)
        if ko < now or ko > now + timedelta(hours=54):
            continue
        t1, t2 = e.get('opponent1NameLocalization', ''), e.get('opponent2NameLocalization', '')
        if not g.is_tournament_allowed(e.get('tournamentNameLocalization', ''), t1, t2):
            continue
        eid = mp_diario.buscar_par(t1, t2, ko)
        if eid:
            keep.append(e)
            ids.add(eid)
    print('ESPN: %d partidos verificables de %d eventos del feed' % (len(keep), len(items)))
    json.dump(sorted(ids), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.espn_ok.json'), 'w'))
    if isinstance(data, dict):
        data['items'] = keep
        return data
    return keep

g.fetch_events = _fetch_verificable

# ...y solo selecciones que el resolver sabe cerrar con marcador, entretiempo y orden
# de los goles (afuera "Penal", y los mercados con texto ambiguo).
_pool = g.build_prop_pool

def _pool_resoluble(*a, **k):
    props = _pool(*a, **k)
    ok = [p for p in props if mp_diario.resoluble(p.get('player', ''), p.get('prop', ''))]
    print('     resolubles: %d de %d' % (len(ok), len(props)))
    return ok

g.build_prop_pool = _pool_resoluble

t0 = time.time()
g.main()
print('mp_build OK in %.1fs' % (time.time() - t0))
