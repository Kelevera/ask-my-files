import re
from pathlib import Path

from eval.run import GATES

REPORT = Path(__file__).resolve().parent.parent / "EVAL_REPORT.md"


def test_committed_eval_report_passes_all_gates():
    """The acceptance gate of BRIEF.md: the last real eval run passed every gate."""
    report = REPORT.read_text(encoding="utf-8")
    for name, gate in GATES.items():
        value, result = re.search(
            rf"\| {re.escape(name)} \| ([0-9.]+) \| {gate:.2f} \| (PASS|FAIL) \|", report).groups()
        assert float(value) >= gate, name
        assert result == "PASS", name
    assert "Overall: PASS" in report
    assert "## Failing cases" in report
