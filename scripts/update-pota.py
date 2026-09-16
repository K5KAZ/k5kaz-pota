#!/usr/bin/env python3
import json, os, sys, time
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen

CALL = os.environ.get('POTA_CALLSIGN', 'K5KAZ').upper()
BASE = 'https://api.pota.app'
OUT = 'data/pota.json'
DELAY = 0.15

def get_json(url):
    req = Request(url, headers={'User-Agent':'K5KAZ-POTA-Site/3.0','Accept':'application/json'})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values(): yield from walk(v)
    elif isinstance(x, list):
        for v in x: yield from walk(v)

def num(x):
    if isinstance(x, bool): return None
    try:
        n=float(x); return int(n) if n.is_integer() else n
    except (TypeError,ValueError): return None

def first_num(obj, keys):
    for d in walk(obj):
        for k in keys:
            if k in d:
                n=num(d[k])
                if n is not None: return n
    return None

def norm_date(v):
    s=str(v).strip()
    return f'{s[:4]}-{s[4:6]}-{s[6:]}' if len(s)==8 and s.isdigit() else s

def get_stats(raw):
    return {
      'activations': first_num(raw,['activations','activationCount','totalActivations','activatorActivations']) or 0,
      'parks': first_num(raw,['parks','parkCount','uniqueParks','uniqueParksActivated','activatorParks']) or 0,
      'qsos': first_num(raw,['qsos','qsoCount','totalQsos','totalQSOs','activatorQsos']) or 0,
      'states': first_num(raw,['states','stateCount','uniqueStates','statesActivated']) or 0,
    }

def park_refs(raw):
    out=[]; seen=set()
    for d in walk(raw):
        if not isinstance(d,dict): continue
        for k in ('reference','parkReference','park_ref','park','ref'):
            v=d.get(k)
            if v:
                s=str(v).strip()
                if '-' in s and len(s)>=4 and s not in seen:
                    seen.add(s); out.append(s)
    return out

def park_info(ref):
    data=get_json(f'{BASE}/park/{quote(ref)}')
    name=ref; lat=lon=None
    for d in walk(data):
        if not isinstance(d,dict): continue
        name=d.get('name') or d.get('parkName') or name
        if lat is None: lat=d.get('latitude') or d.get('lat')
        if lon is None: lon=d.get('longitude') or d.get('lon') or d.get('lng')
    try: lat=float(lat) if lat is not None else None; lon=float(lon) if lon is not None else None
    except (TypeError,ValueError): lat=lon=None
    return str(name),lat,lon

def park_activations(ref):
    data=get_json(f'{BASE}/park/activations/{quote(ref)}?count=all')
    if isinstance(data,dict):
        for k in ('activations','results','data'):
            if isinstance(data.get(k),list): return data[k]
        return []
    return data if isinstance(data,list) else []

def main():
    raw=get_json(f'{BASE}/stats/user/{quote(CALL)}')
    st=get_stats(raw)
    refs=park_refs(raw)
    print(f'Stats: {json.dumps(st)}')
    print(f'Park references found: {len(refs)}')
    if not refs:
        print('No park references found in user stats.',file=sys.stderr); sys.exit(2)

    rows=[]; parks=[]; seen_rows=set(); seen_parks=set()
    for i,ref in enumerate(refs,1):
        print(f'Checking {i}/{len(refs)}: {ref}')
        try:
            name,lat,lon=park_info(ref); time.sleep(DELAY)
            records=park_activations(ref); found=0
            for r in records:
                if not isinstance(r,dict): continue
                active=str(r.get('activeCallsign') or r.get('activator') or r.get('callsign') or '').upper().strip()
                if active != CALL: continue
                qdate=r.get('qso_date') or r.get('date') or r.get('activationDate')
                if not qdate: continue
                total=num(r.get('totalQSOs'))
                if total is None:
                    total=(num(r.get('qsosCW')) or 0)+(num(r.get('qsosDATA')) or 0)+(num(r.get('qsosPHONE')) or 0)
                row={'reference':ref,'name':name,'date':norm_date(qdate),'qsos':int(total or 0)}
                key=(row['reference'],row['date'])
                if key not in seen_rows:
                    seen_rows.add(key); rows.append(row); found+=1
            if lat is not None and lon is not None and ref not in seen_parks:
                parks.append({'reference':ref,'name':name,'lat':lat,'lon':lon}); seen_parks.add(ref)
            print(f'  Found {found} K5KAZ activation(s)')
        except Exception as e:
            print(f'  Skipped {ref}: {e}',file=sys.stderr)
        time.sleep(DELAY)

    rows.sort(key=lambda x:x['date'],reverse=True)
    if not rows:
        print('No K5KAZ activation records found.',file=sys.stderr); sys.exit(3)

    payload={'callsign':CALL,'updatedAt':datetime.now(timezone.utc).isoformat(),'stats':st,'activationsList':rows,'parks':parks,'source':'POTA public API','status':'ok'}
    os.makedirs('data',exist_ok=True)
    with open(OUT,'w',encoding='utf-8') as f: json.dump(payload,f,indent=2)
    print(f'Wrote {OUT}')
    print(f'Activation records: {len(rows)}')
    print(f'Park locations: {len(parks)}')

if __name__=='__main__': main()

