"""Bounded synthetic catalog demo: explicit rules, no inference or network."""
import csv
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

FIELDS = ['sku', 'title', 'price', 'vendor', 'product_type', 'option1_name', 'option1_value']
EXCEPTION_FIELDS = ['row_id', 'sku', 'reason_code', 'field', 'observed_value']
VENDORS = {'acme': 'Acme'}
CATEGORIES = {'shirts': 'Shirts', 'mugs': 'Mugs', 'accessories': 'Accessories'}
OPTIONS = {'size': 'Size', 'color': 'Color'}
PRICE = re.compile(r'(?:[0-9]+(?:\.[0-9]{2})?|[0-9]+,[0-9]{2}|\$[0-9]+\.[0-9]{2})\Z')


def normalize(input_path, output_dir):
    """Write deterministic outputs; row_id is one-based data-row number."""
    with Path(input_path).open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames != FIELDS:
            raise ValueError('INVALID_SCHEMA: exact ordered input headers required')
        rows = list(reader)
    # Validate the whole shape before producing either output.
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError('INVALID_SCHEMA: row width does not match header')
    sku_counts = Counter(row['sku'].strip() for row in rows if row['sku'].strip())
    safe, exceptions = [], []
    for row_id, raw in enumerate(rows, 1):
        row = {key: value.strip() for key, value in raw.items()}
        reasons = []

        def reject(code, field):
            reasons.append({'row_id': row_id, 'sku': row['sku'], 'reason_code': code,
                            'field': field, 'observed_value': raw[field]})

        for field in ['sku', 'title', 'price', 'vendor', 'product_type']:
            if not row[field]:
                reject('MISSING_REQUIRED', field)
        if row['price']:
            if PRICE.fullmatch(row['price']):
                row['price'] = format(Decimal(row['price'].removeprefix('$').replace(',', '.')), '.2f')
            else:
                reject('INVALID_PRICE', 'price')
        for field, mapping, code in [('vendor', VENDORS, 'UNKNOWN_VENDOR'),
                                     ('product_type', CATEGORIES, 'UNKNOWN_CATEGORY')]:
            if row[field]:
                value = mapping.get(row[field].casefold())
                if value is None:
                    reject(code, field)
                else:
                    row[field] = value
        name, value = row['option1_name'], row['option1_value']
        if bool(name) != bool(value):
            reject('AMBIGUOUS_VARIANT', 'option1_name' if not name else 'option1_value')
        elif name:
            if name.casefold() not in OPTIONS:
                reject('UNKNOWN_OPTION', 'option1_name')
            else:
                row['option1_name'] = OPTIONS[name.casefold()]
        if row['sku'] and sku_counts[row['sku']] > 1:
            reject('DUPLICATE_SKU_AMBIGUOUS', 'sku')
        if reasons:
            exceptions.extend(reasons)
        else:
            safe.append(row)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, fields, records in [('import_ready.csv', FIELDS, safe),
                                     ('exceptions.csv', EXCEPTION_FIELDS, exceptions)]:
        with (output_dir / filename).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(records)
    return len(safe), len(exceptions)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    count, issues = normalize(root / 'input/synthetic_catalog.csv', root / 'output')
    print(f'Safe rows: {count}; exception reasons: {issues}')
