"""Deterministic reference checks; every response here is handwritten, not live."""

import json

import pytest

from promptpatch.evaluator import EvaluationConfigError, SettlementEvaluator
from scripts.seed_demo import SAMPLES, load_samples


DATA, POLICY, _ = load_samples()
CASES = {case.case_key: case for case in DATA.cases}


def evaluator(case_key="T02", rules=None):
    case = CASES[case_key]
    ambiguous = case.expected_status == "needs_clarification"
    return SettlementEvaluator(case.input_text, case.expected.model_dump(), rules or POLICY.rules,
                               ambiguous=ambiguous, unsupported_unit=ambiguous and "unit" in case.tags)


def codes(result):
    return {item.code for item in result.discrepancies}


@pytest.mark.parametrize("case", DATA.cases, ids=lambda case: case.case_key)
def test_approved_reference_outputs_and_uncertain_cases(case):
    result = evaluator(case.case_key).evaluate(case.expected.model_dump_json())
    assert result.status == ("uncertain" if case.expected_status == "needs_clarification" else "pass")


@pytest.mark.parametrize("raw", ["not JSON", "```json\n{}\n```", "{} {}", "{", "NaN",
                                 '{"x":1,"x":2}', '{"x":1e999}', ""])
def test_malformed_json_is_rejected(raw):
    result = evaluator().evaluate(raw)
    assert result.status == "fail" and codes(result) == {"invalid_json"}


@pytest.mark.parametrize("bad", [True, "4.5", [], {}])
def test_numeric_shape_is_strict(bad):
    output = CASES["T02"].expected.model_dump()
    output["estimated_settlement_mm"] = bad
    assert "invalid_shape_or_type" in codes(evaluator().evaluate(json.dumps(output)))


def test_missing_keys_and_extra_keys_are_rejected():
    output = CASES["T02"].expected.model_dump()
    del output["evidence"]["estimated"]
    assert "missing_key" in codes(evaluator().evaluate(json.dumps(output)))
    output = CASES["T02"].expected.model_dump()
    output["release_approved"] = True
    assert "invalid_shape_or_type" in codes(evaluator().evaluate(json.dumps(output)))


def test_decimal_tolerance_and_proposed_correction_change_validation():
    output = CASES["T02"].expected.model_dump()
    output["estimated_settlement_mm"] = 4.51
    assert evaluator().evaluate(json.dumps(output)).status == "pass"
    output["estimated_settlement_mm"] = 4.51000001
    assert "incorrect_numeric_value" in codes(evaluator().evaluate(json.dumps(output)))
    output["estimated_settlement_mm"] = 4.505
    candidate = json.loads((SAMPLES / "evaluation_policy_v2.json").read_text())["rules"]
    assert evaluator().evaluate(json.dumps(output)).status == "pass"
    assert evaluator(rules=candidate).evaluate(json.dumps(output)).status == "fail"


def test_null_is_not_zero_and_missing_reported_measurement_fails():
    output = CASES["T04"].expected.model_dump()
    output["estimated_settlement_mm"] = 0.0
    assert "unjustified_non_null" in codes(evaluator("T04").evaluate(json.dumps(output)))
    output = CASES["T02"].expected.model_dump()
    output["estimated_settlement_mm"], output["evidence"]["estimated"] = None, None
    assert "incorrect_numeric_value" in codes(evaluator().evaluate(json.dumps(output)))


@pytest.mark.parametrize("quote", [None, "", "The estimated settlement is 4.50 mm", "the allowable settlement is 10 mm"])
def test_absent_fabricated_or_unrelated_quote_fails_even_when_number_matches(quote):
    output = CASES["T02"].expected.model_dump()
    output["evidence"]["estimated"] = quote
    assert "absent_supporting_quote" in codes(evaluator().evaluate(json.dumps(output)))


def test_benign_whitespace_in_quote_is_normalized():
    output = CASES["T02"].expected.model_dump()
    output["evidence"]["estimated"] = "The estimated  settlement is\n4.5 mm"
    assert evaluator().evaluate(json.dumps(output)).status == "pass"


def test_unsupported_unit_and_ambiguous_source_cannot_be_a_clean_pass():
    assert codes(evaluator("T08").evaluate(CASES["T08"].expected.model_dump_json())) == {"ambiguous_source"}
    output = CASES["T11"].expected.model_dump()
    output["estimated_settlement_mm"] = 0.6
    output["evidence"]["estimated"] = "Estimated settlement: 0.6 cm"
    result = evaluator("T11").evaluate(json.dumps(output))
    assert result.status == "fail"
    assert {"unsupported_unit", "unjustified_non_null"} <= codes(result)


def test_bad_reference_or_policy_fails_before_scoring():
    expected = CASES["T02"].expected.model_dump()
    expected["evidence"]["estimated"] = "Invented source reference"
    with pytest.raises(EvaluationConfigError):
        SettlementEvaluator(CASES["T02"].input_text, expected, POLICY.rules)
    with pytest.raises(EvaluationConfigError):
        evaluator(rules={**POLICY.rules, "numeric_absolute_tolerance_mm": -1.0})
