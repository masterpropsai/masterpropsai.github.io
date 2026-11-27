#!/usr/bin/env python3
"""Gate de escudos: el mapa de gambeta.ai esta cargado y el cruce sigue siendo estricto."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escudos

m = escudos._cargar()
fallas = []
if len(m['exacto']) < 1500:
    fallas.append(f"mapa con {len(m['exacto'])} nombres (esperado 1500+): correr scripts/sync_escudos.py")
for a, b in escudos.ALIAS.items():
    if escudos.norm(b) not in m['exacto']:
        fallas.append(f'alias {a!r} apunta a {b!r}, que no esta en el mapa de gambeta')
CASOS = [
    ('Independiente Rivadavia', 'Argentina', 'independiente-rivadavia'),   # no tiene que caer en Independiente
    ('Independiente', 'Argentina', 'independiente.png'),
    ('Nacional', 'Portugal. Primeira Liga', 'nacional-madeira'),
    ('Nacional', 'Uruguay. Primera Division', 'nacional.png'),
    ('Barcelona', 'Copa Libertadores', 'barcelona-sc'),
    ('Chelsea', 'England. Premier League', 'chelsea'),
    ('Oud-Heverlee Leuven', 'Belgium. Jupiler League', 'oh-leuven'),
    ('Equipo Que No Existe FC', '', None),
    ('Real', 'Spain', None),                                              # un pedazo de nombre no alcanza
]
for nombre, liga, espera in CASOS:
    u = escudos.escudo(nombre, liga)
    if (espera is None and u) or (espera and (not u or espera not in u)):
        fallas.append(f'{nombre!r} ({liga}) -> {u} (esperado {espera})')
for x in fallas:
    print('  ❌', x)
print(f"escudos: {len(m['exacto'])} nombres, {len(escudos.ALIAS)} alias, {len(fallas)} fallas")
sys.exit(1 if fallas else 0)
