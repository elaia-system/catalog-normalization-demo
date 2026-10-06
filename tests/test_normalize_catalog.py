import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalog', ROOT / 'src/normalize_catalog.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class CatalogTests(unittest.TestCase):
    def run_rows(self, rows):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name)
        with (path / 'input.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(catalog.FIELDS)
            writer.writerows(rows)
        catalog.normalize(path / 'input.csv', path / 'out')
        def read(filename):
            with (path / 'out' / filename).open(encoding='utf-8', newline='') as stream:
                return list(csv.DictReader(stream))
        return read('import_ready.csv'), read('exceptions.csv')

    def test_deterministic_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            catalog.normalize(ROOT / 'input/synthetic_catalog.csv', folder / 'a')
            catalog.normalize(ROOT / 'input/synthetic_catalog.csv', folder / 'b')
            for name in ['import_ready.csv', 'exceptions.csv']:
                self.assertEqual((folder / 'a' / name).read_bytes(), (folder / 'b' / name).read_bytes())

    def test_safe_normalization(self):
        safe, errors = self.run_rows([[' X ', ' Title ', '19,99', ' ACME ', ' shirts ', ' size ', ' M '],
                                     ['Y', 'Mug', '$12.50', 'Acme', 'Mugs', '', '']])
        self.assertEqual(errors, [])
        self.assertEqual(safe[0], dict(zip(catalog.FIELDS, ['X', 'Title', '19.99', 'Acme', 'Shirts', 'Size', 'M'])))
        self.assertEqual(safe[1]['price'], '12.50')

    def test_required_field_and_reason(self):
        safe, errors = self.run_rows([['X', '', '15.00', 'Acme', 'Accessories', '', '']])
        self.assertEqual(safe, [])
        self.assertEqual(errors, [{'row_id': '1', 'sku': 'X', 'reason_code': 'MISSING_REQUIRED', 'field': 'title', 'observed_value': ''}])

    def test_invalid_prices(self):
        prices = ['N/A', '-1.00', '1,000.00', 'NaN', '1e2', '12.5', '€12.50']
        safe, errors = self.run_rows([[str(i), 'Mug', p, 'Acme', 'Mugs', '', ''] for i, p in enumerate(prices)])
        self.assertEqual(safe, [])
        self.assertEqual([e['reason_code'] for e in errors], ['INVALID_PRICE'] * len(prices))

    def test_duplicate_sku_variants_and_conflicts_rejected(self):
        for second in [['X', 'T', '19.99', 'ACME', 'Shirts', 'Size', 'L'],
                       ['X', 'Other', '20.00', 'Acme', 'Mugs', 'Size', 'M'],
                       ['X', 'T', '19.99', 'Acme', 'Shirts', 'Size', 'M']]:
            safe, errors = self.run_rows([[' X ', 'T', '19.99', 'Acme', 'Shirts', 'Size', 'M'], second])
            self.assertEqual(safe, [])
            self.assertEqual([e['reason_code'] for e in errors], ['DUPLICATE_SKU_AMBIGUOUS'] * 2)

    def test_unknown_category_and_partial_option(self):
        safe, errors = self.run_rows([['X', 'T', '19', 'Acme', 'Unknown', 'Size', ''],
                                     ['Y', 'T', '19', 'Acme', 'Mugs', 'Mystery', 'A']])
        self.assertEqual(safe, [])
        self.assertEqual([e['reason_code'] for e in errors], ['UNKNOWN_CATEGORY', 'AMBIGUOUS_VARIANT', 'UNKNOWN_OPTION'])

    def test_invalid_schema_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'input.csv').write_text('sku,title\nX,T\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'INVALID_SCHEMA'):
                catalog.normalize(path / 'input.csv', path / 'out')
            self.assertFalse((path / 'out').exists())

    def test_invalid_row_width_failure(self):
        for bad_row in ['X,T,19,Acme,Mugs,\n', 'X,T,19,Acme,Mugs,,,EXTRA\n']:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)
                (path / 'input.csv').write_text(','.join(catalog.FIELDS) + '\n' + bad_row, encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'INVALID_SCHEMA'):
                    catalog.normalize(path / 'input.csv', path / 'out')
                self.assertFalse((path / 'out').exists())


if __name__ == '__main__':
    unittest.main()
