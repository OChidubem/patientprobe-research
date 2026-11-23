"""Evidence-grounded, reproducible offline evaluation for voice-agent trials.

No phone calls, LLM calls, or external requests are made here. Synthetic fixtures are
rejected by default so demonstration data cannot become reported results by accident.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

CONDITIONS = frozenset({"clean", "interruption", "ambiguity", "noise"})
SOURCES = frozenset({"real", "synthetic"})
BOOLEAN_FIELDS = ("task_completed", "correction_required", "correction_honored",
                  "clarification_required", "clarification_asked",
                  "confirmation_claimed", "backend_action_verified")
REQUIRED = ("trial_id", "scenario_id", "condition", "source", "reviewer", "evidence_ref")


def _validate(item: dict[str, Any], line: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"Line {line}: expected JSON object")
    for key in REQUIRED:
        if not isinstance(item.get(key), str) or not item[key].strip():
            raise ValueError(f"Line {line}: {key} must be a nonempty string")
    if item["condition"] not in CONDITIONS:
        raise ValueError(f"Line {line}: invalid condition {item['condition']!r}")
    if item["source"] not in SOURCES:
        raise ValueError(f"Line {line}: invalid source {item['source']!r}")
    for name in BOOLEAN_FIELDS:
        value = item.get(name)
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"Line {line}: {name} must be true, false or null")
    for flag, observation in (("correction_required", "correction_honored"),
                              ("clarification_required", "clarification_asked")):
        if item.get(flag) is not True and item.get(observation) is not None:
            raise ValueError(f"Line {line}: {observation} requires {flag}=true")
    lag = item.get("response_latency_ms")
    if lag is not None and (isinstance(lag, bool) or not isinstance(lag, (float, int))
                            or not math.isfinite(lag) or lag < 0):
        raise ValueError(f"Line {line}: response_latency_ms must be nonnegative finite number or null")
    return item


def load_trials(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input trial annotations missing: {path}")
    rows = []
    ids = set()
    for line_no, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Line {line_no}: invalid JSON: {exc}") from exc
        _validate(obj, line_no)
        if obj['trial_id'] in ids:
            raise ValueError(f"Line {line_no}: duplicate trial_id {obj['trial_id']!r}")
        ids.add(obj['trial_id'])
        rows.append(obj)
    return rows


def _rate(rows: list[dict[str, Any]], eligible, passes) -> dict[str, Any]:
    eligible_rows = [row for row in rows if eligible(row)]
    k = sum(bool(passes(row)) for row in eligible_rows)
    n = len(eligible_rows)
    if not n:
        return {"successes": 0, "denominator": 0, "rate": None,
                "wilson_95_interval": None}
    value = k / n
    z = 1.96
    d = 1 + z*z/n
    center = (value + z*z/(2*n))/d
    radius = (z/d)*math.sqrt(value*(1-value)/n + z*z/(4*n*n))
    return {"successes": k, "denominator": n, "rate": round(value, 4),
            "wilson_95_interval": [round(max(0., center-radius), 4),
                                   round(min(1., center+radius), 4)]}


def _group_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observed_lag = [float(row['response_latency_ms']) for row in rows
                    if row.get('response_latency_ms') is not None]
    return {
        'attempts': len(rows),
        'task_completion_rate': _rate(rows,
            lambda r: r.get('task_completed') is not None,
            lambda r: r['task_completed'] is True),
        'correction_retention_rate': _rate(rows,
            lambda r: r.get('correction_required') is True and r.get('correction_honored') is not None,
            lambda r: r['correction_honored'] is True),
        'clarification_rate': _rate(rows,
            lambda r: r.get('clarification_required') is True and r.get('clarification_asked') is not None,
            lambda r: r['clarification_asked'] is True),
        'verified_false_confirmation_rate': _rate(rows,
            lambda r: r.get('confirmation_claimed') is True and r.get('backend_action_verified') is not None,
            lambda r: r['backend_action_verified'] is False),
        'confirmed_but_unverified_count': sum(r.get('confirmation_claimed') is True
            and r.get('backend_action_verified') is None for r in rows),
        'response_latency_ms': {'n_observed': len(observed_lag),
                                 'median': round(median(observed_lag), 2) if observed_lag else None},
    }



def _scenario_matched_comparisons(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Descriptive scenario-matched differences; not randomized causal estimates."""
    by_scenario: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row.get('task_completed') is not None:
            by_scenario[row['scenario_id']][row['condition']].append(row['task_completed'])
    out: dict[str, Any] = {}
    for condition in ('interruption', 'ambiguity', 'noise'):
        matched = []
        for name, conditions in sorted(by_scenario.items()):
            clean = conditions.get('clean', [])
            altered = conditions.get(condition, [])
            if clean and altered:
                clean_rate = sum(clean) / len(clean)
                altered_rate = sum(altered) / len(altered)
                matched.append({
                    'scenario_id': name,
                    'clean_n': len(clean),
                    'changed_n': len(altered),
                    'clean_task_completion_rate': round(clean_rate, 4),
                    'changed_task_completion_rate': round(altered_rate, 4),
                    'difference_changed_minus_clean_pp': round(100*(altered_rate-clean_rate), 2),
                })
        out[condition + '_vs_clean'] = {
            'matched_scenarios': len(matched),
            'mean_scenario_difference_pp': round(sum(m['difference_changed_minus_clean_pp'] for m in matched)/len(matched), 2) if matched else None,
            'details': matched,
            'note': 'Descriptive, scenario-level differences only; not a controlled causal effect or a significance test.'
        }
    return out

def summarize(rows: list[dict[str, Any]], *, include_synthetic: bool = False) -> dict[str, Any]:
    if not include_synthetic and any(r['source'] == 'synthetic' for r in rows):
        raise ValueError('Synthetic fixture found. Refusing to mix demo with real results; '
                         'use --include-synthetic ONLY for a labeled software demonstration.')
    if include_synthetic and any(r['source']=='real' for r in rows) and any(r['source']=='synthetic' for r in rows):
        raise ValueError('Do not mix real and synthetic trials in one report')
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row['condition']].append(row)
    synthetic = bool(rows) and all(row['source'] == 'synthetic' for row in rows)
    return {
        'report_type': 'SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_RESULTS' if synthetic else 'REAL_ANNOTATION_SUMMARY',
        'trial_count': len(rows),
        'observational_evidence_available': bool(rows) and not synthetic,
        'metrics_overall': _group_metrics(rows),
        'conditions': {key: _group_metrics(groups[key]) for key in sorted(groups)},
        'scenario_matched_comparisons': _scenario_matched_comparisons(rows),
        'notes': [
           'A null field means unknown or unobserved; it is excluded from the metric denominator.',
           'Verified false confirmation requires independent backend-action evidence.',
           'Wilson intervals are descriptive; related calls may violate independence assumptions.',
           'Annotated outcomes still require independent evidence auditing to be trustworthy.',
        ],
    }


def evaluate_file(input_path: Path, output_path: Path, *, include_synthetic: bool = False) -> dict[str, Any]:
    rows = load_trials(input_path)
    report = summarize(rows, include_synthetic=include_synthetic)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    return report
