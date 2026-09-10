"""Synthetic threshold and majority classifiers; no reference answer imports."""
import argparse
import json
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--context', required=True)
context = json.loads(Path(parser.parse_args().context).read_text(encoding='utf-8'))
spec = json.loads(Path(context['spec']).read_text(encoding='utf-8'))
rows = json.loads(Path(context['inputs']['data']).read_text(encoding='utf-8'))['rows']
by_id = {row['id']: row for row in rows}
majority = Counter(by_id[key]['label'] for key in spec['data_split']['fit_ids']).most_common(1)[0][0]
predictions = [{'id': key, 'prediction': (
    ('positive' if by_id[key]['x'] > 0 else 'negative')
    if spec['method_id'] == 'threshold-main' else majority)}
    for key in spec['data_split']['test_ids']]
(Path(context['output_dir']) / 'predictions.json').write_text(json.dumps(predictions), encoding='utf-8')
