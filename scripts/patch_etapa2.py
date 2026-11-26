#!/usr/bin/env python3
"""Etapa 2 (26-nov-2026): limpieza de restos del Mundial + accesibilidad en la home.
Se aplica igual a template.html (molde del generador) y a index.html. Idempotente."""
import re, sys

def sub1(s, a, b, n=1):
    if a not in s:
        return s, False
    return s.replace(a, b, n), True

def patch(s):
    log = []
    # 1) Banner "Partidos del dia" del Mundial (seccion + script + estilos): mostraba Francia-Noruega en noviembre
    i = s.find('<!-- BANNER PARTIDOS DEL DÍA')
    if i >= 0:
        j = s.find('<div class="hero">', i)
        k = s.rfind('</style>', i, j)
        assert j > i and k > i
        s = s[:i] + s[k + len('</style>'):].lstrip('\n')
        s = s.replace('<div class="hero">', '<div class="hero">', 1)
        log.append('banner mundial fuera')
    # 2) Dropshot AI: el sitio enlazado da 404
    i = s.find('<!-- DROPSHOT AI -->')
    if i >= 0:
        j = s.find('<div id="gambeta-crosspromo"', i)
        k = s.rfind('</div>', i, j)
        s = s[:i] + s[k + len('</div>'):].lstrip('\n')
        log.append('dropshot fuera')
    # 3) Textos y campañas del Mundial
    for a, b in [
        ('<p>Picks del Mundial 2026 · Análisis IA en tiempo real</p>', '<p>Picks de fútbol de hoy · Análisis IA en tiempo real</p>'),
        ('utm_campaign=mundial2026', 'utm_campaign=masterprops'),
    ]:
        if a in s:
            s = s.replace(a, b); log.append('texto: ' + a[:30])
    # 4) Landmarks: main + footer + sponsor
    if '<main id="contenido">' not in s:
        s, ok1 = sub1(s, '<div class="hero">', '<main id="contenido">\n<div class="hero">')
        s, ok2 = sub1(s, '<div class="footer">', '</main>\n<div class="footer" role="contentinfo">')
        assert ok1 and ok2
        log.append('main + footer')
    s, ok = sub1(s, '<div class="sponsor-bar">', '<div class="sponsor-bar" role="complementary" aria-label="Sponsor">')
    if ok: log.append('sponsor landmark')
    # 5) Nombres accesibles
    for sid, lab in [('sportFilter', 'Deporte'), ('tierFilter', 'Categoría'), ('statusFilter', 'Estado'),
                     ('confFilter', 'Confianza'), ('sortFilter', 'Orden')]:
        s, ok = sub1(s, f'<select class="filter-dropdown" id="{sid}">', f'<select class="filter-dropdown" id="{sid}" aria-label="{lab}">')
        if ok: log.append('select ' + sid)
    n = s.count('class="db-logo">')
    if n:
        s = s.replace('class="db-logo">', 'class="db-logo" aria-label="DBbet">'); log.append(f'db-logo x{n}')
    # 6) Jerarquia de titulos
    if '<h3>PRONÓSTICOS GAMBETA.AI</h3>' in s:
        s = s.replace('<h3>PRONÓSTICOS GAMBETA.AI</h3>', '<h2>PRONÓSTICOS GAMBETA.AI</h2>')
        s = s.replace('.gp-header-text h3 {', '.gp-header-text h2, .gp-header-text h3 {')
        log.append('h3->h2 gambeta')
    # 7) Contraste (WCAG AA 4,5:1)
    if '/* a11y etapa 2 */' not in s:
        css = """
/* a11y etapa 2 */
.leg-odd { color: #7a5600; }
.sponsor-bar .db-register { background: #d6173f; }
.last-updated { color: #a8a294; opacity: 1; }
"""
        i = s.rfind('</style>', 0, s.find('<body'))
        s = s[:i] + css + s[i:]
        log.append('css contraste')
    # 8) Botones de Telegram/YouTube: blanco sobre verde/rojo claro no llegaba a 4,5:1
    for a, b in [('background:#22c55e;color:#fff;', 'background:#15803d;color:#fff;'),
                 ('background:#ef4444;color:#fff;', 'background:#dc2626;color:#fff;')]:
        if a in s:
            s = s.replace(a, b); log.append('boton ' + b[11:18])
    a = 'target="_blank" style="display:inline-flex;align-items:center;vertical-align:middle"><svg'
    if a in s:
        s = s.replace(a, a.replace('><svg', ' aria-label="DBbet"><svg')); log.append('logo pie')
    return s, log

for fn in ('template.html', 'index.html'):
    s = open(fn, encoding='utf-8').read()
    s2, log = patch(s)
    open(fn, 'w', encoding='utf-8').write(s2)
    print(fn, len(s), '->', len(s2), log)
