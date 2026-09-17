K5KAZ POTA website

POTA data is updated by GitHub Actions.

The live aggregate statistics (activations, parks, QSOs) come from the POTA public API.
The States count and the My POTA Parks map use data from data/activator_parks.csv,
which is the current POTA My Stats -> Activator Parks -> Export CSV file.

If your POTA park list changes, replace data/activator_parks.csv with a fresh export
from POTA and commit it to GitHub. Then run the "Update K5KAZ POTA data" workflow.

The updater gets park coordinates from the official POTA API, so coordinates are not
stored manually in the website.
