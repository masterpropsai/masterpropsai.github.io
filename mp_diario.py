#!/usr/bin/env python3
"""
MasterProps — registro diario + resolver gratis con ESPN (26-nov-2026)
=====================================================================
Por que existe:
  * Los ids de billete (WKD-W1, SAT-S2...) se repiten todos los dias y el
    generador pisa index.html en cada corrida. Lo publicado ayer se perdia antes
    de resolverse y el historial solo guardaba el primer billete de cada id.
  * La llave de The Odds API que resolvia los marcadores dejo de funcionar.

Que hace:
  ledger/AAAA-MM-DD.json  = los billetes de ese dia TAL COMO se publicaron.
                            Se escribe una sola vez: un billete publicado no se
                            cambia ni se borra (regla aprendida en gambeta.ai).
  Los resultados salen del scoreboard publico de ESPN (sin llave): marcador
  final, entretiempo y orden de los goles. Si un partido no se encuentra con
  certeza, queda pendiente: nunca se inventa un resultado.

Uso:
  python mp_diario.py hoy        -> sale 0 si ya hay billetes de hoy, 1 si no
  python mp_diario.py guardar    -> guarda los billetes de index.html como los de hoy
  python mp_diario.py resolver   -> resuelve lo pendiente y actualiza historial/HTML
  python mp_diario.py cruce      -> prueba: que partidos pendientes encuentra en ESPN
"""
import json, os, re, sys, unicodedata, urllib.request
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import auto_resolve as ar
import history_lib as hl

BASE = os.path.dirname(os.path.abspath(__file__))
LEDGER_DIR = os.path.join(BASE, 'ledger')
INDEX = os.path.join(BASE, 'index.html')
TEMPLATE = os.path.join(BASE, 'template.html')
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?limit=1000&dates='

HIST_EN_HTML = 60          # billetes con detalle que viajan en el HTML (el resto, solo totales)
DIAS_ABIERTO = 15          # un dia sin terminar se sigue intentando resolver este tiempo
MIN_DESDE_INICIO = 125     # minutos desde el inicio para buscar el marcador final

TICKETS_RE = re.compile(r"const TICKETS = \[(.*?)\n\];", re.DOTALL)
RESULTS_RE = re.compile(r"const LEG_RESULTS = \{.*?\};", re.DOTALL)


# ───────────────────────── fechas ─────────────────────────
def hoy_ar(now=None):
    now = now or datetime.now(timezone.utc)
    return (now - timedelta(hours=3)).date().isoformat()


def parse_fecha(s, ref):
    """'Nov 26 · 20:00' (UTC) -> datetime. El anio sale de la fecha del registro."""
    m = re.match(r"([A-Za-z]+)\.?\s+(\d{1,2})\s*·\s*(\d{1,2}):(\d{2})", s or '')
    if not m or m.group(1) not in hl.MONTHS:
        return None
    mes = hl.MONTHS[m.group(1)]
    anio = ref.year + (1 if (ref.month == 12 and mes == 1) else 0)
    try:
        return datetime(anio, mes, int(m.group(2)), int(m.group(3)), int(m.group(4)), tzinfo=timezone.utc)
    except ValueError:
        return None


# ───────────────────────── registro ─────────────────────────
def ruta(dia):
    return os.path.join(LEDGER_DIR, dia + '.json')


def leer(dia):
    with open(ruta(dia), encoding='utf-8') as f:
        return json.load(f)


def escribir(reg):
    os.makedirs(LEDGER_DIR, exist_ok=True)
    with open(ruta(reg['dia']), 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)


def dias():
    if not os.path.isdir(LEDGER_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(LEDGER_DIR) if re.match(r"\d{4}-\d{2}-\d{2}\.json$", f))


def html_de(reg):
    """HTML minimo con el que trabajan auto_resolve.py e history_lib.py."""
    return "const TICKETS = [" + reg['tickets_raw'] + "\n];\n" + reg['leg_results_js'] + "\n"


