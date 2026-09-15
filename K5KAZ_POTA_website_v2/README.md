# K5KAZ POTA Website — v2

A dark outdoors personal website focused on K5KAZ's Parks on the Air activities.

## What is included

- Dark outdoors / radio-shack visual design
- Responsive desktop + mobile layout
- POTA statistics area
- Automatic daily POTA cache refresh via GitHub Actions
- Recent activation section
- Leaflet/OpenStreetMap park map
- Station & Gear, Photos, and About sections ready for real content
- No POTA password or private credentials are stored in the site

## Automatic update design

The browser reads `data/pota.json`, not the POTA API directly. The GitHub Action runs once per day and calls the public POTA stats endpoint, then attempts to enrich park references with public park information.

POTA's official public API documentation is currently marked under construction. The site therefore uses a defensive parser and keeps the raw upstream assumptions isolated in `scripts/update-pota.py`.

POTA is the authoritative system of record for your activity. POTA states that submitted ADIF logs feed its activity/statistics system and that stats can take time to update after log submission.

## Publish with GitHub Pages

1. Create a GitHub repository, e.g. `k5kaz-pota`.
2. Upload all files from this folder.
3. In GitHub: Settings → Pages → Deploy from branch → `main` → `/ (root)`.
4. Go to Actions and manually run **Update K5KAZ POTA data** once.
5. The scheduled workflow will refresh the cached POTA data daily.
6. Add your custom domain later if desired.

## Important

The first sync should be run against the live POTA API after the repository is published. If the current POTA response uses field names not recognized by the defensive parser, the updater will still save the response-derived file, but a small field-mapping adjustment may be needed.

## Next personalization

Replace the three feature cards with your actual:
- Radios
- Antennas
- Power system
- Logging software
- Activation photos
- Short biography
- Favorite parks / activation stories

The placeholder hero artwork is a concept image. For the finished site, use your own POTA photographs.
