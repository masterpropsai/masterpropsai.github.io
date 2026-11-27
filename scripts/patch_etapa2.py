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
    # 9) Estados que aparecen cuando hay resultados (27-nov): rojo sobre rojo oscuro no llegaba
    #    a 4,5:1 y el billete perdido se atenuaba con opacity .55 (texto ilegible).
    if '/* a11y estados */' not in s:
        css = """
/* a11y estados */
.ticket-heat-badge.fire, .ticket-result-badge.lost { color: #ff9a9a; }
.ticket-heat-badge.hot { color: #ffa25c; }
.ticket.ticket-dead { opacity: .88; filter: grayscale(.55); }
.ticket.ticket-dead:hover { opacity: 1; }
"""
        i = s.rfind('</style>', 0, s.find('<body'))
        s = s[:i] + css + s[i:]
        log.append('css estados')
    # 10) "Pronosticos Gambeta.ai · EN VIVO" mostraba 4 picks FIJOS del Mundial (Francia-Noruega,
    #     "Gana España") como si fueran de hoy (27-nov). Se oculta y se vacia la lista.
    a = '<div class="gambeta-picks-section" id="gambeta-picks-section">'
    if a in s:
        s = s.replace(a, '<div class="gambeta-picks-section" id="gambeta-picks-section" hidden style="display:none">')
        s = re.sub(r"const GAMBETA_PICKS = \[.*?\n\];", "const GAMBETA_PICKS = [];", s, count=1, flags=re.S)
        log.append('picks fijos del Mundial fuera')
    # 11) El billete perdido se atenuaba con opacity: el texto chico caia a 4,2:1. Se marca
    #     solo con escala de grises (no baja el contraste del texto).
    if '/* a11y estados 3 */' not in s:
        css = """
/* a11y estados 3 */
.ticket.ticket-dead, .ticket.ticket-dead:hover { opacity: 1; filter: grayscale(.75); }
.conf-label { color: #b0aa9c; opacity: 1; }
"""
        i = s.rfind('</style>', 0, s.find('<body'))
        s = s[:i] + css + s[i:]
        log.append('css estados 2')
    # 12) Con 50+ billetes la entrada escalonada (0,08 s por billete) tardaba mas de 4 s:
    #     los ultimos seguian semitransparentes un buen rato. Tope de 0,6 s.
    a = 'style="animation-delay: ${i * 0.08}s"'
    if a in s:
        s = s.replace(a, 'style="animation-delay: ${Math.min(i * 0.05, 0.6)}s"')
        log.append('tope de animacion')
    return s, log

for fn in ('template.html', 'index.html'):
    s = open(fn, encoding='utf-8').read()
    s2, log = patch(s)
    open(fn, 'w', encoding='utf-8').write(s2)
    print(fn, len(s), '->', len(s2), log)
