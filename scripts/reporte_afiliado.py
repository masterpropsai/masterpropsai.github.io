#!/usr/bin/env python3
"""Reporte de afiliado por SubID (API "GetPostbackSubId" del sistema de partners de la casa).

Dice, por idioma y por boton, cuantos clics, registros, primeros depositos y comision trajo
MasterProps. SE CORRE SOLO EN LA MAC: el repo y sus Actions son publicos y esto son numeros de
plata; el script no guarda nada en el repo, solo imprime.

Necesita tres variables de entorno (las define Mauro en su Mac, nunca en el repo ni en el chat):
    AFF_API_DOMAIN   dominio del panel de partners (por defecto partnersdbbet.com, verificado el
                     27-nov-2026: la API responde ahi; el PDF pone "domain.com" de ejemplo)
    AFF_API_TOKEN    token del gabinete de afiliado
    AFF_MERCHANT_ID  moneda del reporte: 3 = rublos, 6 = dolares (por defecto 6)

Uso:
    python scripts/reporte_afiliado.py            # ultimos 7 dias
    python scripts/reporte_afiliado.py 1          # ayer
    python scripts/reporte_afiliado.py 30         # ultimos 30 dias
NO PROBADO contra la API real (27-nov-2026): se escribio desde el PDF, falta token y dominio."""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

IDIOMAS = ['es', 'en', 'pt', 'it', 'fr', 'ru']
LUGARES = {'top': 'barra de arriba', 'hero': 'boton del inicio', 'cta': 'cartel del medio', 'cupon': 'boton Apostar (cupon)',
           'pie': 'pie', 'otro': 'otros'}
SUELTOS = {'mpcupon': 'cupon sin idioma', 'mplegal': 'pagina de terminos', '': 'sin SubID (sin JavaScript o links viejos)'}


def pedir(dominio, token, merchant, ini, fin, subid):
    q = urllib.parse.urlencode({'token': token, 'MerchantId': merchant, 'dateStart': ini, 'dateEnd': fin, 'subid': subid})
    req = urllib.request.Request(f'https://{dominio}/API/GetPostbackSubId?{q}', headers={'User-Agent': 'reporte'})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.loads(r.read().decode())
    if isinstance(d, str):                      # ej. "The token parameter is not correct."
        raise ValueError(d)
    return d[0] if isinstance(d, list) and d else (d if isinstance(d, dict) else {})


def main():
    dominio = os.environ.get('AFF_API_DOMAIN', '').strip() or 'partnersdbbet.com'
    token = os.environ.get('AFF_API_TOKEN', '').strip()
    if not token:
        print('Falta AFF_API_TOKEN (ver el comentario al principio del archivo).')
        return 2
    merchant = os.environ.get('AFF_MERCHANT_ID', '6')
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    hoy = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    ini, fin = int((hoy - timedelta(days=dias)).timestamp()), int(hoy.timestamp()) - 1
    subs = [(f'mp{l}{k}', f'{l} · {v}') for l in IDIOMAS for k, v in LUGARES.items()] + list(SUELTOS.items())
    print(f'Ultimos {dias} dia(s), hasta ayer (UTC). Moneda {merchant}.\n')
    print(f"{'origen':38s} {'clics':>6s} {'regs':>5s} {'1er dep':>7s} {'depositos':>10s} {'comision':>9s}")
    tot = [0, 0, 0, 0.0, 0.0]
    por_idioma = {}
    for sub, nombre in subs:
        try:
            d = pedir(dominio, token, merchant, ini, fin, sub)
        except ValueError as e:
            print(f'La API contesto: {e}\nRevisa el token (se saca del panel de partners).')
            return 1
        except Exception as e:
            print(f'{nombre:38s} error: {type(e).__name__}')
            continue
        fila = [d.get('DirectLink', 0) or 0, d.get('Regs', 0) or 0, d.get('Countftd', 0) or 0,
                float(d.get('SumDep', 0) or 0), float(d.get('ItogComission', d.get('ItogCommission', 0)) or 0)]
        if any(fila):
            print(f'{nombre:38s} {fila[0]:6d} {fila[1]:5d} {fila[2]:7d} {fila[3]:10.2f} {fila[4]:9.2f}')
        tot = [a + b for a, b in zip(tot, fila)]
        if sub[2:4] in IDIOMAS and sub.startswith('mp'):
            p = por_idioma.setdefault(sub[2:4], [0, 0, 0, 0.0, 0.0])
            por_idioma[sub[2:4]] = [a + b for a, b in zip(p, fila)]
        time.sleep(0.3)
    print('\nPor idioma:')
    for l, f in por_idioma.items():
        print(f'{l:38s} {f[0]:6d} {f[1]:5d} {f[2]:7d} {f[3]:10.2f} {f[4]:9.2f}')
    print(f"\n{'TOTAL':38s} {tot[0]:6d} {tot[1]:5d} {tot[2]:7d} {tot[3]:10.2f} {tot[4]:9.2f}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
