import sys
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
FUNCTION_DIR = ROOT_DIR / "backend" / "src" / "functions" / "timeout-checker"
COMMON_LAYER_DIR = ROOT_DIR / "backend" / "src" / "layers" / "common"

sys.path.insert(0, str(FUNCTION_DIR))
sys.path.insert(0, str(COMMON_LAYER_DIR))

import index as timeout_checker


def test_parse_datetime_iso_string():
    value = "2026-01-31T12:34:56"
    parsed = timeout_checker.parse_datetime(value)
    assert parsed == datetime(2026, 1, 31, 12, 34, 56)


def test_parse_datetime_epoch_seconds():
    epoch = 1700000000
    parsed = timeout_checker.parse_datetime(epoch)
    assert parsed == datetime.utcfromtimestamp(epoch)


def test_should_timeout_true_when_elapsed_exceeds():
    last_motion = datetime(2026, 1, 1, 0, 0, 0)
    now = datetime(2026, 1, 1, 0, 6, 0)
    assert timeout_checker.should_timeout(last_motion, 5, now) is True


def test_should_timeout_false_when_elapsed_under_limit():
    last_motion = datetime(2026, 1, 1, 0, 0, 0)
    now = datetime(2026, 1, 1, 0, 4, 0)
    assert timeout_checker.should_timeout(last_motion, 5, now) is False


def test_calculate_session_duration_minutes():
    start = datetime(2026, 1, 1, 0, 0, 0)
    end = datetime(2026, 1, 1, 0, 10, 30)
    duration = timeout_checker.calculate_session_duration_minutes(start, end)
    assert duration == 10.5
