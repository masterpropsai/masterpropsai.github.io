#!/usr/bin/env python3
"""Extrae de template.html todos los textos en español que hay que traducir -> i18n/es.json

Unidades (cada una con id estable = hash del texto fuente):
  html : contenido de un elemento cuyo interior es solo texto + etiquetas en linea
         (se traduce la frase ENTERA con sus <strong>, no pedacitos sueltos)
  attr : aria-label / title / placeholder / alt
  key  : valores del bloque I18N.es del JavaScript (rotulos que arma el codigo)
  js   : literales sueltos del JavaScript, listados a mano en JS_SUELTOS
  prop : plantillas de las selecciones ("Menos de {n} goles de {team}")
  meta : title / description de la pagina

Uso: python scripts/i18n_extract.py   (no pisa traducciones: solo reescribe es.json)
"""
import hashlib, json, os, re
from html.parser import HTMLParser

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
INLINE = {'strong', 'b', 'em', 'i', 'span', 'br', 'u', 'small', 'sup', 'sub', 'a', 'img', 'svg', 'path'}
SALTAR = {'script', 'style', 'svg', 'select'}          # select: se toman sus <option> una por una
LETRAS = re.compile(r'[A-Za-zÁÉÍÓÚÑáéíóúñ]{3}')
NO_TRADUCIR = re.compile(r'^(DBbet|MasterProps|GAMBETA\.AI|MASTERPROPS|ROI|Hit rate|Track Record|YouTube.*|@\w+|[A-Z]{2}|'
                         r'Español|English|Português|Italiano|Français|Русский|tu@email\.com|\W*MASTERPROPS\W*|.*Gambeta\W*)$')

# Selecciones que hoy publica el generador (ver mp_diario.resoluble). {n} = linea, {team} = equipo
PROPS = {
    'prop.under_team': 'Menos de {n} goles de {team}',
    'prop.over_team': 'Más de {n} goles de {team}',
    'prop.under': 'Menos de {n} goles',
    'prop.over': 'Más de {n} goles',
    'prop.win': 'Gana {team}',
    'prop.win_over': '{team} Gana y Más de {n} goles',
    'prop.win_under': '{team} Gana y Menos de {n} goles',
    'prop.dc_over': '{team} No pierde y Más de {n} goles',
    'prop.dc_under': '{team} No pierde y Menos de {n} goles',
    'prop.next_goal': '{team} Anota próximo gol ({n})',
    'prop.next_goal_none': 'Ninguno Anota próximo gol ({n})',
    'prop.team_even': '{team} Total Par',
    'prop.team_odd': '{team} Total Impar',
    'prop.even': 'Total Par',
    'prop.odd': 'Total Impar',
    'prop.handicap': 'HÁ {team} {n}',
    'prop.race_none': 'Primero en ({n}) goles - Ninguno',
}

VIEJAS = set('overPts overAst overReb over3pt tripleDouble goalAnytime overGoals goalAndOver goalAndCard goalOrAssist overAssists winBySub koRound1 koAnyRound koRound3 winByDec winRounds12 winStraight overAces overGames overDF win20 overK hrYes overHW overYdPass overTDrush overYdRec anytimeTD'.split())

# Literales del JavaScript que se ven en pantalla y no pasan por I18N
JS_SUELTOS = [
    'Abrí el boleto', 'Código copiado al portapapeles', 'Tocá el código si necesitás copiarlo de nuevo',
    'Sin conexión. Probá más tarde.', 'no se pudo guardar', 'ENVIANDO...', 'RECIBIR BILLETES GRATIS',
    '✓ Listo. Revisá tu inbox.', '💰 ¡GANADOR! 🎉', '❌ PERDIDO', '🔄 SIN ACCIÓN', '▲ OCULTAR HISTORIAL',
    '— INFERNO', '— EN FUEGO', '— CALIENTE', '— VAMOS',
    '📜 VER HISTORIAL', 'Billetes ✅', 'Billetes ❌', 'Picks ✅', 'Picks ❌', 'Acierto picks',
    'Todavía no hay billetes resueltos — los billetes terminados se archivan acá automáticamente. ⏳',
]


def uid(tipo, src):
    return tipo + '.' + hashlib.sha1(src.encode('utf-8')).hexdigest()[:10]


