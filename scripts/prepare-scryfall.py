#!/usr/bin/env python3
"""Prepare offline Hugo data from Scryfall Default Cards (Python stdlib only)."""
import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request

SCHEMA = 1
HEADERS = {'User-Agent': 'hugo-mtg-shortcodes (+https://github.com/jordinebot/hugo-mtg-shortcodes)', 'Accept': 'application/json'}
FIELDS = ('name', 'scryfall_uri', 'image_uris', 'card_faces', 'mana_cost', 'cmc', 'colors', 'type_line', 'set')


def key(name):
    return name.strip().lower()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        json.dump(value, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(temporary, path)


def request(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120)
    except urllib.error.HTTPError as exc:
        body = exc.read(4096).decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {exc.code} {exc.reason}: {body}; Retry-After={exc.headers.get("Retry-After", "unspecified")}') from exc


def build_index(cards):
    selected = {}
    ranks = {}
    for card in cards:
        if card.get('object') != 'card':
            continue
        # Prefer English, regular paper printings, then newest release; stable tie-break.
        rank = (card.get('lang') == 'en', 'paper' in card.get('games', []),
                not card.get('promo', False), card.get('released_at', ''), card['id'])
        slim = {k: card[k] for k in FIELDS if k in card}
        slim['id'] = card['id']
        names = {card['name'], *(face['name'] for face in card.get('card_faces', []))}
        if card.get('flavor_name'):
            names.add(card['flavor_name'])
        names.update(face['flavor_name'] for face in card.get('card_faces', []) if face.get('flavor_name'))
        for name in names:
            for lookup in (key(name), key(name) + '|' + card['set'].lower()):
                if lookup not in ranks or rank > ranks[lookup]:
                    ranks[lookup] = rank
                    selected[lookup] = slim
    if not selected:
        raise ValueError('Bulk file contains no cards')
    records = {card['id']: {k: card[k] for k in FIELDS if k in card} for card in selected.values()}
    return {'schema': SCHEMA, 'cards': records, 'names': {name: card['id'] for name, card in selected.items()}}


def prepare(cache, refresh=False):
    snapshot = cache / 'index.json'
    cached = None
    try:
        cached = json.loads(snapshot.read_text())
        if cached['schema'] != SCHEMA or not cached['cards'] or not cached['names']:
            cached = None
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if cached and not refresh and time.time() - cached.get('checked_at', 0) < 86400:
        return snapshot
    try:
        with request('https://api.scryfall.com/bulk-data/default_cards') as response:
            metadata = json.load(response)
        if cached and not refresh and cached.get('updated_at') == metadata['updated_at']:
            cached['checked_at'] = time.time()
            atomic_json(snapshot, cached)
            return snapshot
        url = metadata.get('jsonl_download_uri') or metadata['download_uri']
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile() as download:
            print(f'Downloading Scryfall Default Cards: {url}', flush=True)
            with request(url) as response:
                shutil.copyfileobj(response, download)
            download.seek(0)
            if url.endswith('.gz'):
                stream = gzip.GzipFile(fileobj=download)
            else:
                stream = download
            if metadata.get('jsonl_download_uri'):
                cards = (json.loads(line) for line in stream if line.strip())
            else:
                cards = json.load(stream)
            index = build_index(cards)
        index.update(updated_at=metadata['updated_at'], checked_at=time.time())
        atomic_json(snapshot, index)
    except (OSError, EOFError, ValueError, KeyError, RuntimeError) as exc:
        if not cached:
            raise RuntimeError(f'Cannot prepare Scryfall data and no valid cached snapshot exists: {exc}') from exc
        print(f'WARNING: Using cached Scryfall snapshot from {cached.get("updated_at")}: {exc}', file=sys.stderr)
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache-dir', type=Path, default=Path(os.environ.get('SCRYFALL_CACHE_DIR', str(Path.home() / '.cache/hugo-mtg-scryfall-v1'))))
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    snapshot = prepare(args.cache_dir, args.refresh)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as f:
        temporary = Path(f.name)
        with snapshot.open('rb') as source:
            shutil.copyfileobj(source, f)
    os.replace(temporary, args.output)
    print(f'Scryfall offline index ready: {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError) as exc:
        sys.exit(str(exc))
