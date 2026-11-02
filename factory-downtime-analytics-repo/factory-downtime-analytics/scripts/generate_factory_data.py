"""
Synthetic factory downtime dataset generator (SIMULATED DATA).

Creates three CSVs for a Tableau downtime dashboard:
  machines.csv          - machine master data (12 machines, 3 lines)
  downtime_events.csv   - one row per downtime event
  shift_production.csv  - one row per machine per shift (OEE inputs + telemetry)

Run:  python scripts/generate_factory_data.py   (writes to ../data)
Seeded, so the output is reproducible. Label the project as "simulated data"
on your resume / GitHub README.
"""
import os
import numpy as np
import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(OUT, exist_ok=True)

rng = np.random.default_rng(42)

START, END = "2026-01-01", "2026-09-30"
SHIFTS = {"A": 6, "B": 14, "C": 22}          # shift name -> start hour
SHIFT_MIN = 480

# ---------------- machines ----------------
machines = pd.DataFrame([
    # id, name, line, type, install_year, ideal_cycle_sec, margin_inr_per_unit
    ("M01", "CNC-01",      "Line A", "CNC Machine",   2019, 42, 180),
    ("M02", "CNC-02",      "Line A", "CNC Machine",   2020, 42, 180),
    ("M03", "Press-03",    "Line A", "Hydraulic Press", 2016, 30, 120),
    ("M04", "Robot-04",    "Line A", "Robot Arm",     2022, 25, 150),
    ("M05", "Pack-05",     "Line B", "Packaging",     2021, 12, 40),
    ("M06", "Pack-06",     "Line B", "Packaging",     2021, 12, 40),
    ("M07", "Press-07",    "Line B", "Hydraulic Press", 2015, 30, 120),
    ("M08", "Conveyor-08", "Line B", "Conveyor",      2018, 10, 30),
    ("M09", "CNC-09",      "Line C", "CNC Machine",   2023, 42, 180),
    ("M10", "Robot-10",    "Line C", "Robot Arm",     2023, 25, 150),
    ("M11", "Pack-11",     "Line C", "Packaging",     2020, 12, 40),
    ("M12", "Conveyor-12", "Line C", "Conveyor",      2017, 10, 30),
], columns=["machine_id", "machine_name", "line", "machine_type",
            "install_year", "ideal_cycle_sec", "margin_inr_per_unit"])

# base unplanned-failure intensity per machine-shift (older = worse)
reliab = {m: 1.0 + 0.06 * (2026 - y) for m, y in
          zip(machines.machine_id, machines.install_year)}

# reason code -> (category, median minutes, base rate per machine-shift)
REASONS = {
    "Mechanical Failure":    ("Unplanned", 55, 0.060),
    "Electrical Fault":      ("Unplanned", 35, 0.035),
    "Sensor Fault":          ("Unplanned", 15, 0.040),
    "Tool Wear":             ("Unplanned", 25, 0.040),
    "Material Shortage":     ("Unplanned", 30, 0.045),
    "Operator Absence":      ("Unplanned", 40, 0.025),
    "Changeover":            ("Planned",   30, 0.070),
    "Scheduled Maintenance": ("Planned",   90, 0.000),   # handled separately
}

days = pd.date_range(START, END, freq="D")
n_days = len(days)

events, rows = [], []
fail_flag = {}          # (machine, shift_index) -> True if mech/electrical failure

shift_index = 0
for d_i, day in enumerate(days):
    for sname, shour in SHIFTS.items():
        shift_start = day + pd.Timedelta(hours=shour)
        for _, m in machines.iterrows():
            mid = m.machine_id
            prog = d_i / n_days
            evs = []
            for reason, (cat, med, rate) in REASONS.items():
                lam = rate * reliab[mid]
                # planted patterns
                if sname == "C":
                    lam *= 1.35                       # night shift is worse
                if reason == "Changeover" and day.dayofweek == 0:
                    lam *= 1.8                        # Monday changeover spike
                if mid == "M07" and reason == "Mechanical Failure":
                    lam *= 1.0 + 2.0 * prog           # Press-07 degrading
                if mid == "M03" and reason == "Sensor Fault":
                    lam *= 3.0                        # chronic sensor problem
                if mid == "M08" and reason == "Material Shortage":
                    lam *= 2.2                        # conveyor starved of input
                if reason == "Scheduled Maintenance":
                    # weekly on Sunday, shift A
                    if day.dayofweek == 6 and sname == "A":
                        lam = 1.0
                    else:
                        continue
                k = rng.poisson(lam) if lam < 1 else 1
                for _ in range(k):
                    dur = float(np.clip(rng.lognormal(np.log(med), 0.55), 3, 240))
                    evs.append([reason, cat, dur])

            # keep total downtime under the shift length, then place events
            total = sum(e[2] for e in evs)
            if total > 400:
                f = 400 / total
                for e in evs:
                    e[2] *= f
                total = 400
            if evs:
                gaps = rng.dirichlet(np.ones(len(evs) + 1)) * (SHIFT_MIN - total)
                t = 0.0
                for (reason, cat, dur), g in zip(evs, gaps[:-1]):
                    t += g
                    st = shift_start + pd.Timedelta(minutes=t)
                    en = st + pd.Timedelta(minutes=dur)
                    events.append([mid, st, en, round(dur, 1), cat, reason,
                                   sname, shift_index])
                    t += dur
                    if reason in ("Mechanical Failure", "Electrical Fault"):
                        fail_flag[(mid, shift_index)] = True

            planned_dt = sum(e[2] for e in evs if e[1] == "Planned")
            unplanned_dt = sum(e[2] for e in evs if e[1] == "Unplanned")
            rows.append([mid, day.date(), sname, shift_index,
                         round(planned_dt, 1), round(unplanned_dt, 1)])
        shift_index += 1

