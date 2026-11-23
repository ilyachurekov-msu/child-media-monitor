"""Explicit opt-in network operation, never invoked by application startup or CI."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--model', choices=['e5', 'sentiment'], required=True)
parser.add_argument('--license-reviewed', action='store_true')
args = parser.parse_args()
if args.model == 'sentiment' and not args.license_reviewed:
    parser.error('Confirm weight license review before downloading sentiment weights')
from huggingface_hub import snapshot_download
name = {'e5': 'intfloat/multilingual-e5-small', 'sentiment': 'cointegrated/rubert-tiny-sentiment-balanced'}[args.model]
lock = json.loads(Path('contracts/models.lock.json').read_text())
target = Path('models', args.model)
snapshot_download(name, revision=lock[name]['revision'], local_dir=str(target),
                  allow_patterns=['*.json', '*.txt', '*.model', '*.safetensors', '1_Pooling/*'])
(target / 'PROVENANCE.json').write_text(json.dumps({'model': name, 'revision': lock[name]['revision']}))
print('Local snapshot ready; configure model version to', lock[name]['revision'])
