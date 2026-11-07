import pytest

from core.generator import generate_counterfactuals, select_recommendation
from core.model import Application, predict
from visualization import decision_region_figure


@pytest.mark.parametrize("certification", [0, 1])
def test_regions_agree_with_classifier_including_thresholds(certification):
    figure = decision_region_figure(Application(), [], certification)
    accepted = [trace for trace in figure.data if trace.name == "Accepted region"]
    for income in (0, 24.9999, 25, 35):
        for experience in (0, 2.9999, 3, 5):
            in_region = any(
                min(trace.x) <= income <= max(trace.x)
                and min(trace.y) <= experience <= max(trace.y)
                for trace in accepted
            )
            assert in_region == bool(predict(Application(income, experience, certification)))


def test_points_belong_only_to_their_certification_slice():
    original = Application()
    candidates = generate_counterfactuals(original)
    recommendation = select_recommendation(candidates)
    seen = []
    extents = []
    for cert in (0, 1):
        figure = decision_region_figure(original, candidates, cert, recommendation)
        extents.append((tuple(figure.layout.xaxis.range), tuple(figure.layout.yaxis.range)))
        assert any(trace.name == "Original" for trace in figure.data) == (cert == original.certification)
        assert any(trace.name == "Recommended" for trace in figure.data) == (cert == 1)
        for trace in figure.data:
            if trace.name in ("Feasible CF", "Infeasible CF"):
                for (identifier, slice_value, distance), income, experience in zip(trace.customdata, trace.x, trace.y):
                    assert slice_value == cert
                    item = next(candidate for candidate in candidates if candidate.candidate_id == identifier)
                    assert (income, experience) == (item.application.income, item.application.experience)
                    assert distance == item.distance
                    seen.append(identifier)
        # Also verifies the figure is serializable for Streamlit's frontend.
        assert '"data"' in figure.to_json()
    assert sorted(seen) == ["CF1", "CF2", "CF3", "CF4"]
    assert extents[0] == extents[1]


def test_axes_include_large_original_and_candidates():
    original = Application(1000, 0, 0)
    candidates = generate_counterfactuals(original)
    figure = decision_region_figure(original, candidates, 0)
    assert figure.layout.xaxis.range[1] > 1000
    assert figure.layout.yaxis.range[1] > 3


def test_invalid_certification_slice():
    with pytest.raises(ValueError):
        decision_region_figure(Application(), [], 2)
