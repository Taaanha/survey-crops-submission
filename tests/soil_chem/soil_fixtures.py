"""Hand-counted SoilGrids-shaped payloads (not real measurements)."""


def layer(name, d_factor, mapped, target, per_depth):
    """per_depth: {label: (mean, q05, q50, q95)} raw integers, as the service stores them."""
    depths = []
    for label, (mean, q05, q50, q95) in per_depth.items():
        top, bottom = label.replace("cm", "").split("-")
        depths.append({"range": {"top_depth": int(top), "bottom_depth": int(bottom), "unit_depth": "cm"},
                       "label": label,
                       "values": {"Q0.05": q05, "Q0.5": q50, "Q0.95": q95, "mean": mean}})
    return {"name": name, "unit_measure": {"d_factor": d_factor, "mapped_units": mapped,
                                           "target_units": target, "uncertainty_unit": ""},
            "depths": depths}


def payload(ph_factor=10, soc_factor=10):
    ph = layer("phh2o", ph_factor, "pH*10", "-", {
        "0-5cm": (55, 45, 54, 68), "5-15cm": (56, 46, 55, 69), "15-30cm": (58, 48, 57, 71)})
    soc = layer("soc", soc_factor, "dg/kg", "g/kg", {
        "0-5cm": (120, 80, 115, 170), "5-15cm": (100, 70, 95, 140), "15-30cm": (80, 50, 75, 120)})
    return {"type": "Feature", "properties": {"layers": [ph, soc]}}


def masked_payload():
    """A masked cell: the service answers 200 with every value null."""
    nulls = {k: (None, None, None, None) for k in ("0-5cm", "5-15cm", "15-30cm")}
    return {"type": "Feature", "properties": {"layers": [
        layer("phh2o", 10, "pH*10", "-", nulls), layer("soc", 10, "dg/kg", "g/kg", nulls)]}}
