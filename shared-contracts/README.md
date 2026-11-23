# Shared contracts 1.0.0 — candidate for agreement

Neutral package for all three Childhood Navigator modules. No app imports or ML dependencies. `regions.csv` is copied from the existing regional analytics contract; it is not independently reinvented. Region identifiers are RU-01…RU-99, plus RU and FD-* aggregate rows; these codes are platform keys, not a claim that they are ISO codes. Territory coverage and effective dates require platform-owner review.

`region-mapping.csv` gives an explicit one-to-one mapping from all 83 existing media ISO identifiers. Migration 0003 inserts canonical rows and remaps media relationships without changing post IDs, source IDs, review records or deleting the old dictionary. Back up and check for conflicting preexisting links before applying to an integrated database. Migration fails on duplicate links rather than discarding manual labels. Canonical source UUID generation is in identity.py; existing source IDs from other modules must be retained in a future alias registry until a reviewed source mapping is agreed.

Schemas describe core.regions, core.topics and core.sources. source_id = UUIDv5(documented namespace, source-type + normalized URL), post_id = UUIDv5(source_id, NFC external ID). Algorithm and test vectors are shared unchanged by adapters. Tests verify mapping completeness, uniqueness and unchanged existing UUIDs.

Status: technical proposal, **not ratified** by the three module owners. No changes were made to the regional module or any existing remote repository. This package can be copied unchanged; adoption needs an explicit contract decision and source alias migration for legacy regional UUIDs.
