# Data Dictionary

## Instruments

`_id`: canonical internal ID; `isin`: primary security identifier; `symbol`: exchange ticker; `name`: display name; `exchange`; `asset_type`; `sector`; `currency`; `provider`; `mapping_status`.

## Prices

`instrument_id`, `date` (exchange date), `open`, `high`, `low`, `close` (unadjusted close used for current valuation), `adjusted_close` (historical return series basis if provider defines it), `volume`, `dividend`, `split_factor`, `currency`, `provider`, `source_url`, `retrieved_at`, `usage_status`, `validation_status`.

## Mutual funds

Scheme: `scheme_code`, `scheme_name`, `fund_house`, `plan_type`, `option_type`, `isin`. NAV row: `scheme_code`, `date`, `nav`, `currency`, `provider`, `retrieved_at`. Snapshot: `scheme_code`, `reporting_date`, `publication_date`, `retrieved_at`, `source_url`. Constituent: `scheme_code`, `reporting_date`, `security_name`, `security_isin`, `mapped_instrument_id`, `weight_percentage`, `asset_class`, `sector`, `source_url`.

## Benchmark

`benchmark_id`, `name`, `date`, `index_value`, `return_type` (must identify TRI vs price return), `provider`, `retrieved_at`, `source_url`.

Financial values are stored as MongoDB Decimal128 or integer minor units. Dates are explicit exchange/business dates. Do not infer a missing security mapping from a name alone.
