from __future__ import annotations

from sirna_offtarget.pathway.providers.omnipath import OmniPathProvider
from sirna_offtarget.pathway.providers.panther import PantherProvider
from sirna_offtarget.pathway.providers.reactome_analysis import ReactomeAnalysisProvider
from sirna_offtarget.pathway.providers.reactome_content import ReactomeContentProvider
from sirna_offtarget.pathway.providers.reactome_fi import ReactomeFIProvider
from sirna_offtarget.pathway.providers.signor import SignorProvider


def provider_registry() -> dict[str, object]:
    return {
        "reactome": ReactomeAnalysisProvider(),
        "reactome_analysis": ReactomeAnalysisProvider(),
        "panther": PantherProvider(),
        "omnipath": OmniPathProvider(),
        "signor": SignorProvider(),
        "reactome-fi": ReactomeFIProvider(),
        "reactome_fi": ReactomeFIProvider(),
        "reactome_content": ReactomeContentProvider(),
    }


def get_provider(name: str) -> object:
    normalized = name.strip().lower().replace("_", "-")
    registry = provider_registry()
    if normalized in registry:
        return registry[normalized]
    alt = normalized.replace("-", "_")
    if alt in registry:
        return registry[alt]
    raise KeyError(f"unknown pathway provider {name!r}")