def guardar():
    dia = hoy_ar()
    if os.path.exists(ruta(dia)):
        print(f"ya hay billetes guardados para {dia}: no se tocan")
        return 0
    html = open(INDEX, encoding='utf-8').read()
    m = TICKETS_RE.search(html)
    if not m:
        print("ERROR: no encuentro const TICKETS en index.html")
        return 1
    n = len(hl.parse_tickets(html))
    if n == 0:
        print("ERROR: index.html no trae billetes")
        return 1
    ok_file = os.path.join(BASE, '.espn_ok.json')
    espn_ok = json.load(open(ok_file)) if os.path.exists(ok_file) else []
    escribir({
        'dia': dia,
        'espn_ok': espn_ok,
        'generado': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'billetes': n,
        'cerrado': False,
        'tickets_raw': m.group(1),
        'leg_results_js': 'const LEG_RESULTS = {\n};',
    })
    print(f"guardados {n} billetes de {dia}")
    return 0


# ───────────────────────── ESPN ─────────────────────────
_STOP = {'fc', 'cf', 'ac', 'sc', 'cd', 'ca', 'afc', 'sv', 'club', 'de', 'la', 'el', 'the', 'fk', 'sk', 'if',
         'as', 'ss', 'us', 'ud', 'rc', 'rcd', 'cs', 'ec', 'se', 'cr', 'bk', 'nk', 'vfl', 'vfb', 'tsg', 'bsc'}


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s.replace('.', ''))
    return ' '.join(w for w in s.split() if w not in _STOP)


# Nombres que ESPN escribe distinto que el feed de la casa (se agrega a medida que aparecen)
ALIAS = {
    'copenhagen': 'kobenhavn', 'crvena zvezda': 'red star belgrade', 'stade brestois 29': 'brest',
    'stade brestois': 'brest', 'bayern munich': 'bayern munchen', 'sporting lisbon': 'sporting cp',
    'inter milan': 'internazionale', 'psg': 'paris saint germain', 'ath bilbao': 'athletic club',
    'athletic bilbao': 'athletic club', 'nott forest': 'nottingham forest',
}


