#!/usr/bin/env python3
"""Pone los escudos de gambeta.ai en los billetes YA publicados del ultimo dia guardado, sin
tocar ninguna seleccion ni cuota (solo los campos logo / logoA / logoB). Sirve para el dia en
que se cambia el mapa de escudos; los billetes nuevos ya salen con escudo desde mp_build.py.

Necesita DBBET_CLIENT_ID y DBBET_CLIENT_SECRET (lee el feed para saber que equipo es cada logo).
    python scripts/aplicar_escudos.py"""
import json, os, re, sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(RAIZ)
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))
import escudos, generate_live as g, mp_diario

dia = mp_diario.dias()[-1]
reg = mp_diario.leer(dia)
raw = reg['tickets_raw']
for fn in ('index.html', 'template.html'):
    m = mp_diario.TICKETS_RE.search(open(fn, encoding='utf-8').read())
    if not m or m.group(1) != raw:
        raise SystemExit(f'{fn}: los billetes en pantalla no son los de {dia}; no se toca nada')

por_logo, por_link = {}, {}
for e in g.fetch_events(g.get_token())['items']:
    t1, t2 = e.get('opponent1NameLocalization', ''), e.get('opponent2NameLocalization', '')
    liga = e.get('tournamentNameLocalization', '')
    i1, i2 = (e.get('imageOpponent1') or [''])[0], (e.get('imageOpponent2') or [''])[0]
    if i1:
        por_logo[g.LOGO_BASE + i1] = (t1, liga)
    if i2:
        por_logo[g.LOGO_BASE + i2] = (t2, liga)
    link = e.get('link', '')
    por_link[link.replace('/en/', '/es/')] = por_link[link] = (t1, t2, liga, i1, i2)

cuenta = {'un escudo': 0, 'dos escudos': 0, 'sin cambio': 0}


def leg(m):
    s = m.group(0)
    logo = re.search(r"logo:'([^']*)'", s).group(1)
    link = re.search(r"link:'([^']*)'", s)
    link = link.group(1) if link else ''
    if 'logoA:' in s:
        return s
    if logo:
        crudo, liga = por_logo.get(logo, ('', ''))
        eq = mp_diario.equipos(re.search(r"player:'((?:[^'\\]|\\.)*)'", s).group(1).replace("\\'", "'"))
        u = escudos.escudo([crudo, eq[1] if eq and eq[0] == 'paren' else ''], liga or re.search(r"match:'([^']*)'", s).group(1))
        if u and u != logo:
            cuenta['un escudo'] += 1
            return s.replace(f"logo:'{logo}'", f"logo:'{u}'", 1)
    elif link in por_link:
        t1, t2, liga, i1, i2 = por_link[link]
        a = escudos.escudo(t1, liga) or (g.LOGO_BASE + i1 if i1 else '')
        b = escudos.escudo(t2, liga) or (g.LOGO_BASE + i2 if i2 else '')
        if a and b:
            cuenta['dos escudos'] += 1
            return s.replace("logo:'', ", f"logo:'', logoA:'{a}', logoB:'{b}', ", 1)
    cuenta['sin cambio'] += 1
    return s


nuevo = re.sub(r"\{player:'[^{}]*\}", leg, raw)
print(dia, cuenta)
if nuevo != raw:
    assert len(mp_diario.hl.parse_tickets('const TICKETS = [' + nuevo + '\n];')) == reg['billetes']
    reg['tickets_raw'] = nuevo
    mp_diario.escribir(reg)
    for fn in ('index.html', 'template.html'):
        s = open(fn, encoding='utf-8').read()
        open(fn, 'w', encoding='utf-8').write(s.replace(raw, nuevo, 1))
    print('aplicado en index.html, template.html y ledger/' + dia + '.json')
