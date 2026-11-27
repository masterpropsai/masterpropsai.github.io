#!/usr/bin/env python3
"""Gate de idiomas: frena la publicacion si una version traducida quedaria incompleta.
Misma idea que los tests de idioma de gambeta.ai: nada nuevo sale sin sus traducciones.

  1. El molde no tiene textos nuevos sin inventariar (i18n/es.json al dia).
  2. Cada idioma traduce TODAS las unidades, sin romper etiquetas ni {team}/{n}.
  3. Titulo (emoji + max 65) y descripcion (max 160) por idioma.
  4. La pagina generada no conserva frases en español del inventario.
"""
import json, os, re, sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, 'scripts')
import i18n_extract, build_langs

fallas = []
es = json.load(open('i18n/es.json', encoding='utf-8'))
ahora = i18n_extract.extraer()
for k in ahora:
    if k not in es:
        fallas.append(f'texto nuevo en el molde sin inventariar ni traducir: {ahora[k]["es"][:70]!r} '
                      f'(correr scripts/i18n_extract.py y traducirlo a los 5 idiomas)')

TAG = re.compile(r'<[^>]+>')
PH = re.compile(r'\{(?:team|n)\}')
src = open('index.html', encoding='utf-8').read()
for lang in build_langs.LANGS:
    f = f'i18n/{lang}.json'
    if not os.path.exists(f):
        fallas.append(f'{lang}: falta {f}')
        continue
    tr = json.load(open(f, encoding='utf-8'))
    for k, v in es.items():
        t = tr.get(k)
        if not t or not str(t).strip():
            fallas.append(f'{lang}: sin traduccion {k}')
            continue
        if sorted(TAG.findall(v['es'])) != sorted(TAG.findall(t)):
            fallas.append(f'{lang}: etiquetas HTML distintas en {k}')
        if sorted(PH.findall(v['es'])) != sorted(PH.findall(t)):
            fallas.append(f'{lang}: {{team}}/{{n}} distintos en {k}')
        if k == 'key.confLevels' and t.count('|') != v['es'].count('|'):
            fallas.append(f'{lang}: key.confLevels tiene que traer 6 niveles')
        if v['tipo'] == 'attr' and '"' in t:
            fallas.append(f'{lang}: comillas en {k}')
    t, d = tr.get('meta.title', ''), tr.get('meta.description', '')
    if not t or ord(t[0]) < 0x2000 or len(t) > 65:
        fallas.append(f'{lang}: meta.title sin emoji o de {len(t)} caracteres')
    if len(d) > 160:
        fallas.append(f'{lang}: meta.description de {len(d)} caracteres')
    if fallas:
        continue
    html, avisos = build_langs.construir(lang, src, es, tr)
    cuerpo, _ = build_langs.proteger(html)
    estatico = ''.join(t for s, t in build_langs.partes(cuerpo) if not s)
    for k, v in es.items():
        if v['tipo'] == 'html' and tr[k] != v['es'] and re.search(r'>\s*' + re.escape(v['es']) + r'\s*<', estatico):
            fallas.append(f'{lang}: quedo en español {v["es"][:60]!r}')
    if f'<html lang="{build_langs.LANGS[lang][0]}"' not in html or f'rel="canonical" href="https://masterprops.ai/{lang}/"' not in html:
        fallas.append(f'{lang}: lang o canonica mal')
    if html.count('hreflang="') < 7:
        fallas.append(f'{lang}: faltan hreflang')

for x in fallas[:40]:
    print('  ❌', x)
print(f"idiomas: {len(build_langs.LANGS)} versiones, {len(es)} unidades, {len(fallas)} fallas")
sys.exit(1 if fallas else 0)
