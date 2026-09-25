"""Deterministic, local task classifier. No inference call.

Only the owner's *instruction* text is classified. Quoted passages, fenced code,
block quotes and attachment contents are data: they can supply evidence snippets
but can never change policy, lower a role, or issue router instructions.

The rules are conservative on purpose. They may over-use the highest role; that
is measured on real prompts, not assumed away.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .contracts import (
    CLASSIFIER_VERSION,
    RiskFlag,
    TaskAssessment,
    TaskKind,
    Urgency,
    new_id,
)

# Words are matched on word boundaries against lower-cased instruction text.
PATTERNS: dict[str, tuple[str, ...]] = {
    "architecture": (
        r"architecture",
        r"architect(?:ing)?",
        r"system design",
        r"design (?:review|doc|document)",
        r"technical design",
        r"high[- ]level design",
    ),
    "product_decision": (
        r"product decision",
        r"product strategy",
        r"prd",
        r"roadmap",
        r"prioriti[sz]e (?:the )?(?:features|roadmap|backlog)",
        r"go[- ]to[- ]market",
        r"pricing strategy",
        r"should (?:we|i) (?:build|launch|ship|kill)",
    ),
    "ui_decision": (
        r"ui decision",
        r"ux decision",
        r"user interface design",
        r"(?:ui|ux) (?:flow|design|layout)",
        r"wireframe",
        r"design the (?:ui|screen|page|onboarding)",
    ),
    "tradeoff": (
        r"trade[- ]?offs?",
        r"which approach",
        r"pros and cons",
        r"weigh (?:the )?options",
        r"decide between",
        r"compare (?:the )?(?:options|approaches|architectures)",
    ),
    "hc_noun": (
        r"linkedin(?: post| article| profile| summary)?",
        r"research (?:article|paper|piece|essay)",
        r"r[ée]sum[ée]s?",
        r"cv",
        r"job application",
        r"cover letter",
        r"application essay",
        r"op[- ]ed",
    ),
    "hc_verb": (
        r"write",
        r"writing",
        r"draft(?:ing)?",
        r"re-?write",
        r"rewriting",
        r"edit(?:ing)?",
        r"polish",
        r"tailor(?:ing)?",
        r"score",
        r"scoring",
        r"rate",
        r"review",
        r"critique",
        r"improve",
        r"optimi[sz]e",
        r"strengthen",
        r"proofread",
        r"apply",
        r"prepare",
        r"documentation",
        r"document",
    ),
    "coding": (
        r"implement(?:ation)?",
        r"code",
        r"coding",
        r"refactor",
        r"fix (?:the |a |this )?bug",
        r"function",
        r"endpoint",
        r"api",
        r"unit tests?",
        r"migration",
        r"script",
        r"deploy",
        r"pull request",
        r"repository",
        r"repo",
        r"module",
        r"class",
        r"build (?:the|a|an) (?:feature|service|cli|tool|app)",
        r"integrate",
        r"webhook",
        r"schema",
        r"(?:the|my|our) (?:app|codebase|service|backend|frontend)",
    ),
    "money_movement": (
        r"payments?",
        r"payouts?",
        r"money transfer",
        r"transfer(?:ring)? (?:funds|money)",
        r"fund transfers?",
        r"payment[- ]transfer",
        r"wire transfer",
        r"refunds?",
        r"charg(?:e|ing) (?:the )?(?:card|customer)",
        r"billing",
        r"wallet",
        r"ledger",
        r"withdrawals?",
        r"checkout",
        r"stripe",
        r"upi",
        r"remittance",
    ),
    "security": (
        r"auth",
        r"authentication",
        r"authori[sz]ation",
        r"login",
        r"log-in",
        r"sign[- ]in",
        r"passwords?",
        r"access tokens?",
        r"oauth",
        r"encrypt(?:ion)?",
        r"secrets?",
        r"credentials?",
        r"permissions?",
        r"access control",
        r"vulnerab(?:le|ility|ilities)",
        r"security",
        r"csrf",
        r"xss",
        r"sql injection",
        r"session (?:handling|management|cookies?)",
    ),
    "privacy": (
        r"privacy",
        r"pii",
        r"personal data",
        r"personally identifiable",
        r"gdpr",
        r"dpdp",
        r"hipaa",
        r"medical records?",
        r"health data",
        r"ssn",
        r"aadhaar",
        r"pan card",
        r"user data deletion",
        r"data retention",
    ),
    "assessment": (
        r"is (?:this|it) safe",
        r"is (?:this|it|the|my|our) (?:[\w.-]+ ){1,4}safe",
        r"safe to (?:run|deploy|merge|delete|drop|execute|ship)",
        r"will this break",
        r"can i (?:safely )?(?:run|deploy|delete|drop|merge)",
        r"should i (?:run|deploy|delete|drop|merge)",
        r"is (?:this|it) (?:correct|secure|compliant|legal)",
        r"risk assessment",
        r"check (?:if|whether) .* safe",
    ),
    "production": (
        r"production",
        r"prod",
        r"live database",
        r"customer data",
    ),
    "destructive": (
        r"drop (?:table|database|column)",
        r"delete (?:all|from|the database|production)",
        r"truncate",
        r"rm -rf",
        r"force[- ]push",
        r"wipe",
    ),
    "extraction": (
        r"extract",
        r"pull out",
        r"list (?:all|the|every)",
        r"collect",
        r"gather",
        r"find (?:these|the|me|all)? ?(?:resources|links|urls|sources|papers|articles)",
        r"copy (?:out|the)",
        r"compile (?:a )?list",
        r"fetch",
        r"scrape",
        r"get (?:the|all) (?:links|urls|dates|names|emails|numbers|column)",
    ),
    "judgement": (
        r"assess",
        r"evaluate",
        r"judge",
        r"score",
        r"rate",
        r"critique",
        r"analy[sz]e",
        r"interpret",
        r"recommend",
        r"should",
        r"is (?:this|it) (?:good|right|correct|safe|enough)",
        r"improve",
        r"rewrite",
        r"tailor",
        r"why",
        r"compare",
    ),
    "routine": (
        r"format(?:ting)?",
        r"re-?format",
        r"tidy",
        r"clean up (?:my )?(?:notes|text|list)",
        r"summari[sz]e",
        r"summary",
        r"tl;?dr",
        r"fix (?:the )?(?:typos|spelling|grammar)",
        r"convert (?:this )?(?:to|into) (?:bullets|bullet points|a table|markdown)",
        r"bullet points",
        r"my notes",
        r"meeting notes",
        r"private notes?",
        r"(?:draft|write) (?:a |an )?(?:quick |short )?(?:reply|message|email|slack message|text)",
        r"translate",
        r"capitali[sz]e",
        r"sort (?:this|the) list",
        r"rename",
        r"(?:re-?write|reword|rephrase) (?:the|this|my|a) (?:error |status |short )?(?:message|sentence|paragraph|note|label|heading|title)",
        r"in plain english",
    ),
    "softener": (
        r"quick(?:ly)?",
        r"simple",
        r"just",
        r"low priority",
        r"small",
        r"easy",
        r"minor",
    ),
}

_COMPILED = {
    name: re.compile(r"(?<![\w-])(?:" + "|".join(patterns) + r")(?![\w-])", re.IGNORECASE)
    for name, patterns in PATTERNS.items()
}

_QUOTE_PATTERNS = (
    re.compile(r"```.*?```", re.DOTALL),
    re.compile(r"~~~.*?~~~", re.DOTALL),
    re.compile(r"`[^`\n]+`"),
    re.compile(r"\"[^\"\n]{0,2000}\""),
    re.compile(r"“[^”]{0,2000}”"),
    re.compile(r"‘[^’\n]{12,2000}’"),
    re.compile(r"(?m)^\s*>.*$"),
)

_ARCH_REFERENCE = re.compile(
    r"(?:(?:agreed|approved|accepted|existing|finali[sz]ed|signed[- ]off)(?: \w+){0,2} architecture"
    r"|(?:per|from|following|according to|matching) (?:the|our|this) (?:\w+ ){0,2}architecture)",
    re.IGNORECASE,
)

_URGENCY = {
    Urgency.NOW: re.compile(r"(?<!\w)(urgent|asap|right now|immediately|today)(?!\w)", re.IGNORECASE),
    Urgency.LATER: re.compile(r"(?<!\w)(no rush|whenever|low urgency|later this week)(?!\w)", re.IGNORECASE),
}


@dataclass
class ClassifierInput:
    text: str
    attachment_manifest: list[dict] = field(default_factory=list)
    explicit_priority: str | None = None
    explicit_urgency: str | None = None
    metadata: dict = field(default_factory=dict)
    project_context: dict = field(default_factory=dict)


def split_instruction(text: str) -> tuple[str, list[str]]:
    """Return (instruction text with quoted material removed, quoted passages)."""
    quoted: list[str] = []
    instruction = text
    for pattern in _QUOTE_PATTERNS:
        def _cut(match: re.Match[str]) -> str:
            quoted.append(match.group(0))
            return " [quoted] "

        instruction = pattern.sub(_cut, instruction)
    return instruction, quoted


def _hits(name: str, text: str) -> list[str]:
    return [m.group(0) for m in _COMPILED[name].finditer(text)]


def _snippet(text: str, word: str, width: int = 40) -> str:
    index = text.lower().find(word.lower())
    if index < 0:
        return word
    start = max(0, index - width)
    return text[start : index + len(word) + width].strip().replace("\n", " ")


def classify(item: ClassifierInput) -> TaskAssessment:
    instruction, quoted = split_instruction(item.text)
    lowered = instruction.lower()
    hits = {name: _hits(name, lowered) for name in PATTERNS}
    kinds: list[TaskKind] = []
    flags: list[RiskFlag] = []
    reasons: list[str] = []
    uncertainty: list[str] = []
    evidence: list[str] = []

    def add(kind: TaskKind, code: str, words: Iterable[str]) -> None:
        if kind not in kinds:
            kinds.append(kind)
        reasons.append(code)
        for word in list(words)[:2]:
            evidence.append(_snippet(instruction, word))

    metadata_kind = item.metadata.get("task_kind")
    if metadata_kind:
        try:
            add(TaskKind(metadata_kind), "META_TASK_KIND", [])
        except ValueError:
            uncertainty.append(f"unrecognised task_kind metadata {metadata_kind!r}")

    is_extraction = bool(hits["extraction"])
    has_judgement = bool(hits["judgement"])
    is_coding = bool(hits["coding"])

    if hits["architecture"]:
        if is_coding and _ARCH_REFERENCE.search(lowered) and len(_ARCH_REFERENCE.findall(lowered)) >= len(hits["architecture"]):
            # "implement X per the agreed architecture" references a design;
            # it does not ask for one.
            reasons.append("ARCHITECTURE_REFERENCE_ONLY")
        else:
            add(TaskKind.ARCHITECTURE, "ARCHITECTURE", hits["architecture"])
    if hits["product_decision"]:
        add(TaskKind.PRODUCT_DECISION, "PRODUCT_DECISION", hits["product_decision"])
    if hits["ui_decision"]:
        add(TaskKind.UI_DECISION, "UI_DECISION", hits["ui_decision"])
    if hits["tradeoff"]:
        add(TaskKind.TRADEOFF, "TRADEOFF", hits["tradeoff"])

    # High-credibility writing: a credibility noun plus a writing/judging verb.
    # Pure extraction from the same document is different (handled below).
    if hits["hc_noun"]:
        hc_verbs = [v for v in hits["hc_verb"] if v not in {"document"}]
        if hc_verbs and not (is_extraction and not has_judgement and not _writes(hits)):
            add(TaskKind.HIGH_CREDIBILITY_WRITING, "HIGH_CREDIBILITY", hits["hc_noun"] + hc_verbs)
            flags.append(RiskFlag.HIGH_CREDIBILITY)
        elif not is_extraction:
            uncertainty.append("credibility-sensitive document mentioned without a clear operation")
            reasons.append("HC_NOUN_UNCLEAR_OPERATION")

    money = hits["money_movement"]
    security = hits["security"]
    privacy = hits["privacy"]
    pure_extraction = is_extraction and not has_judgement and not _writes(hits)
    if not pure_extraction:
        # A pure extraction may mention prices or passwords as data; only an
        # operation on them carries the risk flag.
        if money:
            flags.append(RiskFlag.MONEY_MOVEMENT)
        if security:
            flags.append(RiskFlag.SECURITY)
        if privacy:
            flags.append(RiskFlag.PRIVACY)
    if hits["destructive"]:
        flags.append(RiskFlag.DESTRUCTIVE)
    if hits["production"]:
        flags.append(RiskFlag.PRODUCTION)

    risky_coding = bool(money or security or privacy)
    if is_coding and risky_coding and not pure_extraction:
        add(TaskKind.HIGH_RISK_CODING, "HIGH_RISK_CODING", money + security + privacy)
    elif is_coding:
        add(TaskKind.IMPLEMENTATION, "IMPLEMENTATION", hits["coding"])
    elif (money or security or privacy) and not is_extraction:
        uncertainty.append("money/security/privacy terms without a clear coding operation")
        reasons.append("RISK_TERMS_UNCLEAR_OPERATION")

    if hits["assessment"] or (hits["destructive"] and not is_coding):
        add(TaskKind.CONSEQUENTIAL_ASSESSMENT, "CONSEQUENTIAL_ASSESSMENT", hits["assessment"] + hits["destructive"])
    elif hits["production"] and (has_judgement or hits["destructive"]):
        add(TaskKind.CONSEQUENTIAL_ASSESSMENT, "PRODUCTION_JUDGEMENT", hits["production"])

    if is_extraction:
        if has_judgement and not kinds:
            uncertainty.append("extraction combined with interpretation/judgement")
            reasons.append("EXTRACTION_WITH_JUDGEMENT")
        elif not kinds:
            add(TaskKind.RESOURCE_EXTRACTION, "LITERAL_EXTRACTION", hits["extraction"])
        else:
            reasons.append("EXTRACTION_SECONDARY")

    if hits["routine"] and not kinds:
        if has_judgement and not _routine_only_judgement(hits):
            uncertainty.append("routine text change combined with judgement words")
            reasons.append("ROUTINE_WITH_JUDGEMENT")
        else:
            add(TaskKind.ROUTINE_TEXT, "ROUTINE_TEXT", hits["routine"])

    if hits["softener"]:
        # Recorded as evidence only: softeners never remove a role floor.
        reasons.append("SOFTENER_IGNORED")

    if quoted:
        reasons.append("QUOTED_MATERIAL_TREATED_AS_DATA")
    attachment_kinds = sorted({str(a.get("kind")) for a in item.attachment_manifest if a.get("kind")})
    if attachment_kinds:
        reasons.append("ATTACHMENTS_TREATED_AS_DATA")

    if not kinds:
        kinds.append(TaskKind.UNKNOWN)
        reasons.append("UNRECOGNISED_TASK")
        uncertainty.append("task class not recognised by the rules")

    primary = _primary(kinds)
    secondary = [k for k in kinds if k is not primary]

    urgency = None
    if item.explicit_urgency:
        urgency = Urgency(item.explicit_urgency)
    else:
        for level, pattern in _URGENCY.items():
            if pattern.search(instruction):
                urgency = level
                break

    ambiguous = bool(uncertainty) or primary is TaskKind.UNKNOWN or _conflicting(kinds)
    if _conflicting(kinds):
        uncertainty.append("conflicting task signals: " + ", ".join(k.value for k in kinds))

    return TaskAssessment(
        id=new_id("task"),
        original_goal=item.text.strip()[:4000],
        task_kind=primary,
        secondary_kinds=secondary,
        risk_flags=_dedupe(flags),
        priority=item.explicit_priority,
        urgency=urgency,
        ambiguous=ambiguous,
        uncertainty=_dedupe(uncertainty),
        evidence=_dedupe(evidence)[:8],
        reason_codes=_dedupe(reasons),
        classifier_version=CLASSIFIER_VERSION,
    )


_PRIMARY_ORDER = (
    TaskKind.HIGH_RISK_CODING,
    TaskKind.CONSEQUENTIAL_ASSESSMENT,
    TaskKind.ARCHITECTURE,
    TaskKind.PRODUCT_DECISION,
    TaskKind.UI_DECISION,
    TaskKind.TRADEOFF,
    TaskKind.HIGH_CREDIBILITY_WRITING,
    TaskKind.IMPLEMENTATION,
    TaskKind.ROUTINE_TEXT,
    TaskKind.RESOURCE_EXTRACTION,
    TaskKind.UNKNOWN,
)


def _primary(kinds: list[TaskKind]) -> TaskKind:
    return min(kinds, key=_PRIMARY_ORDER.index)


def _conflicting(kinds: list[TaskKind]) -> bool:
    low = {TaskKind.ROUTINE_TEXT, TaskKind.RESOURCE_EXTRACTION}
    return bool(low & set(kinds)) and bool(set(kinds) - low - {TaskKind.UNKNOWN})


def _writes(hits: dict[str, list[str]]) -> bool:
    writing = {"write", "writing", "draft", "drafting", "rewrite", "re-write", "rewriting", "tailor", "tailoring", "polish"}
    return any(v.lower() in writing for v in hits["hc_verb"])


def _routine_only_judgement(hits: dict[str, list[str]]) -> bool:
    # "improve the formatting" style phrases stay routine only when every
    # judgement word is a mechanical-edit verb.
    mechanical = {"improve", "rewrite", "re-write"}
    return all(word.lower() in mechanical for word in hits["judgement"]) and not hits["hc_noun"]


def _dedupe(items: list) -> list:
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen
