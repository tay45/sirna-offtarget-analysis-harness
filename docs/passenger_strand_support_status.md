# Passenger Strand Support Status

Passenger-strand search is unsupported in transcript targetability.

The default `search_passenger = false` is accepted. A labeled passenger sequence can be
preserved in the siRNA sequence record, but no passenger targetability artifacts are
generated. Setting `search_passenger = true` fails configuration validation with an
unsupported passenger-search error.
