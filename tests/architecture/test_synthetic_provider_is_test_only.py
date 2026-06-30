from sirna_offtarget.expression.backends.synthetic import SyntheticDemonstrationBackend
from sirna_offtarget.pathway.providers.synthetic import SyntheticPathwayProvider


def test_synthetic_providers_are_marked_test_or_demo_only() -> None:
    assert SyntheticDemonstrationBackend.demonstration_only is True
    assert SyntheticPathwayProvider.test_only is True
