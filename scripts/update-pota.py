#!/usr/bin/env python3
import json,os,sys
from datetime import datetime,timezone
from urllib.parse import quote
from urllib.request import Request,urlopen
CALL=os.environ.get('POTA_CALLSIGN','K5KAZ').upper();BASE='https://api.pota.app';OUT='data/pota.json'
def get(u):
 r=Request(u,headers={'User-Agent':'K5KAZ-POTA-Site/3.0','Accept':'application/json'})
 with urlopen(r,timeout=30) as x:return json.loads(x.read().decode())
def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
def num(x):
 try:
  if isinstance(x,bool):return None
  n=float(x);return int(n) if n.is_integer() else n
 except:return None
def first(o,keys):
 for d in walk(o):
  for k in keys:
   if k in d:
    n=num(d[k])
    if n is not None:return n
def firstlist(o,keys):
 for d in walk(o):
  for k in keys:
   if isinstance(d.get(k),list):return d[k]
def date(v):
 s=str(v).strip();return f'{s[:4]}-{s[4:6]}-{s[6:]}' if len(s)==8 and s.isdigit() else s
def row(i):
 if not isinstance(i,dict):return
 ref=i.get('reference') or i.get('parkReference') or i.get('park_ref') or i.get('park') or i.get('ref');dt=i.get('date') or i.get('activationDate') or i.get('activation_date') or i.get('qso_date') or i.get('QSO_DATE')
 if not ref or not dt:return
 return {'reference':str(ref),'name':str(i.get('parkName') or i.get('name') or i.get('locationName') or ref),'date':date(dt),'qsos':int(first(i,['qsos','qsoCount','totalQsos','totalQSOs','contacts','count']) or 0)}
def rows(raw):
 out=[];seen=set()
 for i in (firstlist(raw,['activations','activationList','activationsList','results','data']) or []):
  r=row(i)
  if r and (r['reference'],r['date']) not in seen:seen.add((r['reference'],r['date']));out.append(r)
 for i in walk(raw):
  r=row(i)
  if r and (r['reference'],r['date']) not in seen:seen.add((r['reference'],r['date']));out.append(r)
 return sorted(out,key=lambda x:x['date'],reverse=True)
def park(ref):
 d=get(f'{BASE}/park/{quote(ref)}');name=ref;lat=lon=None
 for x in walk(d):
  if not isinstance(x,dict):continue
  name=x.get('name') or x.get('parkName') or name;lat=lat if lat is not None else x.get('latitude') or x.get('lat');lon=lon if lon is not None else x.get('longitude') or x.get('lon') or x.get('lng')
 try:return str(name),float(lat),float(lon)
 except:return str(name),None,None
raw=get(f'{BASE}/stats/user/{quote(CALL)}');rr=rows(raw);stats={'activations':first(raw,['activations','activationCount','totalActivations','activatorActivations']),'parks':first(raw,['parks','parkCount','uniqueParks','uniqueParksActivated','activatorParks']),'qsos':first(raw,['qsos','qsoCount','totalQsos','totalQSOs','activatorQsos']),'states':first(raw,['states','stateCount','uniqueStates','statesActivated'])}
if stats['activations'] is None and rr:stats['activations']=len(rr)
if stats['parks'] is None and rr:stats['parks']=len({r['reference'] for r in rr})
if stats['qsos'] is None and rr:stats['qsos']=sum(r['qsos'] for r in rr)
stats={k:(v if v is not None else 0) for k,v in stats.items()};parks=[];seen=set()
for r in rr:
 ref=r['reference']
 if ref in seen:continue
 seen.add(ref)
 try:
  name,lat,lon=park(ref)
  if lat is not None and lon is not None:parks.append({'reference':ref,'name':name,'lat':lat,'lon':lon})
 except Exception as e:print(f'Park enrichment skipped {ref}: {e}',file=sys.stderr)
if not rr and not any(stats.values()):raise SystemExit('POTA returned no usable data')
os.makedirs('data',exist_ok=True)
with open(OUT,'w',encoding='utf-8') as f:json.dump({'callsign':CALL,'updatedAt':datetime.now(timezone.utc).isoformat(),'stats':stats,'activationsList':rr[:100],'parks':parks,'source':'POTA public API','status':'ok'},f,indent=2)
print(json.dumps(stats,indent=2));print(f'Activation records: {len(rr)}');print(f'Park locations: {len(parks)}')
