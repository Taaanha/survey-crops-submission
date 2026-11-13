"""
src/compute/indicators/trend.py

Long-term trend with a homogeneity check (W2, item 7).
Theil-Sen slope + Kendall tau test on the series; then Pettitt's change-point test on the
detrended RESIDUALS. If the residuals still show a level shift, the series is called a step
change and NOT a trend (a broken record must not be shown as a trend).

alpha = 0.05 is a conventional level, our choice, not a cited requirement.
Theil (1950) / Sen (1968) slope; Kendall (1938) tau; Pettitt (1979), see change_point.py.
"""

import numpy as np
from scipy import stats

from change_point import pettitt_test

ALPHA = 0.05
MIN_YEARS = 8


def trend_status(years, values, alpha=ALPHA, unit=""):
    """Status of one yearly series: 'trend', 'step_change', 'no_trend' or 'not_enough_years'.

    Returns a dict: slope (per year, Theil-Sen), tau, kendall_p, pettitt_p, step_year (first year
    of the new level, or None), n, alpha, status, text (one plain sentence)."""
    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)
    ok = ~np.isnan(y)
    x, y = x[ok], y[ok]
    n = int(len(y))
    out = {"slope": float("nan"), "tau": float("nan"), "kendall_p": float("nan"),
           "pettitt_p": float("nan"), "step_year": None, "n": n, "alpha": alpha}
    if n < MIN_YEARS:
        out.update(status="not_enough_years",
                   text=f"only {n} usable seasons (need {MIN_YEARS}); no trend assessed")
        return out

    slope, intercept, _, _ = stats.theilslopes(y, x)
    if np.ptp(y) == 0.0:
        tau, kp = 0.0, 1.0
    else:
        tau, kp = stats.kendalltau(x, y)
        tau, kp = float(tau), float(kp)
    resid = y - (slope * x + intercept)
    pet = pettitt_test(resid)
    out.update(slope=float(slope), tau=round(tau, 6), kendall_p=kp, pettitt_p=pet["p"])

    u = f" {unit}" if unit else ""
    if pet["p"] < alpha:
        year = int(x[pet["split"]])
        out.update(status="step_change", step_year=year,
                   text=f"level shift around {year}, not shown as a trend "
                        f"(Pettitt p={pet['p']:.3f} on the detrended values, n={n})")
    elif kp < alpha:
        out.update(status="trend",
                   text=f"steady change of {slope:+.3g}{u} per year (Kendall p={kp:.3f}, n={n}); "
                        f"no level shift found")
    else:
        out.update(status="no_trend",
                   text=f"no clear trend and no level shift (Kendall p={kp:.2f}, n={n})")
    return out
