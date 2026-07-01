"""Tests for the Visualization value object."""

from aiweather.visualization import HtmlNormalizer, Visualization, VisualizationStatus


def test_from_raw_normalizes_once():
    normalizer = HtmlNormalizer()
    raw = "```html\n<h1>Hi</h1>\n```"
    viz = Visualization.from_raw(raw, normalizer)
    assert viz.raw == raw
    assert viz.normalized == "<h1>Hi</h1>"
    assert viz.normalized != viz.raw


def test_visualization_is_frozen():
    viz = Visualization(raw="a", normalized="b")
    try:
        viz.raw = "c"  # type: ignore[misc]
    except Exception as e:
        assert isinstance(e, (AttributeError,))
    else:
        raise AssertionError("Visualization should be frozen")


def test_status_values_are_stable_strings():
    assert VisualizationStatus.UP_TO_DATE.value == "up_to_date"
    assert VisualizationStatus.OUTDATED.value == "outdated"
    assert VisualizationStatus.GENERATING.value == "generating"
