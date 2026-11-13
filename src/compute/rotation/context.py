"""
src/compute/rotation/context.py

Everything one rotation evaluation reads, in one object, so tests can hand in
a synthetic crop table, synthetic crop specs and synthetic weather. The real
context is built only from the existing risk-calendar loaders: nothing here
re-implements a threshold, a stage or a water balance.
"""

import datetime
import functools
import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd

import risk_calendar as rc
from common import Provenance
from weather import DATA_DIR, RAIN_CITATIONS

from .crop_table import REPO_ROOT, load_crop_table

REPO_URL = "https://github.com/Taaanha/Crop-Shift"
POWER_URL = "https://power.larc.nasa.gov/"


@dataclass
class RotationContext:
    crop_table: pd.DataFrame
    specs: dict                      # risk_calendar crop specs (cited hazards, stages, window)
    weather: Optional[pd.DataFrame]  # rc.prepare_weather(); None only for candidate listing
    water: Optional[dict]            # kc_table / crop_params / soil / paddy, or None (no water)
    turnaround_days: Optional[int]   # None -> risk_calendar.TURNAROUND_DAYS (an assumption)
    weather_provenance: Provenance
    params: Optional[dict] = None    # risk_calendar params (default rc.DEFAULT_PARAMS)
    aman_duration_from: str = "seedbed"   # or "transplanting" (the later, more careful harvest)

    def turnaround(self):
        return rc.TURNAROUND_DAYS if self.turnaround_days is None else int(self.turnaround_days)

    def turnaround_note(self):
        if self.turnaround_days is None:
            return (f"turnaround {rc.TURNAROUND_DAYS} days is a CropShift assumption "
                    "(risk_calendar.ASSUMPTIONS); no cited source yet (NEEDS SOURCE)")
        return f"turnaround {int(self.turnaround_days)} days (supplied by the caller)"

    def risk_params(self):
        return self.params or rc.DEFAULT_PARAMS


def file_date(paths):
    """Latest modification date (ISO) of the files: the best 'retrieved' date the
    repository keeps for a processed data file."""
    stamps = [os.path.getmtime(p) for p in paths if os.path.exists(p)]
    day = datetime.date.fromtimestamp(max(stamps)) if stamps else datetime.date.today()
    return day.isoformat()


def weather_provenance(district):
    power = os.path.join(DATA_DIR, f"power_{district}_daily.csv")
    imerg = os.path.join(DATA_DIR, f"imerg_{district}_daily.csv")
    rel = lambda p: os.path.relpath(p, REPO_ROOT).replace("\\", "/")
    return Provenance(
        dataset=(RAIN_CITATIONS["imerg"]["dataset"] + " (rain) + NASA POWER daily "
                 "(temperature, humidity, wind, solar), with FAO-56 ET0"),
        source_url=RAIN_CITATIONS["imerg"]["url"] + " ; " + POWER_URL,
        retrieved=file_date([power, imerg]),
        granule_or_file=f"{rel(imerg)} ; {rel(power)}",
        note="date is the data file's last-modified date; the files hold the area around the field")


def table_provenance(note=""):
    path = os.path.join(REPO_ROOT, "data", "reference", "crops.csv")
    return Provenance(
        dataset="CropShift crop table (cited rows copied from data/reference/*.csv)",
        source_url=REPO_URL + "/blob/main/data/reference/crops.csv",
        retrieved=file_date([path]), granule_or_file="data/reference/crops.csv", note=note)


def specs_and_ref():
    ref = rc.load_reference_for_calendar()
    return rc.build_crop_specs(ref), ref


@functools.lru_cache(maxsize=8)
def load_context(district, with_weather=True):
    """The real context for a district (cached; treat it as read-only)."""
    metadata = pd.read_csv(rc.DISTRICT_METADATA_PATH).set_index("district")
    if district not in metadata.index:
        raise ValueError(f"unknown district {district!r}; known: {sorted(metadata.index)}")
    specs, ref = specs_and_ref()
    weather, water = None, None
    if with_weather:
        weather = rc.prepare_weather(district, metadata)
        water = {"kc_table": pd.read_csv(rc.KC_TABLE_PATH), "crop_params": rc.load_crop_params(),
                 "soil": rc.load_soil_params()[district], "paddy": rc.resolve_paddy(ref)}
    return RotationContext(crop_table=load_crop_table(), specs=specs, weather=weather,
                           water=water, turnaround_days=None,
                           weather_provenance=weather_provenance(district))

