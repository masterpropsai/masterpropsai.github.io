#!/usr/bin/env python3
"""Gate de SEO: frena la publicacion si una pagina pierde lo basico. Se corre en el
workflow antes de publicar. Mide archivos locales; produccion la mide verify_site.py."""
import glob, html, os, re, sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SITIO = 'https://masterprops.ai'
fallas = []
paginas = ['index.html'] + sorted(glob.glob('blog/*.html'))


def url(f):
    return SITIO + '/' if f == 'index.html' else SITIO + '/blog/' if f == 'blog/index.html' else f"{SITIO}/{f[:-5]}"


sm = open('sitemap.xml', encoding='utf-8').read()
locs = re.findall(r'<loc>(.*?)</loc>', sm)
if set(locs) != {url(f) for f in paginas}:
    fallas.append('sitemap.xml no coincide con las paginas que existen')
if len(locs) != len(set(locs)):
    fallas.append('sitemap.xml con URLs repetidas')

titulos, entrantes = {}, {}
for f in paginas:
    s = open(f, encoding='utf-8').read()
    t = re.search(r'<title>(.*?)</title>', s, re.S)
    t = html.unescape(t.group(1)).strip() if t else ''
    if not t or ord(t[0]) < 0x2000:
        fallas.append(f'{f}: el <title> no empieza con emoji')
    if len(t) > 65:
        fallas.append(f'{f}: <title> de {len(t)} caracteres (max 65)')
    if t in titulos:
        fallas.append(f'{f}: mismo <title> que {titulos[t]}')
    titulos[t] = f
    if not re.search(r'<link rel="canonical" href="' + re.escape(url(f)) + '"', s):
        fallas.append(f'{f}: canonica ausente o distinta de {url(f)}')
    if not re.search(r'<meta name="description" content="[^"]{60,}"', s):
        fallas.append(f'{f}: sin meta description')
    if len(re.findall(r'<h1[\s>]', s)) != 1:
        fallas.append(f'{f}: tiene que haber un solo <h1>')
    if 'noindex' in s.lower():
        fallas.append(f'{f}: tiene noindex')
    for h in set(re.findall(r'href="(/[^"#?]*)', s)):
        p = h.lstrip('/')
        if not (h == '/' or os.path.exists(p) or os.path.exists(p + '.html') or os.path.exists(os.path.join(p, 'index.html'))):
            fallas.append(f'{f}: enlace interno roto {h}')
        if h.startswith('/blog/') and h != '/blog/':
            entrantes.setdefault(h.split('/')[-1], set()).add(f)

for f in paginas:
    if f.startswith('blog/') and not f.endswith('index.html'):
        n = len(entrantes.get(os.path.basename(f)[:-5], set()) - {f})
        if n < 3:
            fallas.append(f'{f}: solo {n} enlaces internos entrantes (min 3)')
if 'href="/blog/"' not in open('index.html', encoding='utf-8').read():
    fallas.append('index.html: la home no enlaza al blog')

for x in fallas:
    print('  ❌', x)
print(f"SEO: {len(paginas)} paginas, {len(fallas)} fallas")
sys.exit(1 if fallas else 0)
