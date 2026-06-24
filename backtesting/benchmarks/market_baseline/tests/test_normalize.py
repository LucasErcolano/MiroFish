from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from normalize import brier, clamp_probability, log_loss, midpoint, relative_probability, scaled_squared_error


def test_brier_basic():
    assert brier(0.75, 1) == 0.0625
    assert brier(0.25, 0) == 0.0625


def test_log_loss_clamps_extremes():
    assert log_loss(1.0, 1) < 0.002
    assert log_loss(0.0, 1) > 6.0


def test_midpoint():
    assert midpoint(1.0, 3.0) == 2.0
    assert midpoint(None, 3.0) is None


def test_relative_probability():
    assert relative_probability(36.5, 44.9) == 0.448403
    assert relative_probability(0, 0) is None


def test_clamp_probability():
    assert clamp_probability(-1) == 0.001
    assert clamp_probability(2) == 0.999


def test_scaled_squared_error():
    assert scaled_squared_error(25.0, 30.0, 100.0) == 0.0025

