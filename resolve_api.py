#!/usr/bin/env python3
"""
resolve_api.py - Resuelve picks de MasterProps automaticamente con The Odds API /scores.
La API key se lee de ODDS_API_KEY (no se hardcodea; repo publico).
Solo resuelve con marcador FINAL (completed). Props de HT / proximo gol -> quedan pendientes.
"""
import json, os, sys, re, subprocess, urllib.request, unicodedata
from datetime import datetime, timezone

API_KEY = os.environ.get("ODDS_API_KEY", "").strip()
BASE = "https://api.the-odds-api.com/v4"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

def _norm(s):
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode().lower()
    s = re.sub(r"\b(fc|cf|ac|sc|cd|ca|afc|sv|club|deportivo|atletico|cs|ec|u)\b"," ",s)
    s = re.sub(r"\(women\)|\(w\)|women|femenino|u20|u23|u19"," ",s)
    s = re.sub(r"[^a-z0-9 ]"," ",s)
    s = re.sub(r"\s+"," ",s).strip()
    return s

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"MasterProps Resolver"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode()), r.headers

def main():
    if not API_KEY:
        print(json.dumps({"error":"ODDS_API_KEY no seteada"})); sys.exit(1)
    pend = json.loads(subprocess.check_output([sys.executable, os.path.join(REPO_DIR,"auto_resolve.py"), "--pending"]).decode())
    matches = pend["matches"]
    sports,_ = fetch(f"{BASE}/sports/?apiKey={API_KEY}")
    keys = [s["key"] for s in sports if s.get("active")]
    index = {}; quota=None
    for k in keys:
        try:
            evs, hdr = fetch(f"{BASE}/sports/{k}/scores/?apiKey={API_KEY}&daysFrom=3")
            quota = hdr.get("x-requests-remaining", quota)
        except Exception:
            continue
        for e in evs:
            if not e.get("completed"): continue
            sc = e.get("scores") or []
            if len(sc) < 2: continue
            sm = {x["name"]: x.get("score") for x in sc}
            h,a = e.get("home_team"), e.get("away_team")
            try: hg=int(sm.get(h)); ag=int(sm.get(a))
            except (TypeError,ValueError): continue
            rec={"home":h,"away":a,"hg":hg,"ag":ag}
            for nm in (h,a): index.setdefault(_norm(nm),[]).append(rec)
    results=[]; resolved=[]; skipped=[]
    for m in matches:
        ln=m["local_name"]; n=_norm(ln); cands=index.get(n,[])
        rec = cands[0] if cands else None
        if not rec:
            skipped.append(ln); continue
        if _norm(rec["home"])==n: lg,vg=rec["hg"],rec["ag"]
        elif _norm(rec["away"])==n: lg,vg=rec["ag"],rec["hg"]
        else: lg,vg=rec["hg"],rec["ag"]
        results.append({"local_name":ln,"local_goals":lg,"visitor_goals":vg,"ht_local":0,"ht_visitor":0,"goal_scorers":[]})
        resolved.append("%s %d-%d"%(ln,lg,vg))
    payload={"batch_label":"AUTO-API "+datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),"match_results":results}
    if results:
        p=subprocess.run([sys.executable, os.path.join(REPO_DIR,"auto_resolve.py"),"--resolve"], input=json.dumps(payload).encode(), capture_output=True)
        try: res=json.loads(p.stdout.decode())
        except Exception: res={"raw":p.stdout.decode(),"err":p.stderr.decode()}
    else:
        res={"status":"nothing_resolved"}
    print(json.dumps({"quota_remaining":quota,"matches_with_score":len(results),"matches_skipped_no_score":len(skipped),"resolve_result":res,"resolved_sample":resolved[:50],"skipped_sample":skipped[:40]}, ensure_ascii=False, indent=2))

if __name__=="__main__":
    main()
