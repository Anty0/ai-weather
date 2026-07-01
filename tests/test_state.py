"""Tests for the passive StateService."""

from aiweather.state import StateService
from aiweather.visualization import Visualization, VisualizationStatus


def test_install_initial_state_seeds_status():
    state = StateService()
    viz = {"Model One": Visualization(raw="r", normalized="n")}
    state.install_initial_state("2026-07-01T12:00:00+00:00", {"temp": 1}, viz)

    assert state.current_timestamp == "2026-07-01T12:00:00+00:00"
    assert state.current_weather == {"temp": 1}
    assert state.current_visualizations == viz
    assert state.visualization_status["Model One"] == VisualizationStatus.UP_TO_DATE


def test_mark_all_outdated_uses_visualizations_as_source():
    state = StateService()
    state.install_initial_state("t", None, {"Model One": Visualization(raw="r", normalized="n")})
    state.mark_all_outdated()
    assert state.visualization_status["Model One"] == VisualizationStatus.OUTDATED


def test_status_transitions():
    state = StateService()
    state.update_visualization("Model One", Visualization(raw="r", normalized="n"))
    state.mark_generating("Model One")
    assert state.visualization_status["Model One"] == VisualizationStatus.GENERATING
    state.mark_up_to_date("Model One")
    assert state.visualization_status["Model One"] == VisualizationStatus.UP_TO_DATE
