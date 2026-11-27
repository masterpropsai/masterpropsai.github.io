#!/usr/bin/env python3
"""Copia el mapa de escudos de gambeta.ai a data/escudos_gambeta.json (27-nov-2026, Mauro:
"que MasterProps use los escudos de Gambeta, que estan todos corregidos").

Fuente: functions/previa/_teamlogos.js del repo de gambeta.ai (generado desde su unico mapa
teamLogos). Ese repo es privado, asi que esto se corre A MANO en la Mac cuando Gambeta suma
o corrige escudos, y se commitea el JSON:

    python scripts/sync_escudos.py ~/Documents/ia-apuestas

Las imagenes NO se copian: se sirven desde https://gambeta.ai/escudos/ (ya optimizadas)."""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escudos

origen = os.path.join(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/Documents/ia-apuestas'),
                      'functions', 'previa', '_teamlogos.js')
txt = open(origen, encoding='utf-8').read()
cuerpo = txt[txt.index('export default {') + len('export default '):txt.rindex('}') + 1]
mapa = json.loads(cuerpo)

exacto, reducido, choque = {}, {}, set()
for nombre, u in mapa.items():
    if u.startswith('/escudos/'):
        u = 'https://gambeta.ai' + u
    elif not u.startswith('https://'):
        continue
    exacto.setdefault(escudos.norm(nombre), u)
    r = escudos.reducir(nombre)
    if r and r != escudos.norm(nombre):
        if r in reducido and reducido[r] != u:
            choque.add(r)
        reducido.setdefault(r, u)
# una forma reducida que apunta a dos escudos distintos no se usa: seria adivinar el club
for r in choque:
    reducido.pop(r, None)
reducido = {k: v for k, v in reducido.items() if k not in exacto}

os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data'), exist_ok=True)
destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'escudos_gambeta.json')
json.dump({'exacto': exacto, 'reducido': reducido}, open(destino, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
print(f'{len(mapa)} alias de gambeta -> {len(exacto)} nombres exactos + {len(reducido)} formas cortas ({len(choque)} ambiguas descartadas)')
