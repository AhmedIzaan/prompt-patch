"""Deterministic extraction scoring against approved references, never an LLM judge."""

from decimal import Decimal
import json
import math
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from promptpatch.models import SettlementExtraction


class EvaluationConfigError(ValueError):
    """Reference/policy evidence cannot support a trustworthy evaluation."""


class EvaluationRules(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore", allow_inf_nan=False)
    numeric_absolute_tolerance_mm: float = Field(ge=0)
    numeric_relative_tolerance: float = Field(ge=0)
    supported_units: list[Literal["mm"]]
    extra_fields_allowed: Literal[False]
    allow_null: Literal[True]
    evidence_whitespace: Literal["collapse"]
    contradiction_action: Literal["needs_clarification"]
    unsupported_unit_action: Literal["needs_clarification"]


class Discrepancy(BaseModel):
    code: str
    field: str | None = None
    message: str


class EvaluationResult(BaseModel):
    status: Literal["pass", "fail", "uncertain"]
    discrepancies: list[Discrepancy]
    parsed_json: JsonValue | None


def parse_json(text: str):
    """Reject duplicate keys and non-JSON NaN/Infinity, without quoting input."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key.")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError("Non-finite JSON constant.")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number.")
        return number

    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant, parse_float=finite_float)


class SettlementEvaluator:
    def __init__(self, input_text, expected, rules, *, ambiguous=False, unsupported_unit=False):
        try:
            self.rules = EvaluationRules.model_validate(rules)
            self.expected = SettlementExtraction.model_validate(expected)
        except ValidationError:
            raise EvaluationConfigError("Approved reference or evaluation rules have invalid shape/types.") from None
        fields = ["estimated_settlement_mm", "allowable_settlement_mm", "evidence"]
        if (rules.get("required_fields") != fields
                or rules.get("numeric_fields") != fields[:2] or self.rules.supported_units != ["mm"]):
            raise EvaluationConfigError("Policy contract is unsupported for this extraction task.")
        self.input_text = input_text
        self.ambiguous = ambiguous
        self.unsupported_unit = unsupported_unit
        if self._evidence_issues(self.expected):
            raise EvaluationConfigError("Approved reference evidence is unsupported by the source.")

    def _close(self, actual, expected):
        actual, expected = Decimal(str(actual)), Decimal(str(expected))
        tolerance = max(Decimal(str(self.rules.numeric_absolute_tolerance_mm)),
                        Decimal(str(self.rules.numeric_relative_tolerance)) * abs(expected))
        return abs(actual - expected) <= tolerance

    def _evidence_issues(self, output):
        issues = []
        source = " ".join(self.input_text.split())
        for name, field in (("estimated", "estimated_settlement_mm"), ("allowable", "allowable_settlement_mm")):
            number, quote = getattr(output, field), getattr(output.evidence, name)
            if number is None:
                if quote is not None:
                    issues.append(Discrepancy(code="absent_supporting_quote", field=field,
                                              message="Null measurements must have null evidence."))
                continue
            if not quote or not quote.strip() or " ".join(quote.split()) not in source:
                issues.append(Discrepancy(code="absent_supporting_quote", field=field,
                                          message="A nonempty supporting substring in the source is required."))
                continue
            measurements = re.findall(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(mm|cm|m)\b", quote, re.I)
            supported = [(value, unit) for value, unit in measurements if unit.lower() in self.rules.supported_units]
            if not supported and measurements:
                issues.append(Discrepancy(code="unsupported_unit", field=field,
                                          message="The evidence uses a unit outside the approved policy."))
            elif not any(self._close(value, number) for value, _ in supported):
                issues.append(Discrepancy(code="absent_supporting_quote", field=field,
                                          message="The source quote does not support the reported measurement."))
        return issues

    def evaluate(self, raw_text: str) -> EvaluationResult:
        try:
            if len(raw_text.encode("utf-8")) > 65536:
                raise ValueError("Response exceeds budget.")
            parsed = parse_json(raw_text)
        except (ValueError, TypeError, RecursionError):
            return EvaluationResult(status="fail", parsed_json=None, discrepancies=[
                Discrepancy(code="invalid_json", message="Response must be one strict JSON document.")])
        try:
            output = SettlementExtraction.model_validate(parsed)
        except ValidationError as error:
            codes = {"missing_key" if item["type"] == "missing" else "invalid_shape_or_type"
                     for item in error.errors(include_input=False, include_context=False)}
            return EvaluationResult(status="fail", parsed_json=parsed, discrepancies=[
                Discrepancy(code=code, message="Response does not satisfy the extraction contract.") for code in sorted(codes)])
        issues = self._evidence_issues(output)
        for field in ("estimated_settlement_mm", "allowable_settlement_mm"):
            actual, expected = getattr(output, field), getattr(self.expected, field)
            if expected is None and actual is not None:
                issues.append(Discrepancy(code="unjustified_non_null", field=field,
                                          message="Reference evidence does not justify a numeric value."))
            elif expected is not None and (actual is None or not self._close(actual, expected)):
                issues.append(Discrepancy(code="incorrect_numeric_value", field=field,
                                          message="Measurement differs from the approved reference/tolerance."))
        status = "fail" if issues else "pass"
        if self.ambiguous or self.unsupported_unit:
            issues.append(Discrepancy(code="unsupported_unit" if self.unsupported_unit else "ambiguous_source",
                                      message="Approved source metadata requires developer clarification."))
            if status == "pass":
                status = "uncertain"
        return EvaluationResult(status=status, discrepancies=issues, parsed_json=parsed)
