#!/usr/bin/env python3
"""MasterProps stage 1/2 — build tickets + HTML, defer coupon codes.
Runs generate_live.main() but stubs the SaveCoupon network so the run finishes
well within the Cowork 45s shell budget. Coupon codes are filled in afterwards
by mp_publish_coupons.py. Writes index.html, template.html, tickets_data.json.
"""
import json, time
import generate_live as g

class _Resp:
    @staticmethod
    def json():
        return {'Success': False, 'Value': '', 'Error': 'deferred-to-mp_publish_coupons'}

# Defer coupon generation (filled by stage 2) and drop courtesy sleeps
g.requests.post = lambda *a, **k: _Resp()
time.sleep = lambda *a, **k: None

t0 = time.time()
g.main()
print('mp_build OK in %.1fs' % (time.time() - t0))
