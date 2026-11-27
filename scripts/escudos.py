#!/usr/bin/env python3
"""Escudo de un equipo segun el mapa de gambeta.ai (data/escudos_gambeta.json).

Cruce ESTRICTO, a proposito: nombre igual (sin acentos ni mayusculas) o, si no, la forma
corta sin "FC", "1.", etc. SOLO cuando esa forma corta apunta a un unico escudo. Nada de
parecidos ni prefijos: en gambeta.ai un cruce por prefijo mando Independiente Rivadavia al
escudo de Independiente. Sin certeza -> None y queda el logo de la casa."""
import json, os, re, unicodedata

_RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'escudos_gambeta.json')
_RUIDO = {'fc', 'cf', 'ac', 'sc', 'afc', 'sv', 'cd', 'ca', 'fk', 'sk', 'as', 'ss', 'us', 'ud', 'rc', 'rcd', 'cs', 'ec',
          'se', 'cr', 'bk', 'nk', 'if', 'vfl', 'vfb', 'tsg', 'bsc', 'club', 'calcio', 'acs', 'kv', 'kaa', 'krc', 'ogc'}
_mapa = None
_memo = {}

# Nombres del feed de la casa que gambeta.ai guarda con otro nombre. Solo equivalencias
# seguras y verificadas una por una; el destino tiene que existir en el mapa
# (scripts/test_escudos.py lo exige). El alias "de verdad" se agrega en gambeta.ai.
ALIAS = {
    'Oud-Heverlee Leuven': 'OH Leuven', 'Unione Venezia': 'Venezia', 'Lille OSC': 'Lille',
    'Inter de Milán': 'Inter Milan', 'Atlas Guadalajara': 'Atlas', 'CA Independiente Avellaneda': 'Independiente',
    'Deportivo Toluca': 'Toluca', 'Zenit Saint Petersburg': 'Zenit St Petersburg',
    'Vitoria Guimaraes': 'Vitoria de Guimaraes', 'K.V.C. Westerlo': 'KVC Westerlo',
    'Deportes La Serena': 'La Serena', 'Nott. Forest': 'Nottingham Forest',
}
_ALIAS_N = None


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.sub(r"[^a-z0-9 ]", ' ', s.replace('.', ' ').replace("'", '')).split())


def reducir(s):
    """'1. FC Heidenheim 1846' -> 'heidenheim' ; 'Darmstadt 98' -> 'darmstadt'."""
    w = [x for x in norm(s).split() if x not in _RUIDO and not x.isdigit()]
    return ' '.join(w)


def _cargar():
    global _mapa
    if _mapa is None:
        try:
            _mapa = json.load(open(_RUTA, encoding='utf-8'))
        except Exception:
            _mapa = {'exacto': {}, 'reducido': {}}
    return _mapa


def _contexto(nombre, liga):
    """Mismos casos que crest() de gambeta.ai: nombres que son otro club segun la liga."""
    c, n = (liga or '').lower(), norm(nombre)
    if n == 'barcelona' and re.search(r'conmebol|libertadores|sudamericana|ecuador', c):
        return 'Barcelona SC'
    if n == 'nacional' and re.search(r'portugal|primeira', c):
        return 'Nacional Madeira'
    if n == 'andorra' and re.search(r'spain|espana|segunda|primera|laliga|la liga|andorra', c):
        return 'FC Andorra'
    return nombre


def escudo(nombres, liga=''):
    """nombres: una o varias formas del mismo equipo (la del feed y la que se muestra).
    -> URL del escudo o None."""
    global _ALIAS_N
    m = _cargar()
    if isinstance(nombres, str):
        nombres = [nombres]
    clave = (tuple(nombres), liga)
    if clave in _memo:
        return _memo[clave]
    if _ALIAS_N is None:
        _ALIAS_N = {norm(k): v for k, v in ALIAS.items()}
    nombres = [_ALIAS_N.get(norm(n), n) for n in nombres if n]
    nombres = [_contexto(n, liga) for n in nombres]
    _memo[clave] = u = _buscar(m, nombres)
    return u


def _buscar(m, nombres):
    for n in nombres:
        u = m['exacto'].get(norm(n))
        if u:
            return u
    for n in nombres:
        r = reducir(n)
        u = m['exacto'].get(r) or m['reducido'].get(r)
        if u and len(r) >= 4:
            return u
    return None
