"""
Exhaust Transmission Loss Calculation Engine.

Ported from the "Transmission loss.xlsx" spreadsheet model.

Formulas (spreadsheet notation → Python):
    c   = sqrt(1.4 * 273 * (273 + T))           speed of sound in exhaust gas [m/s]
    m   = d_exhaust / d_inlet                    diameter ratio [-]
    B   = 0.25 * (m - 1/m)^2                    expansion factor [-]
    k   = 2*pi*f / c                             wave number [rad/m]
    TL  = 10 * log10(1 + B * sin(k*L)^2)            transmission loss [dB]
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List


@dataclass
class ExhaustParams:
    """All physical inputs for the exhaust system."""

    inlet_diameter: float    # metres – pipe entering the expansion chamber
    exhaust_diameter: float  # metres – expansion chamber (muffler) diameter
    exhaust_length: float    # metres – expansion chamber length
    temperature: float       # degrees Celsius – exhaust gas temperature
    num_cylinders: int       # number of engine cylinders


@dataclass
class TLResult:
    """Single transmission-loss data point."""

    frequency: float   # Hz
    tl_db: float       # dB


def speed_of_sound(temperature_celsius: float) -> float:
    """Return exhaust-gas speed of sound [m/s] for the given temperature.

    Formula replicates spreadsheet cell K18:
        c = sqrt(1.4 * 273 * (273 + T_celsius))
    """
    return math.sqrt(1.4 * 273.0 * (273.0 + temperature_celsius))


def transmission_loss(frequency: float, params: ExhaustParams) -> float:
    """Return transmission loss [dB] at *frequency* [Hz] for *params*.

    Replicates the per-column formulas in rows 9–12 of the spreadsheet.
    """
    c = speed_of_sound(params.temperature)
    m = params.exhaust_diameter / params.inlet_diameter
    b = 0.25 * (m - 1.0 / m) ** 2
    k = 2.0 * math.pi * frequency / c
    sin2 = math.sin(k * params.exhaust_length) ** 2
    return 10.0 * math.log10(1.0 + b * sin2)


def compute_harmonics(
    base_frequency: float,
    params: ExhaustParams,
    num_orders: int = 7,
) -> List[TLResult]:
    """Compute TL for engine firing harmonics.

    The first-order frequency = base_frequency * num_cylinders.
    Subsequent orders are integer multiples thereof.
    Replicates the column-by-column layout of the spreadsheet (D–J).
    """
    first_order = base_frequency * params.num_cylinders
    results: List[TLResult] = []
    for n in range(1, num_orders + 1):
        freq = first_order * n
        results.append(TLResult(frequency=freq, tl_db=transmission_loss(freq, params)))
    return results


def compute_sweep(
    start_freq: float,
    stop_freq: float,
    step_freq: float,
    params: ExhaustParams,
) -> List[TLResult]:
    """Compute TL for every frequency in [start_freq, stop_freq] at *step_freq* intervals."""
    if step_freq <= 0:
        raise ValueError("step_freq must be positive")
    if start_freq > stop_freq:
        raise ValueError("start_freq must be <= stop_freq")

    results: List[TLResult] = []
    freq = start_freq
    while freq <= stop_freq + 1e-9:  # small tolerance for floating-point endpoint
        results.append(TLResult(frequency=freq, tl_db=transmission_loss(freq, params)))
        freq = round(freq + step_freq, 10)
    return results
