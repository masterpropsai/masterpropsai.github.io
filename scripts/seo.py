#!/usr/bin/env python3
"""SEO de MasterProps (etapa 3, 27-nov-2026). Idempotente: se puede correr siempre.

  python scripts/seo.py            -> aplica todo (titulos, relacionadas, enlace al blog, sitemap)
  python scripts/seo.py --sitemap  -> solo regenera sitemap.xml (lo corre el workflow diario)

Lo aprendido en gambeta.ai que se aplica aca:
  * la palanca es autoridad, no volumen: no se crean notas nuevas, se enlazan bien las que hay;
  * todo <title> empieza con emoji y no pasa de ~65 caracteres;
  * la pagina manda: el sitemap se arma desde los archivos, con su fecha real de cambio.
"""
import glob, html, os, re, subprocess, sys
from datetime import datetime, timedelta, timezone

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(RAIZ)
SITIO = 'https://masterprops.ai'
MAX_TITULO = 65

BANDERAS = {'argentina': '🇦🇷', 'bolivia': '🇧🇴', 'chile': '🇨🇱', 'colombia': '🇨🇴', 'ecuador': '🇪🇨', 'espana': '🇪🇸',
            'mexico': '🇲🇽', 'paraguay': '🇵🇾', 'peru': '🇵🇪', 'uruguay': '🇺🇾', 'venezuela': '🇻🇪'}
EMOJI = [('kelly', '🧮'), ('glosario', '📖'), ('odds-api', '🔌'), ('pinnacle', '🎯'), ('sharp', '🎯'), ('edge', '📐'),
         ('billete', '🎟️'), ('combinada', '🎟️'), ('ganar-dinero', '💰'), ('ganan-dinero', '💰'),
         ('rentables', '📈'), ('metodo', '🧠'), ('apostar-y-ganar', '🧠')]

# Grupos tematicos para "Segui leyendo": 2 del mismo grupo + 1 del grupo siguiente
GRUPOS = [
    ['apostar-y-ganar-metodo-matematico-real', 'apuestas-que-ganan-dinero-edge-real',
     'apuestas-rentables-2026-combinadas-valor', 'como-ganar-dinero-apuestas-deportivas-2026',
     'metodos-ganar-apuestas-deportivas-ia'],
    ['que-es-billete-largo-parlay-2026', 'como-armar-combinada-x10-valor-matematico',
     'combinadas-que-pagan-mucho-armar-billete-largo', 'kelly-criterion-parlay-billetes-largos',
     'glosario-mercados-props-bets'],
    ['pinnacle-vs-casas-latinas-sharp-odds', 'sharp-odds-como-identificarlas-aprovecharlas',
     'edge-apuestas-deportivas-secreto-matematico', 'the-odds-api-vs-casas-cuando-conviene'],
    ['usar-forebet-desde-' + p for p in BANDERAS],
]


def notas():
    return sorted(f for f in glob.glob('blog/*.html') if not f.endswith('index.html'))


def slug(f):
    return os.path.basename(f)[:-5]


def url(f):
    if f == 'index.html':
        return SITIO + '/'
    if f == 'blog/index.html':
        return SITIO + '/blog/'
    return f"{SITIO}/{f[:-5]}"


def emoji_de(f):
    s = slug(f)
    if f == 'index.html':
        return '💰'
    if f == 'blog/index.html':
        return '📚'
    for pais, b in BANDERAS.items():
        if s.endswith('-' + pais):
            return b
    for k, e in EMOJI:
        if k in s:
            return e
    return '🎯'


def empieza_con_emoji(t):
    return bool(t) and ord(t[0]) > 0x2000


def titulo_nuevo(f, t):
    t = html.unescape(t).strip()
    if f == 'blog/index.html':
        return '📚 Blog MasterProps — Guías de Apuestas y Billetes Largos'
    if empieza_con_emoji(t):
        e = emoji_de(f)
        if t.startswith(e) and e in t[len(e):]:           # bandera repetida en el medio
            t = e + re.sub(r'\s*' + re.escape(e) + r'\s*', ' ', t[len(e):]).rstrip()
        return re.sub(r'\s{2,}', ' ', t)
    base = t
    if len(emoji_de(f) + ' ' + base) > MAX_TITULO:
        base = re.sub(r'\s*[|—-]\s*MasterProps\s*$', '', base)
    if len(emoji_de(f) + ' ' + base) > MAX_TITULO and ':' in base:
        # "Tema: bajada larga" -> se conserva el tema, que es lo que se busca
        cabeza, cola = base.split(':', 1)
        palabras, corto = cola.split(), cabeza + ':'
        for w in palabras:
            if len(emoji_de(f) + ' ' + corto + ' ' + w) > MAX_TITULO:
                break
            corto += ' ' + w
        base = corto.rstrip(' :,') if corto.rstrip() != cabeza + ':' else cabeza
        base = re.sub(r'\s+(de|del|la|el|los|las|que|con|y|un|una|al|en|por|para)$', '', base)
    return f"{emoji_de(f)} {base}"