# ---------------- downtime_events ----------------
ev = pd.DataFrame(events, columns=["machine_id", "start_time", "end_time",
                                   "duration_min", "downtime_category",
                                   "reason_code", "shift", "_si"])
ev = ev.merge(machines[["machine_id", "ideal_cycle_sec", "margin_inr_per_unit"]],
              on="machine_id")
ev["est_lost_units"] = (ev.duration_min * 60 / ev.ideal_cycle_sec * 0.9).round(0)
ev["est_loss_inr"] = (ev.est_lost_units * ev.margin_inr_per_unit).round(0)
# only unplanned downtime counts as "loss" in INR
ev.loc[ev.downtime_category == "Planned", "est_loss_inr"] = 0
ev["start_time"] = ev.start_time.dt.round("s")
ev["end_time"] = ev.end_time.dt.round("s")
ev = ev.sort_values("start_time").reset_index(drop=True)
ev.insert(0, "event_id", ["EV" + str(i + 1).zfill(6) for i in range(len(ev))])
ev = ev.drop(columns=["_si", "ideal_cycle_sec", "margin_inr_per_unit"])

# ---------------- shift_production (+ telemetry) ----------------
sp = pd.DataFrame(rows, columns=["machine_id", "date", "shift", "_si",
                                 "planned_downtime_min", "unplanned_downtime_min"])
sp = sp.merge(machines[["machine_id", "ideal_cycle_sec", "install_year"]],
              on="machine_id")
sp["scheduled_min"] = SHIFT_MIN
sp["run_min"] = (SHIFT_MIN - sp.planned_downtime_min
                 - sp.unplanned_downtime_min).round(1)

perf_base = {m: rng.uniform(0.84, 0.96) for m in machines.machine_id}
sp["_perf"] = sp.machine_id.map(perf_base) + rng.normal(0, 0.025, len(sp))
sp["_perf"] = sp._perf.clip(0.6, 1.0)
sp["units_total"] = (sp.run_min * 60 / sp.ideal_cycle_sec * sp._perf).round(0)
q_base = {m: rng.uniform(0.965, 0.995) for m in machines.machine_id}
sp["_q"] = (sp.machine_id.map(q_base) + rng.normal(0, 0.006, len(sp))).clip(0.9, 1.0)
sp["units_defective"] = (sp.units_total * (1 - sp._q)).round(0)

# telemetry: drifts upward in the 2 shifts before a failure
temp_base = {m: rng.uniform(62, 72) for m in machines.machine_id}
vib_base = {m: rng.uniform(1.8, 2.6) for m in machines.machine_id}
temps, vibs = [], []
for mid, si in zip(sp.machine_id, sp._si):
    pre = (fail_flag.get((mid, si)) or fail_flag.get((mid, si + 1))
           or fail_flag.get((mid, si + 2)))
    t = temp_base[mid] + rng.normal(0, 3.0) + (14 if pre else 0)
    v = vib_base[mid] + rng.normal(0, 0.35) + (2.0 if pre else 0)
    if mid == "M07":
        t += 4          # Press-07 runs hot
        v += 0.5
    temps.append(round(t, 1))
    vibs.append(round(max(v, 0.3), 2))
sp["avg_temp_c"], sp["avg_vibration_mm_s"] = temps, vibs

sp = sp.drop(columns=["_si", "_perf", "_q", "install_year"])
sp.insert(0, "record_id", ["SP" + str(i + 1).zfill(6) for i in range(len(sp))])

# ---------------- write ----------------
machines.drop(columns=["margin_inr_per_unit"]).to_csv(os.path.join(OUT, "machines.csv"), index=False)
ev.to_csv(os.path.join(OUT, "downtime_events.csv"), index=False)
sp.to_csv(os.path.join(OUT, "shift_production.csv"), index=False)

# ---------------- quick sanity summary ----------------
print("machines.csv:", len(machines), "rows")
print("downtime_events.csv:", len(ev), "rows")
print("shift_production.csv:", len(sp), "rows")
avail = 1 - (sp.planned_downtime_min + sp.unplanned_downtime_min).sum() / sp.scheduled_min.sum()
print(f"Overall availability: {avail:.1%}")
print("\nUnplanned downtime hours by reason:")
print((ev[ev.downtime_category == "Unplanned"].groupby("reason_code").duration_min.sum() / 60).round(0).sort_values(ascending=False))
print("\nUnplanned downtime hours by shift:")
print((ev[ev.downtime_category == "Unplanned"].groupby("shift").duration_min.sum() / 60).round(0))
print("\nUnplanned downtime hours by machine (top 5):")
ev2 = ev.merge(machines[["machine_id", "machine_name"]], on="machine_id")
print((ev2[ev2.downtime_category == "Unplanned"].groupby("machine_name").duration_min.sum() / 60).round(0).sort_values(ascending=False).head(5))
unh = ((sp.avg_temp_c > 85) | (sp.avg_vibration_mm_s > 4.5)).mean()
warn = (((sp.avg_temp_c > 75) | (sp.avg_vibration_mm_s > 3.5)) & ~((sp.avg_temp_c > 85) | (sp.avg_vibration_mm_s > 4.5))).mean()
print(f"\nUnhealthy share (temp>85 or vib>4.5): {unh:.1%}  Warning share: {warn:.1%}")
