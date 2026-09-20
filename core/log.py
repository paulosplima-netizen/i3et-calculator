"""Validation log.

The calculator never fails silently and never hides a gap behind a zero. Every
protected division, every missing factor and every violated invariant becomes a
line here, and the log travels with the result into the exported report.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entry:
    severity: str        # INFO | AVISO | ERRO
    rule: str
    message: str
    context: str | None = None


@dataclass
class Log:
    entries: list[Entry] = field(default_factory=list)

    def info(self, rule, message, context=None):
        self.entries.append(Entry("INFO", rule, message, context))

    def warn(self, rule, message, context=None):
        self.entries.append(Entry("AVISO", rule, message, context))

    def error(self, rule, message, context=None):
        self.entries.append(Entry("ERRO", rule, message, context))

    @property
    def has_errors(self) -> bool:
        return any(e.severity == "ERRO" for e in self.entries)

    def of(self, severity):
        return [e for e in self.entries if e.severity == severity]

    def to_records(self):
        return [{"Severity": e.severity, "RuleID": e.rule,
                 "Message": e.message, "Context": e.context} for e in self.entries]

    def summary(self) -> str:
        n = {s: len(self.of(s)) for s in ("ERRO", "AVISO", "INFO")}
        return f"{n['ERRO']} erros, {n['AVISO']} avisos, {n['INFO']} informacoes"
