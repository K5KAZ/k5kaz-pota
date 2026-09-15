#!/usr/bin/env python3

import json, os, re, sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote

CALL = os.environ.get("POTA_CALLSIGN","K5KAZ")
BASE = "https://api.pota.app"
OUT = "data/pota.json"

def get_json(url):
    req=Request(url,headers={"User-Agent":"K5KAZ-POTA-Site/1.0","Accept":"application/json"})
    with urlopen(req,timeout=30) as r:
        return json.load(r)

def num(v):
    try: return int(float(v))
    except: return None

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values(): yield from walk(v)
    elif isinstance(obj, list):
        for v in obj: yield from walk(v)

def first_num(obj, keys):
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and num(obj[k]) is not None: return num(obj[k])
    return None

def find_activation_rows(obj):
    candidates=[]
    for d in walk(obj):
        if not isinstance(d,dict): continue
        ref=d.get("reference") or d.get("parkReference") or d.get("park_ref") or d.get("ref")
        date=d.get("date") or d.get("activationDate") or d.get("activation_date") or d.get("qso_date")
        if ref and date:
            candidates.append({
                "reference":str(ref),
                "name":d.get("parkName") or d.get("name") or d.get("locationName") or str(ref),
                "date":str(date),
                "qsos":first_num(d,["qsos","qsoCount","totalQsos","total","contacts","count"]) or 0
            })
    seen=set(); out=[]
    for x in candidates:
        key=(x["reference"],x["date"])
        if key not in seen:
            seen.add(key); out.append(x)
    return out

def find_stat(obj, keys):
    for d in walk(obj):
        v=first_num(d,keys)
        if v is not None: return v
    return None

try:
    raw=get_json(f"{BASE}/stats/user/{quote(CALL)}")
except Exception as e:
    print("POTA stats fetch failed:",e,file=sys.stderr)
    sys.exit(1)

stats={
    "activations":find_stat(raw,["activations","activationCount","totalActivations","activatorActivations"]),
    "parks":find_stat(raw,["parks","parkCount","uniqueParks","uniqueParksActivated","activatorParks"]),
    "qsos":find_stat(raw,["qsos","qsoCount","totalQsos","totalQSOs","activatorQsos"]),
    "states":find_stat(raw,["states","stateCount","uniqueStates"]),
}
rows=find_activation_rows(raw)

# Try to enrich any park references found in the public stats response.
parks=[]
seen=set()
for row in rows:
    ref=row["reference"]
    if ref in seen: continue
    seen.add(ref)
    try:
        p=get_json(f"{BASE}/park/{quote(ref)}")
        lat=lon=None
        name=row["name"]
        for d in walk(p):
            if not isinstance(d,dict): continue
            if lat is None:
                lat=d.get("latitude") or d.get("lat")
                lon=d.get("longitude") or d.get("lon") or d.get("lng")
            name=d.get("name") or d.get("parkName") or name
        if lat is not None and lon is not None:
            parks.append({"reference":ref,"name":name,"lat":float(lat),"lon":float(lon)})
    except Exception as e:
        print("Park enrichment skipped",ref,e,file=sys.stderr)

payload={
    "callsign":CALL,
    "updatedAt":datetime.now(timezone.utc).isoformat(),
    "stats":stats,
    "activationsList":sorted(rows,key=lambda x:x["date"],reverse=True)[:100],
    "parks":parks,
    "source":"POTA public API",
    "status":"ok"
}
os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,"w",encoding="utf-8") as f: json.dump(payload,f,indent=2)
print("Wrote",OUT)
print(json.dumps(stats,indent=2))
