import sys
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
FUNCTION_DIR = ROOT_DIR / "backend" / "src" / "functions" / "session-manager"
COMMON_LAYER_DIR = ROOT_DIR / "backend" / "src" / "layers" / "common"

sys.path.insert(0, str(FUNCTION_DIR))
sys.path.insert(0, str(COMMON_LAYER_DIR))

import index as session_manager


def test_parse_datetime_iso_string():
    value = "2026-01-31T12:34:56"
    parsed = session_manager.parse_datetime(value)
    assert parsed == datetime(2026, 1, 31, 12, 34, 56)


def test_parse_datetime_epoch_seconds():
    epoch = 1700000000
    parsed = session_manager.parse_datetime(epoch)
    assert parsed == datetime.utcfromtimestamp(epoch)


def test_parse_datetime_none():
    parsed = session_manager.parse_datetime(None)
    assert parsed is None


def test_calculate_analytics_empty_list():
    analytics = session_manager.calculate_analytics([])
    assert analytics['totalSessions'] == 0
    assert analytics['activeSessions'] == 0
    assert analytics['completedSessions'] == 0
    assert analytics['totalMotionEvents'] == 0


def test_calculate_analytics_with_sessions():
    sessions = [
        {
            'sessionId': 'session-1',
            'status': 'completed',
            'motionEventsCount': 5,
            'durationMinutes': 10.5,
            'startTime': '2026-01-31T10:00:00',
            'playbackStarted': True
        },
        {
            'sessionId': 'session-2',
            'status': 'completed',
            'motionEventsCount': 3,
            'durationMinutes': 5.0,
            'startTime': '2026-01-31T14:00:00',
            'playbackStarted': True
        },
        {
            'sessionId': 'session-3',
            'status': 'active',
            'motionEventsCount': 2,
            'startTime': '2026-01-31T18:00:00',
            'playbackStarted': False
        }
    ]
    
    analytics = session_manager.calculate_analytics(sessions)
    
    assert analytics['totalSessions'] == 3
    assert analytics['activeSessions'] == 1
    assert analytics['completedSessions'] == 2
    assert analytics['totalMotionEvents'] == 10
    assert analytics['totalDurationMinutes'] == 15.5
    assert analytics['averageDurationMinutes'] == 7.75
    assert analytics['averageMotionEventsPerSession'] == round(10 / 3, 2)
    assert analytics['sessionsWithPlayback'] == 2
