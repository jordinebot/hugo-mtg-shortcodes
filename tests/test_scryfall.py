import importlib.util
import json
import io
import gzip
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('bulk', Path(__file__).parents[1] / 'scripts/prepare-scryfall.py')
bulk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bulk)


def card(id, name='Fire // Ice', set='mh2', date='2021-01-01'):
    return dict(object='card', id=id, name=name, set=set, released_at=date,
                lang='en', games=['paper'], card_faces=[{'name': 'Fire'}, {'name': 'Ice'}])


def manifest(metadata):
    return {'data': [dict(metadata, type=kind) for kind in ('default_cards', 'oracle_cards')]}


class BulkTests(unittest.TestCase):
    def test_printings_faces_and_order(self):
        cards = [card('old', set='apc', date='2001-01-01'), card('new')]
        index = bulk.build_index(cards)
        self.assertEqual(index, bulk.build_index(reversed(cards)))
        self.assertEqual(index['names']['fire // ice'], 'new')
        self.assertEqual(index['names']['ice'], 'new')
        self.assertEqual(index['names']['fire|apc'], 'old')
        self.assertNotIn('fire|xxx', index['names'])

    def test_download_formats_and_flavor_names(self):
        special = card('skin')
        special['flavor_name'] = 'Alternate Name'
        for jsonl in (True, False):
            with self.subTest(jsonl=jsonl), tempfile.TemporaryDirectory() as tmp:
                metadata = {'updated_at': '2026-11-03',
                            'jsonl_download_uri' if jsonl else 'download_uri':
                            'https://example.com/cards.jsonl.gz' if jsonl else 'https://example.com/cards.json'}
                payload = gzip.compress((json.dumps(special) + '\n').encode()) if jsonl else json.dumps([special]).encode()
                with patch.object(bulk, 'request', side_effect=[io.BytesIO(json.dumps(manifest(metadata)).encode()), io.BytesIO(payload), io.BytesIO(payload)]):
                    snapshot = bulk.prepare(Path(tmp))
                self.assertEqual(json.loads(snapshot.read_text())['names']['alternate name'], 'skin')

    def test_bad_download_preserves_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            data = bulk.build_index([card('old')])
            bulk.atomic_json(path / 'index.json', data)
            metadata = {'updated_at': 'new', 'download_uri': 'https://example.com/cards.json'}
            with patch.object(bulk, 'request', side_effect=[io.BytesIO(json.dumps(manifest(metadata)).encode()), io.BytesIO(b'invalid')]):
                bulk.prepare(path)
            self.assertEqual(json.loads((path / 'index.json').read_text()), data)

    def test_oracle_overrides_defaults_preserves_aliases_and_prefers_exact_name(self):
        old, new = card('old', set='apc'), card('new')
        new['flavor_name'] = 'Alternate Name'
        index = bulk.build_index([old, new])
        exact = card('exact', name='Lightning Bolt')
        face = card('face', name='Other Card')
        face['card_faces'] = [{'name': 'Lightning Bolt'}, {'name': 'Other Face'}]
        bulk.apply_oracle(index, [old, exact, face])
        self.assertEqual(index['names']['fire // ice'], 'old')
        self.assertEqual(index['names']['ice'], 'old')
        self.assertEqual(index['names']['fire|mh2'], 'new')
        self.assertEqual(index['names']['alternate name'], 'new')
        self.assertEqual(index['names']['alternate name|mh2'], 'new')
        self.assertEqual(index['names']['lightning bolt'], 'exact')
        self.assertEqual(index['names']['other face'], 'face')
        with self.assertRaises(ValueError):
            bulk.apply_oracle(index, [])

    def test_old_schema_refreshes_and_survives_network_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            data = bulk.build_index([card('a')])
            data.update(schema=1, checked_at=bulk.time.time())
            bulk.atomic_json(path / 'index.json', data)
            with patch.object(bulk, 'request', side_effect=RuntimeError('HTTP 429')) as request:
                bulk.prepare(path)
                self.assertEqual(request.call_count, 1)
            self.assertEqual(json.loads((path / 'index.json').read_text()), data)

    def test_oracle_failure_does_not_publish_partial_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            data = bulk.build_index([card('old')])
            bulk.atomic_json(path / 'index.json', data)
            metadata = {'updated_at': 'new', 'download_uri': 'https://example.com/cards.json'}
            with patch.object(bulk, 'request', side_effect=[
                    io.BytesIO(json.dumps(manifest(metadata)).encode()),
                    io.BytesIO(json.dumps([card('new')]).encode()), RuntimeError('HTTP 429')]):
                bulk.prepare(path)
            self.assertEqual(json.loads((path / 'index.json').read_text()), data)

    def test_empty_bulk_rejected(self):
        with self.assertRaises(ValueError):
            bulk.build_index([])

    def test_fresh_cache_never_calls_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            data = bulk.build_index([card('a')])
            data['checked_at'] = bulk.time.time()
            bulk.atomic_json(path / 'index.json', data)
            with patch.object(bulk, 'request', side_effect=AssertionError('network')):
                self.assertEqual(bulk.prepare(path), path / 'index.json')

    def test_429_uses_stale_cache_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            data = bulk.build_index([card('a')])
            bulk.atomic_json(path / 'index.json', data)
            with patch.object(bulk, 'request', side_effect=RuntimeError('HTTP 429')) as request:
                bulk.prepare(path)
                self.assertEqual(request.call_count, 1)
            self.assertEqual(json.loads((path / 'index.json').read_text()), data)

    def test_no_cache_fails_on_429(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(bulk, 'request', side_effect=RuntimeError('HTTP 429')):
                with self.assertRaisesRegex(RuntimeError, 'no valid cached snapshot'):
                    bulk.prepare(Path(tmp))


if __name__ == '__main__':
    unittest.main()
