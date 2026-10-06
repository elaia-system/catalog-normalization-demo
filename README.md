# Catalog Normalization Demo — Elaia Demo Hall

For ecommerce teams preparing a catalog cleanup or migration: this small,
reproducible example shows how explicit rules can standardize catalog fields
while keeping invalid or ambiguous records out of the accepted dataset.
Review the sample input, normalized output and exception report, then run the
tests locally to verify the result. It is a bounded portfolio demonstration,
not a Shopify connector or a promise of production-store compatibility.

Takes a raw catalog export, applies explicit normalization and validation
rules, produces an import-ready dataset, and separates ambiguous records
for human review.

Synthetic demonstration only.
No production-store access.
No customer or payment data.
No guessing on ambiguous records.

## Run

From this directory, using Python 3.9 or later (standard library only):

```sh
python3 src/normalize_catalog.py
```

Tests: `python3 -m unittest discover -s tests -v`.

## Explicit rules and boundaries

- Input/output schema is the seven ordered columns in the supplied CSV. No inferred Shopify handles, IDs, variants, or field mapping.
- UTF-8 CSV, strict parsing; invalid headers or row widths fail before outputs are written. `row_id` counts data rows starting at 1, not physical file lines.
- Trim outer whitespace in every field; preserve SKU/title/option value case. Only vendor/category/option **names** have enumerated case-insensitive mappings.
- Vendor: `acme` → `Acme`. Categories: `shirts` → `Shirts`, `mugs` → `Mugs`, `accessories` → `Accessories`. Option names: `size` → `Size`, `color` → `Color`. Unlisted values are exceptions, never guessed.
- Required: SKU, title, price, vendor, product type. A pair of option fields must be both present or both absent.
- Price accepts nonnegative ASCII integer, decimal with exactly two fractional digits, decimal-comma with exactly two digits, or dollar-prefixed decimal with exactly two digits. E.g. `19`, `19.99`, `19,99`, `$12.50`. Output has two decimal digits. No grouping separators, negatives, exponent, currency inference or conversion; the dollar prefix is merely a documented synthetic representation.
- Duplicate trimmed SKU rejects **every** record in the group, even when normalized content agrees. M/L with one SKU is not assumed to identify two safe variants. No silent deduplication or winner selection. Unique SKUs with complete explicitly named option pairs are accepted.
- Every rejected record has one or more deterministic reasons: `MISSING_REQUIRED`, `INVALID_PRICE`, `UNKNOWN_VENDOR`, `UNKNOWN_CATEGORY`, `AMBIGUOUS_VARIANT`, `UNKNOWN_OPTION`, `DUPLICATE_SKU_AMBIGUOUS`. Observed values preserve the original field text.
- Stable row order, field order, UTF-8 and LF line endings produce byte-identical outputs for identical input. No time/random values or LLM runtime.

## Supplied result

Five synthetic rows produce one safe row (`MG-002`, price `12.50`, vendor `Acme`, type `Mugs`) and five exception reasons across four rejected rows. Both `TS-001` rows are ambiguous duplicate SKUs; row 4 has missing title and unknown vendor; row 5 has invalid price.

`import_ready.csv` means ready for the **documented demo schema**, not a certified Shopify import. Actual target-store schema, currency, taxonomy, variant identities and client transformation rules require separate evidence and human agreement. This is a small portfolio artifact, not a production system, product, or capability claim. No network dependencies or external integrations.
