import json
from pathlib import Path
import pytest
from patientprobe.research import load_trials, summarize, evaluate_file
from patientprobe.cli import main


def record(**changes):
    r = dict(trial_id='x1', scenario_id='schedule',condition='clean',source='real',
        task_completed=True,correction_required=False,correction_honored=None,
        clarification_required=False,clarification_asked=None,confirmation_claimed=True,
        backend_action_verified=None,response_latency_ms=None,reviewer='r1',evidence_ref='private_record_1')
    r.update(changes)
    return r


def test_unknown_backend_not_false_confirmation():
    r=summarize([record()])['metrics_overall']
    assert r['confirmed_but_unverified_count']==1
    assert r['verified_false_confirmation_rate']['denominator']==0
    assert r['verified_false_confirmation_rate']['rate'] is None


def test_verified_false_confirmation():
    r=summarize([record(backend_action_verified=False)])['metrics_overall']
    assert r['verified_false_confirmation_rate']['successes']==1
    assert r['verified_false_confirmation_rate']['rate']==1


def test_missing_task_does_not_become_failure():
    r=summarize([record(task_completed=None)])['metrics_overall']
    assert r['task_completion_rate']['denominator']==0


def test_correction_denominator():
    a=record(trial_id='a',correction_required=True,correction_honored=True)
    b=record(trial_id='b',correction_required=True,correction_honored=None)
    c=record(trial_id='c')
    d=summarize([a,b,c])['metrics_overall']['correction_retention_rate']
    assert d['successes']==1 and d['denominator']==1


def test_reject_synthetic_by_default():
    with pytest.raises(ValueError,match='Synthetic'):
        summarize([record(source='synthetic')])


def test_reject_mixed_real_and_synthetic():
    with pytest.raises(ValueError,match='mix real and synthetic'):
        summarize([record(), record(trial_id='s',source='synthetic')],include_synthetic=True)


def test_synthetic_report_marked():
    x=summarize([record(source='synthetic')],include_synthetic=True)
    assert 'SYNTHETIC' in x['report_type']
    assert not x['observational_evidence_available']


def test_duplicate_trial_id_rejected(tmp_path):
    p=tmp_path/'trials.jsonl'; row=record()
    p.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n')
    with pytest.raises(ValueError,match='duplicate trial_id'):
        load_trials(p)


def test_inconsistent_label_rejected(tmp_path):
    p=tmp_path/'bad.jsonl';p.write_text(json.dumps(record(correction_honored=True))+'\n')
    with pytest.raises(ValueError,match='correction_honored requires'):
        load_trials(p)


def test_demo_cli(tmp_path):
    p=tmp_path/'demo.jsonl';p.write_text(json.dumps(record(source='synthetic'))+'\n')
    out=tmp_path/'r.json'
    assert main(['research','--input',str(p),'--output',str(out)])==2
    assert not out.exists()
    assert main(['research','--input',str(p),'--output',str(out),'--include-synthetic'])==0
    assert json.loads(out.read_text())['report_type'].startswith('SYNTHETIC')


def test_none_rows():
    result=summarize([])
    assert result['trial_count']==0
    assert result['metrics_overall']['task_completion_rate']['rate'] is None


def test_scenario_matched_comparison_is_descriptive():
    x=summarize([record(trial_id='clean',condition='clean',task_completed=True),
                 record(trial_id='changed',condition='interruption',task_completed=False)])
    match=x['scenario_matched_comparisons']['interruption_vs_clean']
    assert match['matched_scenarios']==1
    assert match['mean_scenario_difference_pp']==-100


def test_no_matched_comparison_without_clean():
    x=summarize([record(condition='interruption')])
    assert x['scenario_matched_comparisons']['interruption_vs_clean']['matched_scenarios']==0
    assert x['scenario_matched_comparisons']['interruption_vs_clean']['mean_scenario_difference_pp'] is None