def titulos():
    n = 0
    for f in ['index.html', 'template.html', 'blog/index.html'] + notas():
        s = open(f, encoding='utf-8').read()
        m = re.search(r'<title>(.*?)</title>', s, re.S)
        if not m:
            continue
        viejo = m.group(1)
        nuevo = titulo_nuevo('index.html' if f == 'template.html' else f, viejo)
        if html.unescape(viejo).strip() == nuevo:
            continue
        esc = html.escape(nuevo, quote=True)
        s2 = s.replace(f'<title>{viejo}</title>', f'<title>{html.escape(nuevo, quote=False)}</title>', 1)
        for attr in ('property="og:title"', 'name="twitter:title"'):
            s2 = re.sub(r'(<meta ' + attr + r' content=")' + re.escape(viejo) + '(")', lambda k: k.group(1) + esc + k.group(2), s2)
        open(f, 'w', encoding='utf-8').write(s2)
        n += 1
        print(f"  titulo {len(nuevo):2d}  {nuevo}")
    return n


def titulo_visible(f):
    s = open(f, encoding='utf-8').read()
    m = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
    return re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else slug(f)


def relacionadas():
    n = 0
    existen = {slug(f): f for f in notas()}
    for gi, grupo in enumerate(GRUPOS):
        grupo = [g for g in grupo if g in existen]
        otro = [g for g in GRUPOS[(gi + 1) % len(GRUPOS)] if g in existen]
        for i, s_ in enumerate(grupo):
            f = existen[s_]
            elegidas = [grupo[(i + 1) % len(grupo)], grupo[(i + 2) % len(grupo)], otro[i % len(otro)]]
            elegidas = [e for j, e in enumerate(elegidas) if e != s_ and e not in elegidas[:j]]
            items = ''.join(f'<li><a style="color:#f0c850;text-decoration:underline" href="/blog/{e}">{html.escape(titulo_visible(existen[e]), quote=False)}</a></li>' for e in elegidas)
            bloque = ('<!-- mp-rel -->\n<nav class="mp-rel" aria-label="Seguí leyendo" style="margin:34px 0 8px;padding:18px 20px;'
                      'border:1px solid rgba(212,165,32,.25);border-radius:14px;background:rgba(255,255,255,.03)">\n'
                      '<h2 style="font-size:1.05rem;margin:0 0 10px;color:#f0c850">📚 Seguí leyendo</h2>\n'
                      f'<ul style="margin:0;padding-left:20px;line-height:1.9">{items}</ul>\n'
                      '<p style="margin:12px 0 0"><a style="color:#f0c850;text-decoration:underline" href="/blog/">Ver todas las guías del blog →</a></p>\n</nav>\n<!-- /mp-rel -->\n')
            s = open(f, encoding='utf-8').read()
            if '<!-- mp-rel -->' in s:
                s2 = re.sub(r'<!-- mp-rel -->.*?<!-- /mp-rel -->\n?', lambda _: bloque, s, flags=re.S)
            else:
                i2 = s.rfind('</article>')
                s2 = s[:i2] + bloque + s[i2:]
            if s2 != s:
                open(f, 'w', encoding='utf-8').write(s2)
                n += 1
    return n


def enlace_blog_home():
    n = 0
    for f in ('template.html', 'index.html'):
        s = open(f, encoding='utf-8').read()
        o = s
        a = '    <a href="#" class="active">Billetes</a>\n'
        if 'href="/blog/"' not in s and a in s:
            s = s.replace(a, a + '    <a href="/blog/">📚 Blog</a>\n', 1)
            b = '<a href="https://gambeta.ai">⚽ Gambeta</a> · <a href="#">🎯 MasterProps</a>'
            s = s.replace(b, '<a href="/blog/">📚 Blog</a> · ' + b, 1)
        if s != o:
            open(f, 'w', encoding='utf-8').write(s)
            n += 1
    return n


def fecha_git(f):
    try:
        out = subprocess.check_output(['git', 'log', '-1', '--format=%cs', '--', f], text=True).strip()
        sucio = subprocess.check_output(['git', 'status', '--porcelain', '--', f], text=True).strip()
        if out and not sucio:
            return out
    except Exception:
        pass
    return hoy()


def hoy():
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date().isoformat()


def sitemap(solo_home=False):
    """solo_home: lo usa el workflow diario (checkout sin historial git): mueve la fecha de
    la home y conserva la que ya tenia cada nota."""
    previas = {}
    if solo_home and os.path.exists('sitemap.xml'):
        previas = dict(re.findall(r'<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>', open('sitemap.xml', encoding='utf-8').read()))
    fecha = (lambda f: previas.get(url(f), hoy())) if solo_home else fecha_git
    filas = [('index.html', hoy(), 'daily', '1.0'), ('blog/index.html', fecha('blog/index.html'), 'weekly', '0.9')]
    filas += [(f, fecha(f), 'monthly', '0.8') for f in notas()]
    filas += [(f, fecha(f), 'yearly', '0.3') for f in ('contacto.html', 'terminos.html') if os.path.exists(f)]
    x = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for f, mod, freq, pri in filas:
        x += ['  <url>', f'    <loc>{url(f)}</loc>', f'    <lastmod>{mod}</lastmod>',
              f'    <changefreq>{freq}</changefreq>', f'    <priority>{pri}</priority>', '  </url>']
    x.append('</urlset>')
    nuevo = '\n'.join(x) + '\n'
    viejo = open('sitemap.xml', encoding='utf-8').read() if os.path.exists('sitemap.xml') else ''
    if nuevo != viejo:
        open('sitemap.xml', 'w', encoding='utf-8').write(nuevo)
    return len(filas)


if __name__ == '__main__':
    if '--sitemap' not in sys.argv:
        print('titulos cambiados:', titulos())
        print('notas con "Seguí leyendo":', relacionadas())
        print('home con enlace al blog:', enlace_blog_home())
    print('sitemap:', sitemap(solo_home='--sitemap' in sys.argv), 'urls')
