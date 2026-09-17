#!/usr/bin/env python3
import csv
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen

CALL = os.environ.get('POTA_CALLSIGN', 'K5KAZ').upper()
BASE = 'https://api.pota.app'
OUT = 'data/pota.json'
ACTIVATOR_CSV = 'data/activator_parks.csv'


def get(url):
    req = Request(url, headers={
        'User-Agent': 'K5KAZ-POTA-Site/3.1',
        'Accept': 'application/json',
    })
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def num(value):
    try:
        if isinstance(value, bool):
            return None
        n = float(value)
        return int(n) if n.is_integer() else n
    except Exception:
        return None


def first(obj, keys):
    for item in walk(obj):
        for key in keys:
            if key in item:
                value = num(item[key])
                if value is not None:
                    return value
    return None


def load_activated_parks():
    if not os.path.exists(ACTIVATOR_CSV):
        raise RuntimeError(f'Missing {ACTIVATOR_CSV}. Upload the current POTA Activator Parks CSV.')

    parks = []
    seen = set()
    with open(ACTIVATOR_CSV, 'r', encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            ref = (row.get('Reference') or row.get('reference') or '').strip()
            if not ref or ref in seen:
                continue
            seen.add(ref)
            parks.append({
                'reference': ref,
                'name': (row.get('Park Name') or row.get('name') or ref).strip(),
                'location': (row.get('HASC') or row.get('Location') or '').strip(),
                'date': (row.get('First QSO Date') or '').strip(),
                'attempts': int(float(row.get('Attempts') or 0)),
                'activations': int(float(row.get('Activations') or 0)),
                'qsos': int(float(row.get('QSOs') or 0)),
            })
    return parks


def extract_park_list(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ('parks', 'data', 'results'):
            value = raw.get(key)
            if isinstance(value, list):
                return value
    return []


def add_coordinates(activated):
    # Fetch each state/location once, then match the user's 45 current park
    # references against the official POTA park catalog returned by the API.
    by_ref = {}
    locations = sorted({p['location'] for p in activated if p['location']})

    for location in locations:
        if not location.startswith('US-'):
            continue
        try:
            raw = get(f'{BASE}/location/parks/{quote(location)}')
            for item in extract_park_list(raw):
                if not isinstance(item, dict):
                    continue
                ref = item.get('reference') or item.get('parkReference')
                if ref:
                    by_ref[str(ref)] = item
        except Exception as exc:
            print(f'Location catalog skipped {location}: {exc}', file=sys.stderr)

    result = []
    missing = []
    for park in activated:
        item = by_ref.get(park['reference'])
        if item is None:
            missing.append(park)
            continue
        lat = item.get('latitude') or item.get('lat')
        lon = item.get('longitude') or item.get('lon') or item.get('lng')
        if lat is not None and lon is not None:
            result.append({
                'reference': park['reference'],
                'name': item.get('name') or park['name'],
                'location': park['location'],
                'lat': float(lat),
                'lon': float(lon),
                'firstQsoDate': park['date'],
                'attempts': park['attempts'],
                'activations': park['activations'],
                'qsos': park['qsos'],
            })
        else:
            missing.append(park)

    # A small number of parks may not appear in the location summary. Fall
    # back to the detailed park endpoint for those references.
    for park in missing:
        try:
            raw = get(f'{BASE}/park/{quote(park["reference"])}')
            candidate = None
            for item in walk(raw):
                if not isinstance(item, dict):
                    continue
                if (item.get('reference') or item.get('parkReference')) == park['reference']:
                    candidate = item
                    break
                if candidate is None and any(k in item for k in ('latitude', 'lat')):
                    candidate = item
            if candidate:
                lat = candidate.get('latitude') or candidate.get('lat')
                lon = candidate.get('longitude') or candidate.get('lon') or candidate.get('lng')
                if lat is not None and lon is not None:
                    result.append({
                        'reference': park['reference'],
                        'name': candidate.get('name') or park['name'],
                        'location': park['location'],
                        'lat': float(lat),
                        'lon': float(lon),
                        'firstQsoDate': park['date'],
                        'attempts': park['attempts'],
                        'activations': park['activations'],
                        'qsos': park['qsos'],
                    })
                    continue
        except Exception as exc:
            print(f'Park lookup skipped {park["reference"]}: {exc}', file=sys.stderr)
        print(f'No coordinates found for {park["reference"]}', file=sys.stderr)

    return sorted(result, key=lambda p: p['reference'])


raw = get(f'{BASE}/stats/user/{quote(CALL)}')
stats = {
    'activations': first(raw, ['activations', 'activationCount', 'totalActivations', 'activatorActivations']),
    'parks': first(raw, ['parks', 'parkCount', 'uniqueParks', 'uniqueParksActivated', 'activatorParks']),
    'qsos': first(raw, ['qsos', 'qsoCount', 'totalQsos', 'totalQSOs', 'activatorQsos']),
    # The current POTA stats endpoint is not returning the state count, so
    # calculate it from the user's current Activator Parks export instead.
    'states': None,
}

activated = load_activated_parks()
state_codes = {p['location'] for p in activated if p['location']}
stats['states'] = len(state_codes)

for key in ('activations', 'parks', 'qsos'):
    if stats[key] is None:
        raise RuntimeError(f'POTA stats endpoint did not return {key}.')

parks = add_coordinates(activated)

if not activated:
    raise RuntimeError('The Activator Parks CSV contained no park rows.')

os.makedirs('data', exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as handle:
    json.dump({
        'callsign': CALL,
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        'stats': stats,
        'parks': parks,
        'source': 'POTA public API + POTA Activator Parks export',
        'status': 'ok',
    }, handle, indent=2)

print(json.dumps(stats, indent=2))
print(f'Activated park rows: {len(activated)}')
print(f'Park locations: {len(parks)}')
print(f'Activated states: {len(state_codes)}')
