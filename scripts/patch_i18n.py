#!/usr/bin/env python3
"""Prepara template.html e index.html para las paginas por idioma (27-nov-2026). Idempotente.
- Las banderitas pasan a ser enlaces reales (/, /en/, /pt/...): antes cambiaban ~30 palabras
  en el navegador y Google no veia ninguna version traducida.
- translateProp() traduce las selecciones de hoy con las plantillas que inyecta build_langs.
- hreflang entre todas las versiones."""
import re

LANGS = [('es', '', 'Español', 'ar', 'AR'), ('en', 'en/', 'English', 'us', 'US'), ('pt', 'pt/', 'Português', 'br', 'BR'),
         ('it', 'it/', 'Italiano', 'it', 'IT'), ('fr', 'fr/', 'Français', 'fr', 'FR'), ('ru', 'ru/', 'Русский', 'ru', 'RU')]
SITIO = 'https://masterprops.ai/'

PROP_JS = r"""
// === Selecciones por idioma (build_langs.py inyecta window.MP_PROPS = [[es, traduccion], ...]) ===
const MP_PROP_RE = (window.MP_PROPS || []).map(([es, tr]) => {
  const orden = [];
  const re = es.replace(/[.*+?^$()|[\]\\]/g, '\\$&').replace(/\{(team|n)\}/g, (_, k) => {
    orden.push(k);
    return k === 'team' ? '(.+?)' : '([-+]?\\d+(?:[.,]\\d+)?(?: - \\d+(?:[.,]\\d+)?)?)';
  });
  return { re: new RegExp('^' + re + '$'), tr, orden };
});
function mpTranslateProp(propEs) {
  for (const { re, tr, orden } of MP_PROP_RE) {
    const m = propEs.match(re);
    if (m) { let out = tr; orden.forEach((k, i) => { out = out.replace('{' + k + '}', m[i + 1]); }); return out; }
  }
  return null;
}
"""


def patch(s):
    log = []
    # a) banderitas -> enlaces
    if 'class="lang-flag" data-lang' in s or 'class="lang-flag active" data-lang' in s:
        i = s.index('<div class="lang-switcher">')
        j = s.index('</div>', i) + len('</div>')
        links = ''.join(
            f'\n    <a class="lang-flag{" active" if c == "es" else ""}" href="/{p}" hreflang="{c}" lang="{c}" title="{n}">'
            f'<img src="https://flagcdn.com/w40/{f}.png" width="20" height="15" alt="{n}"></a>'
            for c, p, n, f, a in LANGS)
        s = s[:i] + '<div class="lang-switcher">' + links + '\n  </div>' + s[j:]
        log.append('banderas -> enlaces')
    a = "    currentLang = flag.dataset.lang;\n"
    if a in s and 'if (!flag.dataset.lang) return;' not in s:
        s = s.replace("  flag.addEventListener('click', () => {\n", "  flag.addEventListener('click', () => {\n    if (!flag.dataset.lang) return;   // ahora son enlaces a /en/, /pt/...\n", 1)
        log.append('guard handler')
    # c) selecciones
    if 'function mpTranslateProp' not in s:
        a = "function translateProp(propEs) {\n"
        assert a in s
        s = s.replace(a, PROP_JS + "\n" + a + "  const _mp = mpTranslateProp(propEs);\n  if (_mp !== null) return _mp;\n", 1)
        log.append('translateProp')
    # d) historial
    a = '<div class="leg-detail">${l.prop} \\u00b7 ${l.match}'
    if a in s:
        s = s.replace(a, '<div class="leg-detail">${translateProp(l.prop)} \\u00b7 ${l.match}')
        log.append('historial traduce')
    # e) locale
    a = "const locale = currentLang === 'es' ?"
    if a in s:
        s = s.replace(a, "const locale = window.MP_LOCALE ? window.MP_LOCALE : currentLang === 'es' ?")
        log.append('locale')
    # f) rutas absolutas
    if '`./go.html?c=' in s:
        s = s.replace('`./go.html?c=', '`/go.html?c=')
        log.append('go.html absoluto')
    # g) hreflang
    bloque = '<!-- hreflang -->\n' + ''.join(f'<link rel="alternate" hreflang="{c}" href="{SITIO}{p}">\n' for c, p, *_ in LANGS) \
             + f'<link rel="alternate" hreflang="x-default" href="{SITIO}">\n<!-- /hreflang -->\n'
    if '<!-- hreflang -->' in s:
        s2 = re.sub(r'<!-- hreflang -->.*?<!-- /hreflang -->\n', lambda _: bloque, s, flags=re.S)
    else:
        m = re.search(r'<link rel="canonical"[^>]*>\n', s)
        s2 = s[:m.end()] + bloque + s[m.end():]
        log.append('hreflang')
    return s2, log


if __name__ == '__main__':
    for fn in ('template.html', 'index.html'):
        s = open(fn, encoding='utf-8').read()
        s2, log = patch(s)
        if s2 != s:
            open(fn, 'w', encoding='utf-8').write(s2)
        print(fn, log)
