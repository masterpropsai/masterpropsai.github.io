#!/usr/bin/env python3
"""MasterProps stage 2/2 — generate DBbet coupon (booking) codes and bake them in.
Reads tickets_data.json, calls the public DBbet SaveCoupon endpoint concurrently
(with retries), writes coupons.json, and injects each code into index.html and
template.html. No credentials needed (public share-slip endpoint).
"""
import json, re, time, requests, concurrent.futures
from pathlib import Path

REPO = Path(__file__).parent
TD = json.loads((REPO / 'tickets_data.json').read_text(encoding='utf-8'))

URL = 'https://db-bet.com/service-api/LiveBet/Open/SaveCoupon'
HDR = {
    'content-type': 'application/json',
    'accept': 'application/json, text/plain, */*',
    'origin': 'https://db-bet.com',
    'referer': 'https://db-bet.com/es',
}

def _body(events):
    return {
        'notWait': True, 'CheckCf': 1, 'partner': 164,
        'AntiExpressCoef': 2, 'Summ': 100,
        'Events': [{
            'GameId': e['GameId'], 'Type': e['Type'], 'Coef': e['Coef'],
            'Param': e.get('Param', 0), 'PV': None,
            'PlayerId': e.get('PlayerId', 0), 'Kind': 3,
            'InstrumentId': 0, 'Seconds': 0, 'Price': 0,
            'Expired': 0, 'PlayersDuel': [],
        } for e in events],
        'Vid': 0,
    }

def _gen(td):
    tid = td['ticket_id']
    body = _body(td['events'])
    last = 'unknown'
    for _ in range(4):
        try:
            r = requests.post(URL, json=body, headers=HDR, timeout=8)
            res = r.json()
            if res.get('Success') and res.get('Value'):
                return tid, res['Value']
            last = res.get('Error', 'unknown')
        except Exception as e:
            last = type(e).__name__
        time.sleep(1.0)
    print(f'   warn {tid}: {last}')
    return tid, None

codes = {}
t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    for tid, code in ex.map(_gen, TD):
        if code:
            codes[tid] = code

# Fallback: keep any prior code for tickets that failed this run
cf = REPO / 'coupons.json'
if cf.exists():
    try:
        for tid, code in json.loads(cf.read_text(encoding='utf-8')).items():
            if code and tid not in codes:
                codes[tid] = code
    except Exception:
        pass

cf.write_text(json.dumps(codes, indent=2), encoding='utf-8')

for fn in ('index.html', 'template.html'):
    p = REPO / fn
    txt = p.read_text(encoding='utf-8')
    for tid, code in codes.items():
        txt = re.compile(r"(id:'" + re.escape(tid) + r"',[^\n]*?couponCode:')[^']*(')").sub(
            lambda m: m.group(1) + code + m.group(2), txt)
    p.write_text(txt, encoding='utf-8')

print('mp_publish_coupons OK: %d/%d codes in %.1fs' % (len(codes), len(TD), time.time() - t0))
