"""
scripts/fetch_imerg_bgd.py

Downloads NASA GPM IMERG V07 Final Run daily precipitation (GPM_3IMERGDF.07) for the whole
Bangladesh box on the native 0.1 degree grid (52 x 64 cells), 2001-01-01 to 2025-09-30, through
the NASA Earthdata OPeNDAP subset service (about 40 KB per day). One file per year:

    data/raw/imerg_bgd/imerg_<year>.npz   (dates, precip_mm [day, lat, lon], version, missing)

data/raw/ is gitignored. Resumable: a year whose file already has all its days is skipped.
Needs EARTHDATA_TOKEN in .env (never printed). Free; no other account is used.

Run from the repo root:
    python scripts/fetch_imerg_bgd.py              # 8 parallel workers, whole record
    python scripts/fetch_imerg_bgd.py 2005 2006    # only these years
"""

import datetime as dt
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from common import proj_guard  # noqa: E402  (must run before rasterio / pyproj are imported)
proj_guard.apply()
sys.path.insert(0, os.path.join(ROOT, "src", "acquire"))
import imerg_subset as ims  # noqa: E402
from district_grid.grid import imerg_axes  # noqa: E402
import numpy as np  # noqa: E402
import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

OUT_DIR = os.path.join(ROOT, "data", "raw", "imerg_bgd")
FIRST_DAY = dt.date(2001, 1, 1)
LAST_DAY = dt.date(2025, 9, 30)  # end of the V07 Final Run record at the time of writing
WORKERS = 8


def year_path(year):
    return os.path.join(OUT_DIR, f"imerg_{year}.npz")


def year_days(year):
    return ims.days_between(max(FIRST_DAY, dt.date(year, 1, 1)), min(LAST_DAY, dt.date(year, 12, 31)))


def is_complete(year):
    p = year_path(year)
    if not os.path.exists(p):
        return False
    try:
        with np.load(p) as z:
            return len(z["dates"]) == len(year_days(year))
    except Exception:
        return False


def fetch_with_retry(session, token, day):
    last = None
    for attempt in range(4):
        try:
            field, ver, status = ims.fetch_day(session, token, day)
            if field is not None:
                return day, field, ver
            if status in (400, 404):
                return day, None, None  # no such granule on the server
            last = status
        except Exception as err:  # network error, odd response: retry
            last = type(err).__name__
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{day}: failed after 4 tries (last: {last})")


def fetch_year(year, token):
    days = year_days(year)
    shape = (len(imerg_axes()[1]), len(imerg_axes()[0]))
    t0 = time.time()
    with requests.Session() as session, ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(lambda d: fetch_with_retry(session, token, d), days))
    precip = np.full((len(days), *shape), np.nan, dtype="float32")
    versions, missing = [], []
    for i, (day, field, ver) in enumerate(results):
        if field is None:
            missing.append(day.isoformat())
            versions.append("")
        else:
            precip[i] = field
            versions.append(ver)
    np.savez_compressed(year_path(year), dates=np.array([d.isoformat() for d in days]),
                        precip_mm=precip, version=np.array(versions), missing=np.array(missing))
    print(f"{year}: {len(days) - len(missing)}/{len(days)} days, "
          f"versions {sorted(set(versions) - {''})}, missing {len(missing)}, {time.time() - t0:.0f} s", flush=True)


def main(argv):
    load_dotenv(os.path.join(ROOT, ".env"))
    token = os.environ.get("EARTHDATA_TOKEN")
    if not token:
        sys.exit("EARTHDATA_TOKEN is not set in .env")
    os.makedirs(OUT_DIR, exist_ok=True)
    years = [int(a) for a in argv] or list(range(FIRST_DAY.year, LAST_DAY.year + 1))
    for year in years:
        if is_complete(year):
            print(f"{year}: already complete, skipped", flush=True)
        else:
            fetch_year(year, token)


if __name__ == "__main__":
    main(sys.argv[1:])
