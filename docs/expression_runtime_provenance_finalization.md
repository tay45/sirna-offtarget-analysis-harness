# Expression Runtime Provenance Finalization

Expression V2 records carry the normalization run id, contrast id, identifier
resolution id, source row identifier, source checksums, software declaration,
and identifier snapshot id.

`expression_analysis_result_v2.json` lists canonical artifacts and checksums so
downstream stages can verify they consumed the committed V2 outputs.
