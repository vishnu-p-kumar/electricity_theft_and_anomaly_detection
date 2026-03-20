from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.grid_network_model import compute_feeder_load

try:  # pragma: no cover - optional at runtime
    import pandapower as pp
except Exception:  # pragma: no cover - optional at runtime
    pp = None


def _fallback_grid_state(dataframe: pd.DataFrame) -> dict[str, Any]:
    feeders = compute_feeder_load(dataframe)
    if feeders.empty:
        return {"method": "fallback", "feeders": [], "summary": {"overloaded_feeders": 0, "average_voltage_stability": 1.0, "estimated_line_losses_kw": 0.0}}
    feeders = feeders.copy()
    feeders["voltage_stability"] = (1.0 - feeders["load_ratio"].clip(0.0, 1.4) * 0.18).clip(lower=0.72).round(3)
    feeders["line_losses_kw"] = (feeders["total_load_kw"] * (0.03 + feeders["load_ratio"] * 0.05)).round(3)
    feeders["distribution_efficiency"] = ((1.0 - (feeders["line_losses_kw"] / feeders["total_load_kw"].replace(0.0, np.nan))).fillna(1.0) * 100.0).round(2)
    summary = {
        "overloaded_feeders": int(feeders["overload_flag"].sum()),
        "average_voltage_stability": round(float(feeders["voltage_stability"].mean()), 3),
        "estimated_line_losses_kw": round(float(feeders["line_losses_kw"].sum()), 3),
    }
    return {"method": "fallback", "feeders": feeders.replace({np.nan: None}).to_dict(orient="records"), "summary": summary}


def simulate_grid_state(dataframe: pd.DataFrame) -> dict[str, Any]:
    if dataframe.empty:
        return _fallback_grid_state(dataframe)
    if pp is None:
        return _fallback_grid_state(dataframe)

    feeders = compute_feeder_load(dataframe)
    if feeders.empty:
        return _fallback_grid_state(dataframe)

    try:
        net = pp.create_empty_network()
        substation_bus = pp.create_bus(net, vn_kv=11.0, name="Grid Substation")
        pp.create_ext_grid(net, bus=substation_bus, vm_pu=1.0)
        feeder_rows: list[dict[str, Any]] = []
        for feeder in feeders.itertuples():
            feeder_bus = pp.create_bus(net, vn_kv=11.0, name=feeder.feeder_id)
            pp.create_line_from_parameters(
                net,
                from_bus=substation_bus,
                to_bus=feeder_bus,
                length_km=1.5,
                r_ohm_per_km=0.22,
                x_ohm_per_km=0.08,
                c_nf_per_km=210.0,
                max_i_ka=0.4,
                name=feeder.feeder_id,
            )
            active_mw = max(float(feeder.total_load_kw) / 1000.0, 0.001)
            reactive_mvar = max(active_mw * 0.15, 0.0002)
            pp.create_load(net, bus=feeder_bus, p_mw=active_mw, q_mvar=reactive_mvar, name=feeder.feeder_id)
        pp.runpp(net)

        for feeder in feeders.itertuples():
            bus_index = int(net.bus.loc[net.bus["name"] == feeder.feeder_id].index[0])
            voltage_pu = float(net.res_bus.loc[bus_index, "vm_pu"])
            feeder_rows.append(
                {
                    "substation": feeder.substation,
                    "feeder_id": feeder.feeder_id,
                    "meter_count": int(feeder.meter_count),
                    "total_load_kw": round(float(feeder.total_load_kw), 3),
                    "capacity_kw": round(float(feeder.capacity_kw), 3),
                    "load_ratio": round(float(feeder.load_ratio), 4),
                    "overload_flag": int(feeder.overload_flag),
                    "voltage_stability": round(voltage_pu, 4),
                    "line_losses_kw": round(float(feeder.total_load_kw) * 0.03, 3),
                    "distribution_efficiency": round((1.0 - 0.03) * 100.0, 2),
                }
            )
        return {
            "method": "pandapower",
            "feeders": feeder_rows,
            "summary": {
                "overloaded_feeders": int(sum(row["overload_flag"] for row in feeder_rows)),
                "average_voltage_stability": round(float(np.mean([row["voltage_stability"] for row in feeder_rows])), 4),
                "estimated_line_losses_kw": round(float(sum(row["line_losses_kw"] for row in feeder_rows)), 3),
            },
        }
    except Exception:
        return _fallback_grid_state(dataframe)
