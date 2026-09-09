from copy import deepcopy
import sys

import pytest

from mathmode.evaluators import evaluate
from mathmode.io import read_json, write_json, file_hash
from mathmode.runner import execute_model
from mathmode.validation import independently_validate, audit_evidence, validate_criteria
from test_validation import prepared, criteria_for, FIXTURES


def case():
    data = {'classes': ['negative', 'positive'], 'rows': [
        {'id': str(i), 'x': i - 3, 'label': 'negative' if i < 3 else 'positive'}
        for i in range(6)]}
    spec = {'seed': 42, 'data_split': {'strategy': 'holdout', 'train_ids': ['0', '3'],
        'fit_ids': ['0', '3'], 'test_ids': ['1', '2', '4', '5'], 'target': 'label',
        'features': ['x'], 'sample_groups': {}}}
    main = [{'id': k, 'prediction': label} for k, label in zip(
        spec['data_split']['test_ids'], ['negative', 'positive', 'positive', 'positive'])]
    baseline = [{'id': k, 'prediction': 'positive'} for k in spec['data_split']['test_ids']]
    criteria = criteria_for('classification')
    criteria['evaluation']['target'] = 'label'
    return data, main, baseline, spec, criteria


def test_metrics_are_recomputed_from_original_labels():
    data, main, baseline, spec, criteria = case()
    main[0]['macro_f1'] = 1.0  # A claimed score is deliberately ignored.
    metrics = evaluate(data, main, baseline, spec, criteria)
    assert metrics['main_error_rate'] == .25
    assert metrics['main_macro_f1'] == pytest.approx((2 / 3 + 4 / 5) / 2)
    assert metrics['baseline_macro_f1'] == pytest.approx(1 / 3)
    assert metrics['macro_f1_improvement'] == pytest.approx(.4)


@pytest.mark.parametrize('bad', ['fit', 'overlap', 'coverage', 'duplicate', 'label', 'truth', 'classes', 'bootstrap', 'group'])
def test_invalid_classification_evidence_is_rejected(bad):
    data, main, baseline, spec, criteria = case()
    split = spec['data_split']
    if bad == 'fit': split['fit_ids'].append('1')
    if bad == 'overlap': split['train_ids'].append('1')
    if bad == 'coverage': main.pop()
    if bad == 'duplicate': main.append(deepcopy(main[0]))
    if bad == 'label': main[0]['prediction'] = True
    if bad == 'truth': data['rows'][1]['label'] = 'unknown'
    if bad == 'classes': data['classes'].append('positive')
    if bad == 'bootstrap': criteria['evaluation']['bootstrap_repetitions'] = 100
    if bad == 'group':
        split['strategy'] = 'group'
        split['sample_groups'] = {row['id']: 'same' for row in data['rows']}
        for row in data['rows']: row['group'] = 'same'
    with pytest.raises(ValueError): evaluate(data, main, baseline, spec, criteria)


def test_classification_criteria_cannot_omit_required_checks():
    criteria = case()[-1]
    validate_criteria(criteria)
    criteria['checks'] = [c for c in criteria['checks'] if c['metric'] != 'main_macro_f1_loss']
    with pytest.raises(ValueError, match='mandatory'): validate_criteria(criteria)


def test_absent_declared_class_is_not_dropped_from_macro_average():
    data, main, baseline, spec, criteria = case()
    data['classes'].append('third')
    metrics = evaluate(data, main, baseline, spec, criteria)
    assert metrics['main_macro_f1'] == pytest.approx((2 / 3 + 4 / 5) / 3)


def test_disjoint_raw_groups_are_accepted():
    data, main, baseline, spec, criteria = case()
    split = spec['data_split']
    split['strategy'] = 'group'
    for row in data['rows']:
        row['group'] = 'train' if row['id'] in split['train_ids'] else 'holdout'
    split['sample_groups'] = {row['id']: row['group'] for row in data['rows']}
    assert evaluate(data, main, baseline, spec, criteria)['split_leakage'] == 0


def test_fitting_rows_must_cover_declared_classes():
    data, main, baseline, spec, criteria = case()
    data['rows'][3]['label'] = 'negative'
    with pytest.raises(ValueError, match='cover'):
        evaluate(data, main, baseline, spec, criteria)


@pytest.mark.parametrize('wrong_prediction', [False, True])
def test_real_classification_validator_and_gate(prepared, wrong_prediction):
    # Reuse the real workspace lifecycle fixture, replacing its synthetic problem.
    root = prepared
    manifest = read_json(root / 'input_manifest.json')
    inputs = {entry['input_id']: entry for entry in manifest['files']}
    data, _, _, split_spec, criteria = case()
    if wrong_prediction:
        data['rows'][1]['label'] = 'positive'
    for key, payload in [('data', data), ('criteria', criteria)]:
        path = root / inputs[key]['path']
        path.chmod(0o600)
        write_json(path, payload)
        inputs[key].update(sha256=file_hash(path), size_bytes=path.stat().st_size)
        path.chmod(0o444)
    write_json(root / 'input_manifest.json', manifest)
    (root / 'code/classification.py').write_bytes((FIXTURES / 'validation/classification_solver.py').read_bytes())
    for method, filename in [('threshold-main', 'main_spec.json'), ('majority-baseline', 'baseline_spec.json')]:
        spec = read_json(root / filename)
        spec.update(method_id=method, task_type='classification', data_split=split_spec['data_split'])
        spec['data_split']['sample_times'] = {}
        spec['objective'] = {'metric': 'error_rate', 'sense': 'min', 'expression': 'misclassified rows / holdout rows'}
        spec['implementation'] = {'entrypoint': 'code/classification.py', 'code_files': ['code/classification.py'], 'language': 'python'}
        spec['outputs'][0]['fields'][1]['type'] = 'string'
        spec['validation_plan'].update(checks=[c['check_id'] for c in criteria['checks']],
            criteria={'path': inputs['criteria']['path'], 'sha256': inputs['criteria']['sha256']})
        write_json(root / filename, spec)
    runs = [execute_model(root, filename, role=role, interpreter=sys.executable)
        for role, filename in [('main', 'main_spec.json'), ('baseline', 'baseline_spec.json')]]
    assert all(r['status'] == 'PASS' for r in runs)
    summary = independently_validate(root, *(f"runs/{r['run_id']}/run_manifest.json" for r in runs), interpreter=sys.executable)
    expected = 'FAIL' if wrong_prediction else 'PASS'
    assert summary['status'] == expected
    relative = f"validations/{summary['validation_id']}/validation_summary.json"
    assert audit_evidence(root, relative)['status'] == expected
    assert not list((root / summary['validator_workspace']).rglob('classification.py'))
    # A tampered result must close the gate even if the stored summary says PASS.
    output = root / runs[0]['outputs'][0]['path']
    write_json(output, [{'id': '1', 'prediction': 'positive'}])
    assert audit_evidence(root, relative)['status'] != 'PASS'
