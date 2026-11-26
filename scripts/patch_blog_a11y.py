#!/usr/bin/env python3
"""Accesibilidad del blog (26-nov-2026): <main>, pie como landmark, tarjetas con nombre,
links del texto subrayados. Idempotente."""
import glob, html, re

CSS = "\n/* a11y */\n.crumb a, .footer a, .container p a, .container li a, .hero-blog a { text-decoration: underline; }\n"
for fn in sorted(glob.glob('blog/*.html')):
    s = o = open(fn, encoding='utf-8').read()
    if '<main' not in s:
        if '<article class="container">' in s:
            s = s.replace('<article class="container">', '<main>\n<article class="container">', 1)
            i = s.rfind('</article>')
            s = s[:i] + '</article>\n</main>' + s[i + len('</article>'):]
        elif '<section class="hero-blog">' in s:
            s = s.replace('<section class="hero-blog">', '<main>\n<section class="hero-blog">', 1)
            i = s.find('<div class="footer"')
            s = s[:i] + '</main>\n' + s[i:]
    s = s.replace('<div class="footer">', '<div class="footer" role="contentinfo">')
    def nombre(m):
        t = re.search(r'<h2 class="card-title">(.*?)</h2>', m.group(0), re.S)
        lab = html.escape(re.sub(r'<[^>]+>', '', t.group(1)).strip(), quote=True) if t else 'Leer la nota'
        return m.group(0).replace('class="card-link"></a>', f'class="card-link" aria-label="{lab}"></a>', 1)
    s = re.sub(r'<article class="card">.*?</article>', nombre, s, flags=re.S)
    if '/* a11y */' not in s and '</style>' in s:
        i = s.find('</style>')
        s = s[:i] + CSS + s[i:]
    if s != o:
        open(fn, 'w', encoding='utf-8').write(s)
        print('ok', fn)
