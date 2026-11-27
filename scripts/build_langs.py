#!/usr/bin/env python3
"""Genera /en/ /pt/ /it/ /fr/ /ru/ a partir de index.html + i18n/<idioma>.json (27-nov-2026).

Corre en el workflow despues de cada cambio de index.html (billetes nuevos o resultados),
asi las cinco versiones muestran siempre lo mismo que la española.

Que traduce: todo el texto fijo (frases enteras, con sus etiquetas), rotulos que arma el
JavaScript (I18N), literales sueltos, las selecciones de cada billete (plantillas) y los
metadatos. Que NO traduce: nombres de equipos y ligas, marcas, el blog y las paginas legales
(siguen en español: no hay version traducida todavia).

Uso: python scripts/build_langs.py [--check]   (--check: no escribe, solo valida)
"""
import json, os, re, sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SITIO = 'https://masterprops.ai/'
LANGS = {'en': ('en', 'en_US'), 'pt': ('pt-BR', 'pt_BR'), 'it': ('it', 'it_IT'), 'fr': ('fr', 'fr_FR'), 'ru': ('ru', 'ru_RU')}
DATOS = [r"const TICKETS = \[.*?\n\];", r"const HISTORY = .*?\];", r"const LEG_RESULTS = \{.*?\n\};"]
ATTRS = ('aria-label', 'title', 'placeholder', 'alt')


def js_ascii(s):
    """Texto -> seguro dentro de cualquier literal JS ('..', "..", `..`)."""
    out = []
    for ch in s:
        o = ord(ch)
        if ch in "'\"`\\":
            out.append('\\x%02x' % o)
        elif ch == '$':
            out.append('\\x24')
        elif o < 128:
            out.append(ch)
        elif o > 0xFFFF:
            o -= 0x10000
            out.append('\\u%04x\\u%04x' % (0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF)))
        else:
            out.append('\\u%04x' % o)
    return ''.join(out)


def js_escapado(s):
    """Variante del texto fuente tal como puede estar escrito en el JS (con \\uXXXX)."""
    out = []
    for ch in s:
        o = ord(ch)
        if o < 128:
            out.append(ch)
        elif o > 0xFFFF:
            o -= 0x10000
            out.append('\\u%04x\\u%04x' % (0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF)))
        else:
            out.append('\\u%04x' % o)
    return ''.join(out)


def cargar():
    es = json.load(open('i18n/es.json', encoding='utf-8'))
    trs = {l: json.load(open(f'i18n/{l}.json', encoding='utf-8')) for l in LANGS if os.path.exists(f'i18n/{l}.json')}
    return es, trs


def proteger(html):
    """Saca los bloques de datos (billetes, historial, resultados) para no tocarlos."""
    guardado = []

    def fuera(m):
        guardado.append(m.group(0))
        return f'/*@@DATOS{len(guardado) - 1}@@*/'
    for pat in DATOS:
        html = re.sub(pat, fuera, html, count=1, flags=re.S)
    return html, guardado


def partes(html):
    """-> lista de (es_script, texto) para tratar distinto el HTML y el JavaScript."""
    out, pos = [], 0
    for m in re.finditer(r'(<script\b[^>]*>)(.*?)(</script>)', html, re.S):
        out.append((False, html[pos:m.start(2)]))
        out.append((True, m.group(2)))
        pos = m.end(2)
    out.append((False, html[pos:]))
    return out


