#!/usr/bin/env python3
"""MasterProps stage 1/2 — build tickets + HTML, defer coupon codes.
Runs generate_live.main() but stubs the SaveCoupon network so the run finishes
well within the Cowork 45s shell budget. Coupon codes are filled in afterwards
by mp_publish_coupons.py. Writes index.html, template.html, tickets_data.json.
"""
import json, sys, time
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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))
import escudos

_fetch = g.fetch_events
_por_link = {}        # link del evento -> (local, visitante, liga, logo1, logo2)
_por_logo = {}        # logo de la casa -> (nombre del equipo en el feed, liga)

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
            liga = e.get('tournamentNameLocalization', '')
            _por_link[e.get('link', '')] = (t1, t2, liga, (e.get('imageOpponent1') or [''])[0], (e.get('imageOpponent2') or [''])[0])
            for nombre, img in ((t1, e.get('imageOpponent1') or []), (t2, e.get('imageOpponent2') or [])):
                if img:
                    _por_logo[g.LOGO_BASE + img[0]] = (nombre, liga)
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
    # Escudos de gambeta.ai (curados y optimizados) en lugar del logo de la casa, cuando el
    # equipo se reconoce con certeza; si no, queda el de la casa (27-nov-2026, Mauro).
    n = 0
    for p in ok:
        if not p.get('logo'):
            # Seleccion "de partido" (Mas de 2.5 goles en A vs B): los dos escudos
            ev = _por_link.get(p.get('link', ''))
            if ev:
                t1, t2, liga, i1, i2 = ev
                a = escudos.escudo(t1, liga) or (g.LOGO_BASE + i1 if i1 else '')
                b = escudos.escudo(t2, liga) or (g.LOGO_BASE + i2 if i2 else '')
                if a and b:
                    p['logoA'], p['logoB'] = a, b
            continue
        crudo, liga = _por_logo.get(p['logo'], ('', p.get('match', '')))
        eq = mp_diario.equipos(p.get('player', ''))
        u = escudos.escudo([crudo, eq[1] if eq and eq[0] == 'paren' else ''], liga)
        if u:
            p['logo'] = u
            n += 1
    print('     escudos de gambeta: %d de %d con logo' % (n, sum(1 for p in ok if p.get('logo'))))
    print('     resolubles: %d de %d' % (len(ok), len(props)))
    return ok

g.build_prop_pool = _pool_resoluble

t0 = time.time()
g.main()
print('mp_build OK in %.1fs' % (time.time() - t0))
