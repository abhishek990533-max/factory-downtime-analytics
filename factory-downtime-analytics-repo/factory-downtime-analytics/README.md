# Factory Downtime Analytics Dashboard

A Tableau dashboard project analyzing machine downtime, OEE, reliability (MTBF/MTTR) and downtime cost for a manufacturing plant.

> **Note:** the dataset is **simulated**. It was generated with `scripts/generate_factory_data.py` (seeded, reproducible) to practice downtime analytics. It is not real plant data.

**Tableau Public:** _add your link here after publishing_

## Business questions
1. How much production time is lost, and how much of it is unplanned?
2. What is the OEE, and which of Availability, Performance or Quality drags it down?
3. Which reasons, machines, lines and shifts cause the most downtime (Pareto)?
4. Is any machine getting worse over time?
5. Which machines run Unhealthy (temperature / vibration) and may fail next?
6. What does unplanned downtime cost in INR?

## Tools
Tableau, Python (Pandas, NumPy), CSV

## Dataset
| File | Grain | Rows |
|---|---|---|
| `data/machines.csv` | 1 per machine (12 machines, 3 lines) | 12 |
| `data/downtime_events.csv` | 1 per downtime event | 5,664 |
| `data/shift_production.csv` | 1 per machine per shift | 9,828 |

Period: 1 Jan 2026 to 30 Sep 2026. Shifts: A (06:00-14:00), B (14:00-22:00), C (22:00-06:00), 480 minutes each.

### Key columns
- **downtime_events:** machine_id, start_time, end_time, duration_min, downtime_category (Planned / Unplanned), reason_code, shift, est_lost_units, est_loss_inr
- **shift_production:** machine_id, date, shift, scheduled_min, planned_downtime_min, unplanned_downtime_min, run_min, units_total, units_defective, avg_temp_c, avg_vibration_mm_s

## KPI definitions
- **Availability** = Run time / (Scheduled time - Planned downtime)
- **Performance** = (Units produced x Ideal cycle time) / Run time
- **Quality** = Good units / Total units
- **OEE** = Availability x Performance x Quality
- **MTBF** = Run hours / Number of failures (mechanical + electrical)
- **MTTR** = Failure downtime hours / Number of failures
- **Machine health:** Unhealthy if temperature > 85 or vibration > 4.5; Warning if temperature > 75 or vibration > 3.5

## Dashboard views
Pareto of downtime reasons, downtime trend with moving average and anomaly flag, machine OEE vs target, shift comparison, day-of-week heatmap, reason x line treemap, health scatter, MTBF / MTTR by machine, event detail table.
Interactivity: filter, highlight and parameter actions, metric selector, viz-in-tooltip.

## Key findings
_Add your findings here after building the dashboard, using numbers you read off it._

## Screenshots
_Add images to `screenshots/` and link them here._

## Reproduce the data
```bash
pip install -r requirements.txt
python scripts/generate_factory_data.py
```

## Repository structure
```
factory-downtime-analytics/
├── data/            # CSV files (simulated)
├── scripts/         # data generator
├── screenshots/     # dashboard images
├── requirements.txt
└── README.md
```