class Unidades(HTMLParser):
    """Arma el arbol y elige como unidad el elemento MAS EXTERNO cuyo interior es solo texto +
    etiquetas en linea. Un contenedor sin texto propio y con varios hijos con texto no es
    unidad: lo son sus hijos (asi un menu no queda como una sola frase)."""

    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src, self.attrs = src, []
        self.raiz = {'tag': '#', 'hijos': [], 'directo': False, 'padre': None, 'ini': 0, 'fin': len(src)}
        self.cur = self.raiz
        self.lineas = [0]
        for l in src.split('\n'):
            self.lineas.append(self.lineas[-1] + len(l) + 1)

    def pos(self):
        l, c = self.getpos()
        return self.lineas[l - 1] + c

    def en_salto(self):
        n = self.cur
        while n:
            if n['tag'] in SALTAR - {'select'}:
                return True
            n = n['padre']
        return False

    def handle_starttag(self, tag, attrs):
        ini = self.pos()
        for k, v in attrs:
            if k in ('aria-label', 'title', 'placeholder', 'alt') and v and not self.en_salto():
                self.attrs.append(v)
        if tag in ('br', 'img', 'input', 'meta', 'link', 'path', 'hr'):
            self.cur['hijos'].append({'tag': tag, 'hijos': [], 'directo': False, 'padre': self.cur, 'vacio': True})
            return
        n = {'tag': tag, 'hijos': [], 'directo': False, 'padre': self.cur,
             'ini': ini + len(self.get_starttag_text()), 'fin': None}
        self.cur['hijos'].append(n)
        self.cur = n

    def handle_endtag(self, tag):
        n = self.cur
        while n and n['tag'] != tag:
            n = n['padre']
        if not n or n is self.raiz:
            return
        n['fin'] = self.pos()
        self.cur = n['padre']

    def handle_data(self, data):
        if LETRAS.search(data) and not self.en_salto():
            self.cur['directo'] = True

    # ── seleccion de unidades ──
    def _texto(self, n):
        return n['directo'] or any(self._texto(h) for h in n['hijos'])

    def _enlinea(self, n):
        return all(h['tag'] in INLINE and self._enlinea(h) for h in n['hijos'])

    def _es_unidad(self, n):
        if n.get('vacio') or n.get('fin') is None or n['tag'] in SALTAR or not self._texto(n) or not self._enlinea(n):
            return False
        return n['directo']        # sin texto propio: las unidades son sus hijos

    def unidades(self):
        out = []

        def baja(n, salto):
            salto = salto or n['tag'] in SALTAR - {'select'}
            if not salto and n is not self.raiz and self._es_unidad(n):
                out.append((n['ini'], n['fin'], n['tag']))
                return
            for h in n['hijos']:
                baja(h, salto)
        baja(self.raiz, False)
        return out


def extraer():
    h = open('template.html', encoding='utf-8').read()
    b0 = h.index('<body')
    body = h[b0:]
    u = Unidades(body)
    u.feed(body)
    unidades = {}

    def add(tipo, src, **extra):
        src = src.strip()
        if not src or NO_TRADUCIR.match(re.sub(r'<[^>]+>', '', src).strip()) or not LETRAS.search(re.sub(r'<[^>]+>', '', src)):
            return
        unidades.setdefault(uid(tipo, src), dict(tipo=tipo, es=src, **extra))

    for ini, fin, tag in u.unidades():
        inner = body[ini:fin]
        if '${' in inner or len(inner) > 1500:
            continue
        add('html', inner)
    for a in u.attrs:
        add('attr', a)

    m = re.search(r"const I18N = \{\s*es: \{(.*?)\n  \},", h, re.S)
    for k, v in re.findall(r"(\w+): '((?:[^'\\]|\\.)*)'", m.group(1)):
        if k in VIEJAS or k in ('copyBtn', 'copied'):
            continue                                    # props de jugador de otros deportes: ya no se publican
        unidades['key.' + k] = dict(tipo='key', es=v.replace("\\'", "'"))
    cl = re.search(r"confLevels: \['', (.*?)\]", m.group(1))
    unidades['key.confLevels'] = dict(tipo='key', es='|'.join(re.findall(r"'([^']*)'", cl.group(1))),
                                      nota='6 niveles de confianza separados por |, de menor a mayor')
    for s in JS_SUELTOS:
        add('js', s)
    for k, v in PROPS.items():
        unidades[k] = dict(tipo='prop', es=v)
    t = re.search(r'<title>(.*?)</title>', h, re.S).group(1)
    d = re.search(r'<meta name="description" content="(.*?)"', h, re.S).group(1)
    unidades['meta.title'] = dict(tipo='meta', es=t, nota='max 65 caracteres, empieza con el emoji')
    unidades['meta.description'] = dict(tipo='meta', es=d, nota='max 160 caracteres')
    return unidades


if __name__ == '__main__':
    un = extraer()
    os.makedirs('i18n', exist_ok=True)
    json.dump(un, open('i18n/es.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    import collections
    print(len(un), 'unidades', dict(collections.Counter(v['tipo'] for v in un.values())),
          '| palabras', sum(len(re.sub(r'<[^>]+>', ' ', v['es']).split()) for v in un.values()))
