# BATMAN Tuning Historical Data Cache

This directory defines the immutable cache contract for BATMAN Tuning V1. The tuning engine must consume cached data and must not silently download replacement history during analysis runs.

## Required datasets

- manifest.json — provenance, hashes, coverage, schema version, source, and build timestamp.
- sessions.parquet — NIFTY trading-session calendar and daily closes.
- option_quotes.parquet — timestamped option contract observations required for selected BATMAN legs, including expiry, strike, option type, OHLC and/or executable bid/ask fields.
- intraday_underlying.parquet — intraday NIFTY observations needed for timing/execution alignment.

The cache may be stored as GitHub Actions artifacts or another immutable repository-approved cache mechanism when the raw files are too large for Git. The manifest must remain versioned in this branch and identify the exact artifact/source and SHA-256 hashes.

## Fail-closed rule

T1-T6 must stop with a data-availability error if the manifest is missing, coverage is incomplete, hashes do not match, timestamps are ambiguous, or required bid/ask/intraday fields are absent. A workflow must never substitute live/current data for missing historical observations.

## Current state

The parent BATMAN backfill produced a reconstructed paper-entry record using NSE UDiFF close prices, but explicitly noted that historical bid/ask quotes were unavailable. That record is NOT sufficient for prospective-style historical tuning and is not accepted as the T1 cache.
