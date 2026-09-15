#!/usr/bin/env python3
"""
K5KAZ POTA data updater.

Validates the POTA public API response instead of assuming one fixed shape.
Fails the GitHub Action when no usable POTA data is returned.
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen

CALL = os.environ.get("POTA_CALLSIGN", "K5KAZ").upper()
BASE = "https://api.pota.app"
OUT = "data/pota.json"


def get_json(url):
    req = Request(
        url,
        headers={
            "User-Agent": "K5KAZ-POTA-Site/2.1",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=30) as response:
        body = response.read()
        if not body:
            raise RuntimeError(f"Empty response from {url}")
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Response from {url} was not valid JSON: {body[:200]!r}"
            ) from exc


def as_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return None


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def first_number(obj, keys):
    for item in walk(obj):
        for key in keys:
            if key in item:
                value = as_number(item[key])
                if value is not None:
                    return value
    return None


def first_list(obj, keys):
    for item in walk(obj):
        for key in keys:
            value = item.get(key)
            if isinstance(value, list):
                return value
    return None


def normalize_date(value):
    if value is None:
        return None
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def normalize_activation(item):
    if not isinstance(item, dict):
        return None

    ref = (
        item.get("reference")
        or item.get("parkReference")
        or item.get("park_ref")
        or item.get("park")
        or item.get("ref")
    )
    date = (
        item.get("date")
        or item.get("activationDate")
        or item.get("activation_date")
        or item.get("qso_date")
        or item.get("QSO_DATE")
    )

    if not ref or not date:
        return None

    qsos = first_number(
        item,
        ["qsos", "qsoCount", "totalQsos", "totalQSOs", "contacts", "count"],
    )
    name = (
        item.get("parkName")
        or item.get("name")
        or item.get("locationName")
        or str(ref)
    )

    return {
        "reference": str(ref),
        "name": str(name),
        "date": normalize_date(date),
        "qsos": int(qsos or 0),
    }


def find_activation_rows(raw):
    rows = []
    seen = set()

    candidates = first_list(
        raw,
        ["activations", "activationList", "activationsList", "results", "data"],
    )

    if candidates:
        for item in candidates:
            row = normalize_activation(item)
            if row:
                key = (row["reference"], row["date"])
                if key not in seen:
                    seen.add(key)
                    rows.append(row)

    for item in walk(raw):
        row = normalize_activation(item)
        if row:
            key = (row["reference"], row["date"])
            if key not in seen:
                seen.add(key)
                rows.append(row)

    return sorted(rows, key=lambda x: x["date"], reverse=True)


def fetch_stats():
    url = f"{BASE}/stats/user/{quote(CALL)}"
    print(f"Fetching POTA stats for {CALL}: {url}")

    raw = get_json(url)

    if raw is None:
        raise RuntimeError("POTA returned JSON null")

    stats = {
        "activations": first_number(
            raw,
            ["activations", "activationCount", "totalActivations",
             "activatorActivations"],
        ),
        "parks": first_number(
            raw,
            ["parks", "parkCount", "uniqueParks",
             "uniqueParksActivated", "activatorParks"],
        ),
        "qsos": first_number(
            raw,
            ["qsos", "qsoCount", "totalQsos",
             "totalQSOs", "activatorQsos"],
        ),
        "states": first_number(
            raw,
            ["states", "stateCount", "uniqueStates", "statesActivated"],
        ),
    }

    rows = find_activation_rows(raw)

    if stats["activations"] is None and rows:
        stats["activations"] = len(rows)

    if stats["parks"] is None and rows:
        stats["parks"] = len({row["reference"] for row in rows})

    if stats["qsos"] is None and rows:
        stats["qsos"] = sum(row["qsos"] for row in rows)

    return raw, stats, rows


def enrich_parks(rows):
    parks = []
    seen = set()

    for row in rows:
        ref = row["reference"]
        if ref in seen:
            continue
        seen.add(ref)

        try:
            data = get_json(f"{BASE}/park/{quote(ref)}")
            lat = lon = None
            name = row["name"]

            for item in walk(data):
                if lat is None:
                    lat = item.get("latitude") or item.get("lat")
                if lon is None:
                    lon = item.get("longitude") or item.get("lon") or item.get("lng")
                name = item.get("name") or item.get("parkName") or name

            if lat is not None and lon is not None:
                parks.append({
                    "reference": ref,
                    "name": str(name),
                    "lat": float(lat),
                    "lon": float(lon),
                })
        except Exception as exc:
            print(f"Park enrichment skipped {ref}: {exc}", file=sys.stderr)

    return parks


def main():
    try:
        raw, stats, rows = fetch_stats()
    except Exception as exc:
        print(f"POTA sync failed: {exc}", file=sys.stderr)
        sys.exit(1)

    usable_stats = sum(value is not None for value in stats.values())
    if usable_stats == 0 and not rows:
        print(
            "POTA returned JSON, but no recognizable statistics or activation "
            "records were found.",
            file=sys.stderr,
        )
        print("Top-level response type:", type(raw).__name__, file=sys.stderr)
        if isinstance(raw, dict):
            print(
                "Top-level keys:",
                ", ".join(map(str, list(raw.keys())[:50])),
                file=sys.stderr,
            )
        sys.exit(2)

    stats = {
        key: (value if value is not None else 0)
        for key, value in stats.items()
    }

    parks = enrich_parks(rows)

    payload = {
        "callsign": CALL,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "activationsList": rows[:100],
        "parks": parks,
        "source": "POTA public API",
        "status": "ok",
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(f"Wrote {OUT}")
    print(json.dumps(stats, indent=2))
    print(f"Activation records: {len(rows)}")
    print(f"Park locations: {len(parks)}")


if __name__ == "__main__":
    main()