def parecido(a, b):
    a, b = norm(a), norm(b)
    a, b = ALIAS.get(a, a), ALIAS.get(b, b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = set(a.split()), set(b.split())
    if ta and tb and (ta <= tb or tb <= ta) and max(len(w) for w in ta & tb) >= 4:
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


def nombres(comp):
    t = comp.get('team') or {}
    return [x for x in (t.get('displayName'), t.get('shortDisplayName'), t.get('name'), t.get('location')) if x]


def codigo_ok(code, comp):
    code = norm(code)
    if not code:
        return False
    t = comp.get('team') or {}
    if norm(t.get('abbreviation', '')) == code:
        return True
    for nm in nombres(comp):
        n = norm(nm)
        if n.replace(' ', '').startswith(code) or any(w.startswith(code) for w in n.split()):
            return True
        if ''.join(w[0] for w in n.split()).startswith(code):
            return True
    return False


_cache = {}


def espn_dia(fecha):
    key = fecha.strftime('%Y%m%d')
    if key not in _cache:
        try:
            req = urllib.request.Request(ESPN + key, headers={'User-Agent': 'Mozilla/5.0 (MasterProps resolver)'})
            with urllib.request.urlopen(req, timeout=40) as r:
                _cache[key] = json.loads(r.read().decode()).get('events', [])
        except Exception as e:
            print(f"   aviso: ESPN {key} no respondio ({type(e).__name__})", file=sys.stderr)
            _cache[key] = []
    return _cache[key]


def buscar(local_name, visitor_code, inicio, aprobados=None):
    """-> (evento, lado_del_local 'home'|'away') o (None, motivo)."""
    eventos = {}
    for d in (inicio - timedelta(days=1), inicio, inicio + timedelta(days=1)):
        for e in espn_dia(d):
            eventos[e['id']] = e
    cands = []
    for e in eventos.values():
        try:
            ko = datetime.strptime(e['date'][:16], '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if abs((ko - inicio).total_seconds()) > 25 * 60:
            continue
        comps = (e.get('competitions') or [{}])[0].get('competitors') or []
        if len(comps) != 2:
            continue
        for i, c in enumerate(comps):
            s = max((parecido(local_name, n) for n in nombres(c)), default=0)
            otro = comps[1 - i]
            cod = codigo_ok(visitor_code, otro)
            if s >= 0.86 or (s >= 0.6 and cod):
                cands.append((s + (0.2 if cod else 0), e, c.get('homeAway')))
    if not cands and aprobados:
        # Respaldo: entre los partidos que ESPN ya tenia cuando se armo el billete,
        # a esa misma hora, el que mas se parece (la lista es corta y verificada).
        for e in eventos.values():
            if e['id'] not in aprobados:
                continue
            ko = datetime.strptime(e['date'][:16], '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
            if abs((ko - inicio).total_seconds()) > 25 * 60:
                continue
            comps = e['competitions'][0]['competitors']
            for i, c in enumerate(comps):
                s = max((parecido(local_name, n) for n in nombres(c)), default=0)
                if s >= 0.45 and codigo_ok(visitor_code, comps[1 - i]):
                    cands.append((s, e, c.get('homeAway')))
    if not cands:
        return None, 'no-encontrado'
    cands.sort(key=lambda x: -x[0])
    if len(cands) > 1 and cands[1][1]['id'] != cands[0][1]['id'] and cands[0][0] - cands[1][0] < 0.08:
        return None, 'ambiguo'
    return cands[0][1], cands[0][2]


def minuto(det):
    """-> (minuto base, es_descuento) desde "45'+2'" / "67'"."""
    dv = ((det.get('clock') or {}).get('displayValue') or '')
    m = re.match(r"(\d+)'?(\+)?", dv)
    if not m:
        return None, False
    return int(m.group(1)), bool(m.group(2))


def marcador(e, lado_local):
    """-> dict con el resultado a los 90' o (None, motivo)."""
    comp = e['competitions'][0]
    st = ((comp.get('status') or {}).get('type') or {})
    if not st.get('completed'):
        return None, 'sin-terminar'
    if st.get('name') in ('STATUS_POSTPONED', 'STATUS_CANCELED', 'STATUS_ABANDONED', 'STATUS_SUSPENDED'):
        return None, 'suspendido'
    por_lado = {c['homeAway']: c for c in comp['competitors']}
    ids = {str(c['team']['id']): c['homeAway'] for c in comp['competitors']}
    final = {}
    try:
        for lado, c in por_lado.items():
            final[lado] = int(c.get('score'))
    except (TypeError, ValueError):
        return None, 'sin-marcador'

    goles = []
    for d in comp.get('details') or []:
        if not d.get('scoringPlay') or d.get('shootout'):
            continue
        lado = ids.get(str((d.get('team') or {}).get('id')))
        mn, extra = minuto(d)
        if lado is None or mn is None:
            return None, 'detalle-incompleto'
        goles.append((mn, extra, lado, bool(d.get('ownGoal'))))

    def cuenta(gs, voltear):
        out = {'home': 0, 'away': 0}
        for mn, extra, lado, og in gs:
            if og and voltear:
                lado = 'away' if lado == 'home' else 'home'
            out[lado] += 1
        return out

    # Las apuestas se pagan a los 90' + descuento: se descartan los goles del alargue.
    aet = st.get('name') in ('STATUS_FINAL_AET', 'STATUS_FINAL_PEN')
    reg = [g for g in goles if g[0] <= 90]
    if not aet:
        voltear = None
        for v in (False, True):
            if cuenta(goles, v) == final:
                voltear = v
                break
        if voltear is None:
            return None, 'detalle-no-cierra'      # el detalle de goles no coincide con el marcador
    else:
        voltear = False
        if any(g[3] for g in reg):
            return None, 'alargue-con-gol-en-contra'
        final = cuenta(reg, False)

    otro = 'away' if lado_local == 'home' else 'home'
    seq, ht = [], {'home': 0, 'away': 0}
    for mn, extra, lado, og in sorted(reg, key=lambda g: (g[0], g[1])):
        if og and voltear:
            lado = 'away' if lado == 'home' else 'home'
        seq.append('local' if lado == lado_local else 'visitor')
        if mn <= 45:
            ht[lado] += 1
    return {
        'local_goals': final[lado_local], 'visitor_goals': final[otro],
        'ht_local': ht[lado_local], 'ht_visitor': ht[otro],
        'goal_scorers': seq,
    }, 'ok'


def buscar_par(t1, t2, inicio):
    """Al generar: el partido del feed (t1 local, t2 visitante) existe en ESPN? -> id o None."""
    mejor = None
    for d in (inicio - timedelta(days=1), inicio, inicio + timedelta(days=1)):
        for e in espn_dia(d):
            try:
                ko = datetime.strptime(e['date'][:16], '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if abs((ko - inicio).total_seconds()) > 25 * 60:
                continue
            comps = (e.get('competitions') or [{}])[0].get('competitors') or []
            if len(comps) != 2:
                continue
            for i in (0, 1):
                s1 = max((parecido(t1, n) for n in nombres(comps[i])), default=0)
                s2 = max((parecido(t2, n) for n in nombres(comps[1 - i])), default=0)
                if min(s1, s2) >= 0.6 or (max(s1, s2) >= 0.86 and min(s1, s2) >= 0.3):
                    if mejor is None or s1 + s2 > mejor[0]:
                        mejor = (s1 + s2, e['id'])
    return mejor[1] if mejor else None


# ───────────────────────── resolver ─────────────────────────
_PRUEBAS = [(2, 1, 1, 0, ['local', 'visitor', 'local']), (0, 0, 0, 0, []),
            (1, 3, 0, 2, ['visitor', 'visitor', 'local', 'visitor'])]


def equipos(player):
    """'(COD vs) Equipo' -> ('paren', Equipo, COD) ; 'A vs B' -> ('gen', A, B) ; otro -> None."""
    m = re.match(r"\((\w+)\s+vs\)\s+(.+)", player or '')
    if m:
        return 'paren', m.group(2).strip(), m.group(1)
    if ' vs ' in (player or ''):
        a, b = player.split(' vs ', 1)
        return 'gen', a.strip(), b.strip()
    return None


def resolver_prop(prop, r, local_name, visitor_name):
    """-> 'won' | 'lost' | 'push' | 'void' o None si no se sabe resolver con certeza."""
    lg, vg = r['local_goals'], r['visitor_goals']
    g1 = r['ht_local'] + r['ht_visitor']
    try:
        out = ar.resolve_prop_v2(prop, lg, vg, lg + vg, r['ht_local'], r['ht_visitor'], g1, lg + vg - g1,
                                 r['goal_scorers'], local_name, visitor_name)
    except Exception:
        out = 'SKIP'
    if out in ('won', 'lost', 'push', 'void'):
        return out
    p = (prop or '').strip()
    if p == 'Total Impar':
        return 'won' if (lg + vg) % 2 == 1 else 'lost'
    if p == 'Total Par':
        return 'won' if (lg + vg) % 2 == 0 else 'lost'
    return None


def resoluble(player, prop):
    """Al generar: esta seleccion se va a poder resolver con marcador, entretiempo y goles?"""
    eq = equipos(player)
    if not eq:
        return False
    for lg, vg, hl_, hv, seq in _PRUEBAS:
        r = {'local_goals': lg, 'visitor_goals': vg, 'ht_local': hl_, 'ht_visitor': hv, 'goal_scorers': seq}
        if resolver_prop(prop, r, eq[1], eq[2] if eq[0] == 'gen' else 'Rival') is None:
            return False
    return True


def buscar_gen(a, b, inicio, aprobados):
    """Partido 'A vs B' de una seleccion general -> (evento, lado de A) o (None, motivo)."""
    mejor = None
    eventos = {}
    for d in (inicio - timedelta(days=1), inicio, inicio + timedelta(days=1)):
        for e in espn_dia(d):
            eventos[e['id']] = e
    for e in eventos.values():
        try:
            ko = datetime.strptime(e['date'][:16], '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if abs((ko - inicio).total_seconds()) > 25 * 60:
            continue
        comps = (e.get('competitions') or [{}])[0].get('competitors') or []
        if len(comps) != 2:
            continue
        for i in (0, 1):
            s1 = max((parecido(a, n) for n in nombres(comps[i])), default=0)
            s2 = max((parecido(b, n) for n in nombres(comps[1 - i])), default=0)
            ok = min(s1, s2) >= 0.6 or (max(s1, s2) >= 0.86 and min(s1, s2) >= 0.3)
            if not ok and e['id'] in aprobados:
                ok = max(s1, s2) >= 0.6 or s1 + s2 >= 0.9
            if ok and (mejor is None or s1 + s2 > mejor[0]):
                mejor = (s1 + s2, e, comps[i].get('homeAway'))
    if not mejor:
        return None, 'no-encontrado'
    return mejor[1], mejor[2]


def resolver_dia(reg, now, solo_cruce=False):
    ref = datetime.fromisoformat(reg['dia']).replace(tzinfo=timezone.utc)
    html = html_de(reg)
    hechos = hl.parse_leg_results(html)
    aprobados = set(reg.get('espn_ok') or [])
    info = {'pendientes': 0, 'partidos': 0, 'encontrados': 0, 'resueltos': 0, 'motivos': {}}

    def motivo(k):
        info['motivos'][k] = info['motivos'].get(k, 0) + 1

    partidos, nuevos = {}, {}
    for tk in hl.parse_tickets(html):
        for j, leg in enumerate(tk['legs']):
            key = f"{tk['id']}_{j}"
            if key in hechos:
                continue
            info['pendientes'] += 1
            eq = equipos(leg['player'])
            inicio = parse_fecha(leg['date'], ref)
            if not eq or not inicio:
                motivo('formato-raro')
                continue
            pk = (leg['player'], leg['date'])
            if pk not in partidos:
                info['partidos'] += 1
                if not solo_cruce and (now - inicio).total_seconds() < MIN_DESDE_INICIO * 60:
                    partidos[pk] = (None, 'aun-no-termina', None)
                else:
                    if eq[0] == 'paren':
                        ev, lado = buscar(eq[1], eq[2], inicio, aprobados)
                    else:
                        ev, lado = buscar_gen(eq[1], eq[2], inicio, aprobados)
                    if ev is None:
                        partidos[pk] = (None, lado, None)
                        if solo_cruce:
                            print(f"   ✗ {leg['player']:42s} {leg['match'][:22]:22s} {leg['date']}  [{lado}]")
                    else:
                        info['encontrados'] += 1
                        if solo_cruce:
                            partidos[pk] = (None, 'cruce', None)
                            print(f"   ✓ {leg['player']:42s} -> {ev['name']}")
                        else:
                            res, mot = marcador(ev, lado)
                            rival = next((c['team'].get('displayName', '') for c in ev['competitions'][0]['competitors']
                                          if c.get('homeAway') != lado), '')
                            partidos[pk] = (res, mot, rival)
            res, mot, rival = partidos[pk]
            if res is None:
                motivo(mot)
                continue
            r = resolver_prop(leg['prop'], res, eq[1], eq[2] if eq[0] == 'gen' else rival)
            if r is None:
                motivo('seleccion-no-resoluble')
                continue
            nuevos[key] = {'result': r, 'player': leg['player'].replace('\n', ' '), 'prop': leg['prop'].replace('\n', ' ')}
    if solo_cruce or not nuevos:
        return info, False
    html = ar.inject_results(html, nuevos, 'ESPN ' + now.strftime('%Y-%m-%d %H:%MZ'))
    reg['leg_results_js'] = RESULTS_RE.search(html).group(0)
    info['resueltos'] = len(nuevos)
    info['ganadas'] = sum(1 for v in nuevos.values() if v['result'] == 'won')
    info['perdidas'] = sum(1 for v in nuevos.values() if v['result'] == 'lost')
    return info, True


def archivar(reg, hist):
    """Pasa al historial los billetes terminados de ese dia. id unico = id + fecha."""
    html = html_de(reg)
    lr = hl.parse_leg_results(html)
    conocidos = {t['id'] for t in hist['tickets']}
    dd, mm = reg['dia'][8:10], reg['dia'][5:7]
    cambio, todos = False, True
    for tk in hl.parse_tickets(html):
        estado, fin = hl.ticket_status(tk, lr)
        if not fin:
            todos = False
            continue
        uid = f"{tk['id']} · {dd}/{mm}"
        if uid in conocidos:
            continue
        legs = []
        for j, leg in enumerate(tk['legs']):
            leg = dict(leg)
            r = lr.get(f"{tk['id']}_{j}")
            leg['result'] = 'void' if r == 'push' else r
            legs.append(leg)
        hist['tickets'].append({
            'id': uid, 'tier': tk['tier'], 'sport': tk['sport'], 'title': tk['title'],
            'confidence': tk['confidence'], 'totalOdds': tk['totalOdds'],
            'publishedAt': tk['publishedAt'] or reg['generado'],
            'status': estado, 'resolvedAt': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'dia': reg['dia'], 'legs': legs,
        })
        cambio = True
    return cambio, todos


def totales(hist):
    t = {'n': 0, 'tw': 0, 'tl': 0, 'lw': 0, 'll': 0}
    for h in hist['tickets']:
        t['n'] += 1
        if h.get('status') == 'won':
            t['tw'] += 1
        elif h.get('status') == 'lost':
            t['tl'] += 1
        for l in h.get('legs') or []:
            if l.get('result') == 'won':
                t['lw'] += 1
            elif l.get('result') == 'lost':
                t['ll'] += 1
    return t


def historial_js(hist):
    orden = sorted(hist['tickets'], key=lambda t: (t.get('resolvedAt', ''), t.get('status') == 'won'), reverse=True)
    return ("const HISTORY = " + json.dumps(orden[:HIST_EN_HTML], ensure_ascii=False) + ";\n"
            "const HISTORY_TOTALS = " + json.dumps(totales(hist)) + ";")


def publicar_html(hist, reg_hoy):
    """Lleva al sitio el historial y, si los billetes en pantalla son los de hoy, sus resultados."""
    for fn in (INDEX, TEMPLATE):
        html = open(fn, encoding='utf-8').read()
        html = re.sub(r"\nconst HISTORY_TOTALS = \{.*?\};", "", html, count=1)
        js = historial_js(hist)
        if re.search(r"const HISTORY = ", html):
            html = re.sub(r"const HISTORY = .*?\];", lambda _: js, html, count=1, flags=re.DOTALL)
        else:
            m = RESULTS_RE.search(html)
            if m:
                html = html[:m.end()] + "\n\n// === HISTORIAL (billetes terminados) ===\n" + js + html[m.end():]
        if reg_hoy is not None:
            m = TICKETS_RE.search(html)
            if m and m.group(1) == reg_hoy['tickets_raw']:
                html = RESULTS_RE.sub(lambda _: reg_hoy['leg_results_js'], html, count=1)
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(html)


def resolver(solo_cruce=False):
    now = datetime.now(timezone.utc)
    hist = hl.load_history()
    resumen, toco = {}, False
    for dia in dias():
        reg = leer(dia)
        if reg.get('cerrado'):
            continue
        info, cambio = resolver_dia(reg, now, solo_cruce)
        resumen[dia] = info
        if solo_cruce:
            continue
        nuevo_hist, todos = archivar(reg, hist)
        edad = (now.date() - datetime.fromisoformat(dia).date()).days
        if todos or edad > DIAS_ABIERTO:
            reg['cerrado'] = True
            cambio = True
        if cambio or nuevo_hist:
            escribir(reg)
            toco = True
    if solo_cruce:
        print(json.dumps(resumen, ensure_ascii=False, indent=1))
        return 0
    hl.save_history(hist)
    hoy = hoy_ar(now)
    publicar_html(hist, leer(hoy) if os.path.exists(ruta(hoy)) else None)
    with open(os.path.join(BASE, 'stats.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(totales(hist), actualizado=now.isoformat(timespec='seconds'), fuente='ESPN'), f, indent=1)
    print(json.dumps({'cambios': toco, 'historial': totales(hist), 'dias': resumen}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'hoy':
        sys.exit(0 if os.path.exists(ruta(hoy_ar())) else 1)
    elif cmd == 'guardar':
        sys.exit(guardar())
    elif cmd == 'resolver':
        sys.exit(resolver())
    elif cmd == 'cruce':
        sys.exit(resolver(solo_cruce=True))
    print(__doc__)
    sys.exit(2)