def construir(lang, src, es, tr):
    faltan = [k for k in es if not tr.get(k)]
    if faltan:
        raise SystemExit(f'{lang}: faltan {len(faltan)} traducciones, p.ej. {faltan[:3]}')
    html, guardado = proteger(src)
    avisos = []

    unidades_html = sorted(((v['es'], tr[k]) for k, v in es.items() if v['tipo'] == 'html'), key=lambda x: -len(x[0]))
    unidades_attr = [(v['es'], tr[k]) for k, v in es.items() if v['tipo'] == 'attr']
    unidades_js = sorted(((v['es'], tr[k]) for k, v in es.items() if v['tipo'] == 'js'), key=lambda x: -len(x[0]))

    nuevas, usadas = [], set()
    for es_script, t in partes(html):
        if not es_script:
            for a, b in unidades_html:
                pat = re.compile(r'(?<=>)(\s*)' + re.escape(a) + r'(\s*)(?=<)')
                t, n = pat.subn(lambda m: m.group(1) + b + m.group(2), t)
                if n:
                    usadas.add(a)
            for a, b in unidades_attr:
                for at in ATTRS:
                    t = t.replace(f'{at}="{a}"', f'{at}="{b.replace(chr(34), "&quot;")}"')
        else:
            for a, b in unidades_js:
                usado = False
                for forma in {a, js_escapado(a)}:
                    if forma in t:
                        t = t.replace(forma, js_ascii(b))
                        usado = True
                if usado:
                    usadas.add(a)
        nuevas.append(t)
    html = ''.join(nuevas)
    avisos += [f'sin uso: {a[:60]}' for a, _ in unidades_html + unidades_js if a not in usadas]

    # Rotulos del JavaScript: se pisan los de I18N.es (el codigo sigue corriendo "en es")
    keys = {k[4:]: tr[k] for k, v in es.items() if v['tipo'] == 'key'}
    if isinstance(keys.get('confLevels'), str):
        keys['confLevels'] = [''] + keys['confLevels'].split('|')
    props = sorted(((v['es'], tr[k]) for k, v in es.items() if v['tipo'] == 'prop'), key=lambda x: -len(x[0]))
    locale, og = LANGS[lang]
    iny = ('\n// === idioma: ' + lang + ' (generado por scripts/build_langs.py) ===\n'
           'Object.assign(I18N.es, ' + json.dumps(keys, ensure_ascii=True) + ');\n')
    m = re.search(r"\nlet currentLang = 'es';", html)
    assert m, 'no encuentro currentLang'
    html = html[:m.start()] + iny + html[m.start():]
    pre = ('<script>window.MP_LANG=' + json.dumps(lang) + ';window.MP_LOCALE=' + json.dumps(locale)
           + ';window.MP_PROPS=' + json.dumps(props, ensure_ascii=True) + ';</script>\n')
    html = html.replace('<body', pre + '<body', 1) if False else html
    # el script de datos del idioma va primero dentro de <body>
    html = re.sub(r'(<body[^>]*>)', lambda k: k.group(1) + '\n' + pre, html, count=1)

    # Cabecera
    url = SITIO + lang + '/'
    title, desc = tr['meta.title'], tr['meta.description']
    esc = lambda x: x.replace('&', '&amp;').replace('"', '&quot;')
    html = re.sub(r'<html lang="[^"]*"', f'<html lang="{locale}"', html, count=1)
    html = re.sub(r'<title>.*?</title>', lambda _: f'<title>{title.replace("&", "&amp;")}</title>', html, count=1, flags=re.S)
    for pat, val in [(r'(<meta name="description" content=")[^"]*(")', desc),
                     (r'(<meta property="og:title" content=")[^"]*(")', title),
                     (r'(<meta property="og:description" content=")[^"]*(")', desc),
                     (r'(<meta name="twitter:title" content=")[^"]*(")', title),
                     (r'(<meta name="twitter:description" content=")[^"]*(")', desc),
                     (r'(<meta property="og:url" content=")[^"]*(")', url),
                     (r'(<meta property="og:locale" content=")[^"]*(")', og),
                     (r'(<link rel="canonical" href=")[^"]*(")', url)]:
        html = re.sub(pat, lambda k, v=val: k.group(1) + esc(v) + k.group(2), html, count=1)
    # JSON-LD: fuera las preguntas frecuentes (estan en español y no se muestran traducidas)
    html = re.sub(r'<script type="application/ld\+json">(?:(?!</script>).)*?"FAQPage".*?</script>\n?', '', html, flags=re.S)
    html = re.sub(r'("@type":\s*"WebSite".*?"description":\s*")[^"]*(")', lambda k: k.group(1) + desc.replace('"', "'") + k.group(2), html, count=1, flags=re.S)
    html = re.sub(r'("inLanguage":\s*")[^"]*(")', lambda k: k.group(1) + locale + k.group(2), html)
    # bandera activa
    html = html.replace('class="lang-flag active" href="/"', 'class="lang-flag" href="/"')
    html = html.replace(f'class="lang-flag" href="/{lang}/"', f'class="lang-flag active" href="/{lang}/"')

    # El bloque "ultimo pick acertado de gambeta.ai" llega en español desde su API: no se muestra
    html = html.replace('</head>', '<style>#gambeta-crosspromo{display:none !important}</style>\n</head>', 1)
    for i, g in enumerate(guardado):
        html = html.replace(f'/*@@DATOS{i}@@*/', g, 1)
    return html, avisos


def main():
    check = '--check' in sys.argv
    es, trs = cargar()
    src = open('index.html', encoding='utf-8').read()
    hechos = 0
    for lang in LANGS:
        if lang not in trs:
            print(f'  {lang}: sin i18n/{lang}.json, se saltea')
            continue
        html, avisos = construir(lang, src, es, trs[lang])
        for a in sorted(set(avisos))[:6]:
            print(f'  {lang} aviso: {a}')
        if not check:
            os.makedirs(lang, exist_ok=True)
            destino = os.path.join(lang, 'index.html')
            if not os.path.exists(destino) or open(destino, encoding='utf-8').read() != html:
                open(destino, 'w', encoding='utf-8').write(html)
        hechos += 1
    print(f'idiomas generados: {hechos}/{len(LANGS)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
