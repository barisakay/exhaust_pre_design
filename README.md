# exhaust_pre_design

GUI-based desktop calculator for engine exhaust **transmission loss** (acoustic attenuation) as a function of frequency.

The formulas are ported directly from the accompanying `Transmission loss.xlsx` spreadsheet model.

---

## Features

* **Input fields** – inlet pipe diameter, expansion-chamber diameter, expansion-chamber length, exhaust-gas temperature, number of engine cylinders.
* **Frequency modes**
  * *Single base frequency* – computes the 7 engine-firing harmonics (orders 1–7) and displays transmission loss for each.
  * *Frequency sweep* – evaluates transmission loss at every frequency from `start` to `stop` with a user-defined `step`.
* **Results table** – frequency vs. transmission loss (dB).
* **Plot** – live attenuation-vs-frequency graph (matplotlib embedded in Qt).
* **CSV export** – save the current table to a `.csv` file.

---

## Physics

For an expansion-chamber muffler the transmission loss at frequency *f* is:

```
c   = sqrt(1.4 × 273 × (273 + T_celsius))   [m/s]
m   = d_chamber / d_inlet
B   = 0.25 × (m − 1/m)²
k   = 2π × f / c                             [rad/m]
TL  = 10 × log₁₀(1 + B × sin²(k × L × 180/π))   [dB]
```

These match the per-column formulas in rows 9–12 of `Transmission loss.xlsx`.

---

## Getting started

### Prerequisites

* Python 3.10 or newer

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the GUI

```bash
python -m exhaust_calc_gui.main
```

or simply:

```bash
python exhaust_calc_gui/main.py
```

---

## Running tests

```bash
pip install pytest
pytest tests/ -v
```

The test suite (`tests/test_engine.py`) includes:
* Speed-of-sound reference against the spreadsheet value at 450 °C.
* Transmission loss values at all 7 engine orders, verified against spreadsheet cells D12–J12.
* Sweep validity and edge-case checks.

---

## Project layout

```
exhaust_calc_gui/
    __init__.py
    engine.py      # Pure-math calculation engine (no Qt dependency)
    gui.py         # PySide6 GUI
    main.py        # Entry point

tests/
    test_engine.py

requirements.txt
Transmission loss.xlsx   # Original spreadsheet model
```

---

## License

See [LICENSE](LICENSE).