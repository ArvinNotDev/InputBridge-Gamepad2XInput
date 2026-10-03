import json

from phone_mouse import (
    DEFAULT_MOUSE_SENSITIVITY,
    MouseGestureTracker,
    load_mouse_preferences,
    save_mouse_preferences,
)


def test_mouse_tracker_reports_cursor_motion_and_distinguishes_drag_from_tap():
    tracker = MouseGestureTracker(scroll_step=40, tap_slop=8, tap_timeout=0.25)

    assert tracker.begin("finger", 10, 10, now=1.0)
    assert tracker.move("finger", 14, 10, 4, 0) == ("move", 4.0, 0.0)
    assert tracker.end("finger", now=1.1)

    assert tracker.begin("finger", 10, 10, now=2.0)
    assert tracker.move("finger", 30, 10, 20, 0) == ("move", 20.0, 0.0)
    assert not tracker.end("finger", now=2.1)


def test_mouse_tracker_converts_two_finger_swipes_to_scroll_not_clicks():
    tracker = MouseGestureTracker(scroll_step=40)
    assert tracker.begin("one", 0, 100, now=1.0)
    assert tracker.begin("two", 20, 100, now=1.01)

    assert tracker.move("one", 0, 140, 0, 40) is None
    assert tracker.move("two", 20, 140, 0, 40) == ("scroll", 1)
    assert not tracker.end("one", now=1.1)
    assert not tracker.end("two", now=1.1)


def test_mouse_tracker_rejects_a_third_concurrent_touch():
    tracker = MouseGestureTracker()
    assert tracker.begin(1, 0, 0, now=1.0)
    assert tracker.begin(2, 10, 0, now=1.0)
    assert not tracker.begin(3, 20, 0, now=1.0)


def test_mouse_preferences_round_trip_and_sanitize(tmp_path):
    settings_path = tmp_path / "mouse_settings.json"
    save_mouse_preferences(2.75, False, settings_path)

    assert load_mouse_preferences(settings_path) == {
        "sensitivity": 2.75,
        "tap_to_click": False,
    }

    settings_path.write_text(
        json.dumps({"sensitivity": 500, "tap_to_click": "yes"}),
        encoding="utf-8",
    )
    assert load_mouse_preferences(settings_path) == {
        "sensitivity": 4.0,
        "tap_to_click": True,
    }

    settings_path.write_text("not json", encoding="utf-8")
    assert load_mouse_preferences(settings_path) == {
        "sensitivity": DEFAULT_MOUSE_SENSITIVITY,
        "tap_to_click": True,
    }
