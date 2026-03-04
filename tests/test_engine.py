"""
Unit tests for the exhaust transmission loss calculation engine.

Reference values are taken directly from the "Transmission loss.xlsx" spreadsheet
(sheet "Sayfa1") with the default parameter set:

    inlet_diameter   = 0.06 m
    exhaust_diameter = 0.48 m
    exhaust_length   = 0.40 m
    temperature      = 450 °C
    num_cylinders    = 6
    base_frequency   = 50 Hz   →  first-order freq = 300 Hz

Spreadsheet cells used as expected values (read back with data_only=True):
    D12 = 6.582862721   (1st order, 300 Hz)
    E12 = 10.77542503   (2nd order, 600 Hz)
    F12 = 12.15395971   (3rd order, 900 Hz)
    G12 = 11.41677992   (4th order, 1200 Hz)
    H12 = 8.204604539   (5th order, 1500 Hz)
    I12 = 1.239805303   (6th order, 1800 Hz)
    J12 = 4.54807425    (7th order, 2100 Hz)
    K18 = 525.6715705   (speed of sound at 450 °C)
"""

from __future__ import annotations

import math
import pytest

from exhaust_calc_gui.engine import (
    ExhaustParams,
    TLResult,
    compute_harmonics,
    compute_sweep,
    speed_of_sound,
    transmission_loss,
)

# ---------------------------------------------------------------------------
# Shared test fixture
# ---------------------------------------------------------------------------

DEFAULT_PARAMS = ExhaustParams(
    inlet_diameter=0.06,
    exhaust_diameter=0.48,
    exhaust_length=0.40,
    temperature=450.0,
    num_cylinders=6,
)

TOLERANCE = 1e-4  # dB


# ---------------------------------------------------------------------------
# speed_of_sound
# ---------------------------------------------------------------------------


def test_speed_of_sound_reference():
    """Speed of sound must match spreadsheet cell K18 at 450 °C."""
    c = speed_of_sound(450.0)
    assert abs(c - 525.6715705) < 1e-4


def test_speed_of_sound_zero_celsius():
    """At 0 °C the formula gives sqrt(1.4 * 273 * 273)."""
    expected = math.sqrt(1.4 * 273.0 * 273.0)
    assert abs(speed_of_sound(0.0) - expected) < 1e-9


# ---------------------------------------------------------------------------
# transmission_loss – single frequency
# ---------------------------------------------------------------------------

# (frequency_hz, expected_tl_db) from spreadsheet cells D12–J12
SPREADSHEET_CASES = [
    (300.0, 6.582862721),
    (600.0, 10.77542503),
    (900.0, 12.15395971),
    (1200.0, 11.41677992),
    (1500.0, 8.204604539),
    (1800.0, 1.239805303),
    (2100.0, 4.54807425),
]


@pytest.mark.parametrize("freq, expected", SPREADSHEET_CASES)
def test_transmission_loss_vs_spreadsheet(freq, expected):
    tl = transmission_loss(freq, DEFAULT_PARAMS)
    assert abs(tl - expected) < TOLERANCE, (
        f"freq={freq} Hz: got {tl:.8f} dB, expected {expected:.8f} dB"
    )


def test_transmission_loss_zero_at_zero_sin():
    """When sin(k*L*(180/pi)) == 0, TL should equal 0 dB."""
    # sin(0) == 0 → TL = 10*log10(1) = 0
    tl = transmission_loss(0.0, DEFAULT_PARAMS)
    assert abs(tl) < 1e-9


# ---------------------------------------------------------------------------
# compute_harmonics
# ---------------------------------------------------------------------------


def test_compute_harmonics_count():
    results = compute_harmonics(50.0, DEFAULT_PARAMS)
    assert len(results) == 7


def test_compute_harmonics_frequencies():
    """First-order freq = base * cylinders; subsequent orders are multiples."""
    results = compute_harmonics(50.0, DEFAULT_PARAMS)
    for n, r in enumerate(results, start=1):
        assert abs(r.frequency - 300.0 * n) < 1e-9, (
            f"order {n}: expected {300.0 * n} Hz, got {r.frequency} Hz"
        )


def test_compute_harmonics_tl_values():
    """TL values for default params must match the spreadsheet row 12."""
    results = compute_harmonics(50.0, DEFAULT_PARAMS)
    for r, (freq, expected) in zip(results, SPREADSHEET_CASES):
        assert abs(r.tl_db - expected) < TOLERANCE, (
            f"freq={freq}: got {r.tl_db:.8f}, expected {expected:.8f}"
        )


def test_compute_harmonics_custom_orders():
    results = compute_harmonics(50.0, DEFAULT_PARAMS, num_orders=3)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# compute_sweep
# ---------------------------------------------------------------------------


def test_compute_sweep_basic():
    results = compute_sweep(100.0, 500.0, 100.0, DEFAULT_PARAMS)
    freqs = [r.frequency for r in results]
    assert freqs == pytest.approx([100.0, 200.0, 300.0, 400.0, 500.0])


def test_compute_sweep_single_point():
    results = compute_sweep(300.0, 300.0, 50.0, DEFAULT_PARAMS)
    assert len(results) == 1
    assert abs(results[0].frequency - 300.0) < 1e-9


def test_compute_sweep_tl_matches_single():
    """Each sweep point must match calling transmission_loss directly."""
    results = compute_sweep(300.0, 900.0, 300.0, DEFAULT_PARAMS)
    for r in results:
        expected = transmission_loss(r.frequency, DEFAULT_PARAMS)
        assert abs(r.tl_db - expected) < 1e-12


def test_compute_sweep_invalid_step():
    with pytest.raises(ValueError, match="step_freq"):
        compute_sweep(100.0, 500.0, 0.0, DEFAULT_PARAMS)


def test_compute_sweep_invalid_range():
    with pytest.raises(ValueError, match="start_freq"):
        compute_sweep(500.0, 100.0, 10.0, DEFAULT_PARAMS)


# ---------------------------------------------------------------------------
# TLResult dataclass
# ---------------------------------------------------------------------------


def test_tlresult_fields():
    r = TLResult(frequency=300.0, tl_db=6.58)
    assert r.frequency == 300.0
    assert r.tl_db == 6.58
