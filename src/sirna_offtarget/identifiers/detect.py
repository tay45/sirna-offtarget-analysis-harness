from __future__ import annotations

import re

ENSEMBL_GENE = re.compile(r"^ENS[A-Z]*G\d+(?:\.\d+)?$")
ENSEMBL_TRANSCRIPT = re.compile(r"^ENS[A-Z]*T\d+(?:\.\d+)?$")
UNIPROT = re.compile(r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9])$")
REACTOME = re.compile(r"^R-[A-Z]{3}-\d+$")
SIGNOR = re.compile(r"^SIGNOR-[A-Za-z0-9_-]+$")


def detect_identifier_type(identifier: str) -> str:
    value = identifier.strip()
    if not value:
        return "invalid"
    if ENSEMBL_GENE.match(value):
        return "ensembl_gene_id"
    if ENSEMBL_TRANSCRIPT.match(value):
        return "ensembl_transcript_id"
    if REACTOME.match(value):
        return "reactome_stable_id"
    if SIGNOR.match(value):
        return "signor_entity_id"
    if value.isdigit():
        return "entrez_gene_id"
    if UNIPROT.match(value):
        return "uniprot_accession"
    if ":" in value:
        return "provider_specific_id"
    return "hgnc_symbol"
