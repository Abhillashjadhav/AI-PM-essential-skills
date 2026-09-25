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

# Rules revision 2: vocabulary widened after measuring revision 1 on an
# independently written development set (see docs/evidence/routing-heldout-*).
EXTRA_PATTERNS: dict[str, tuple[str, ...]] = {
    "tradeoff": (
        r"[\w.+#-]{1,40} vs\.? [\w.+#-]{1,40}", r"what would you (?:pick|choose|use|recommend)", r"not sure whether", r"whether to",
        r"(?:decided|decide|deciding|choose|choosing|pick|picking) (?:between )?[\w.+#-]{1,40} (?:or|vs\.?|versus) [\w.+#-]{1,40}",
        r"what should i do",
    ),
    "ui_decision": (
        r"(?:hero|page|screen|home ?page|landing page|onboarding) layouts?", r"which (?:one|layout|design|version) (?:and why|should i|is better|works better)",
    ),
    "architecture": (
        r"data ?models?", r"design (?:the|a|an|my) (?:[\w-]+ ){0,4}(?:models?|services?|apis?|schema|architecture|app|backend|database)",
        r"design (?:an?|the|my) (?:[\w-]+ ){0,4}(?:feature|product|flow|experience|system|service|pipeline|agent)",
        r"take-?home",
    ),
    "product_decision": (
        r"north star", r"(?:success |key |core )?metrics? for", r"kpis?", r"positioning", r"keep the product",
        r"mvp", r"decide which", r"help me (?:decide|choose|prioriti[sz]e)", r"prioriti[sz]e",
        r"which (?:features?|ones?|of these|idea|project) (?:to|should i) (?:cut|build|keep|drop|ship|pick|focus on)",
    ),
    "hc_noun": (
        r"recruiters?", r"hiring managers?", r"interviewers?", r"job offer", r"offer letter", r"salary negotiation",
        r"personal statement", r"portfolio case study", r"cold e-?mails?", r"(?:pm|product|apm) roles?", r"founders?",
    ),
    "pub_noun": (r"(?:research|blog|substack|medium) posts?", r"newsletter", r"article"),
    "hc_verb": (
        r"reply", r"respond", r"e-?mail", r"message", r"follow up", r"negotiate", r"answer", r"thank", r"punchier",
        r"make (?:it|this|them|these) (?:better|stronger|punchier|sharper|crisper|more [\w-]+)", r"summari[sz]e (?:[\w-]+ ){0,4}into",
    ),
    "publish": (
        r"publish(?:ing|ed)?", r"post (?:it|this) (?:on|to)", r"share (?:it )?publicly",
        r"for (?:my )?(?:linkedin|blog|substack|newsletter|medium)",
    ),
    "coding": (
        r"pytest", r"unit tests?", r"tests? for", r"write tests?", r"type hints", r"mypy", r"lint(?:er|ing)?", r"ruff",
        r"makefile", r"github actions?", r"ci", r"regex", r"css", r"html", r"react", r"components?", r"typescript",
        r"javascript", r"python", r"node", r"npm", r"pip", r"sql", r"query", r"queries", r"sqlite", r"postgres",
        r"database", r"db", r"sdk", r"cli", r"argparse", r"plugin", r"async", r"await", r"callbacks?", r"traceback",
        r"stack trace", r"exception", r"bug", r"crash(?:es|ing)?", r"flaky", r"variable", r"method", r"cache",
        r"embeddings?", r"scraper", r"httpx", r"requests", r"docker", r"cron", r"bash", r"git",
        r"commit", r"branch", r"deploy(?:ment)?", r"subcommands?", r"mock", r"frontend", r"backend",
        r"[\w-]+\.(?:py|ts|tsx|js|jsx|css|html|sql|sh|go|rs|java|rb|yml|yaml|toml|ipynb)", r"[a-z_][a-z0-9_]*\(\)",
        r"[\w-]+ clone", r"matplotlib", r"pandas", r"numpy", r"tailwind", r"streamlit", r"next\.?js", r"supabase", r"firebase", r"flask",
        r"django", r"fastapi", r"sqlalchemy", r"eslint", r"prettier", r"tsconfig", r"webpack", r"vite", r"div", r"flexbox",
        r"hover", r"retr(?:y|ies)", r"backoff", r"wrapper", r"charts?", r"plots?", r"dataframe", r"df", r"landing page",
        r"export[- ]to[- ]csv", r"nan", r"null", r"undefined", r"pars(?:e|ing|er)", r"lambda", r"endpoints?", r"(?:my|the|this) (?:app|website|site|extension|bot|script|repo|notebook|pipeline)",
        r"add (?:an? )?[\w -]{0,30} to (?:my|the) [\w -]{0,20}(?:app|site|tool|cli|extension|bot|dashboard)",
    ),
    "money_movement": (
        r"pays?", r"paying", r"auto-?pay(?:s|ing)?", r"wise api", r"paypal", r"razorpay", r"bank transfers?",
        r"send(?:s|ing)? money", r"payroll", r"subscription billing",
    ),
    "security": (
        r"api[- ]?keys?", r"secret keys?", r"(?:auth|access|bearer|refresh|jwt|github|api) tokens?", r"keychain",
        r"ssh keys?", r"2fa", r"mfa", r"injection", r"sanitiz(?:e|ation)", r"hash(?:ing)? passwords?", r"\.env",
        r"leak(?:ed|s)?", r"service role key", r"bucket polic(?:y|ies)", r"iam", r"cors", r"security groups?", r"firewall",
        r"reset (?:flow|tokens?|links?)", r"password reset",
    ),
    "privacy": (
        r"delete (?:my|the|a|user'?s?) account", r"account deletion", r"user'?s'? (?:data|notes|emails|messages|history|records)",
        r"(?:users'?|customer'?s?) (?:data|emails|pii|details)", r"contact lists?", r"location data", r"at rest",
    ),
    "destructive": (
        r"force[- ]?push(?:ing)?", r"reset --hard", r"git reset", r"rewrite (?:the )?history", r"clean up the history",
        r"delete (?:the )?(?:remote )?branch", r"drop (?:the )?[\w]+ table", r"push --force", r"push -f",
        r"delet(?:e|es|ing) (?:all )?(?:users|rows|records|accounts|data) from (?:the )?(?:prod|production|live)",
    ),
    "extraction": (
        r"count", r"how many", r"just the (?:links|urls|numbers|names|dates|titles)", r"find (?:the )?(?:[\w-]+ ){0,3}(?:links|urls)",
        r"look up", r"pull up", r"grab", r"give me (?:the|all|just)", r"(?:just )?tell me (?:the|what)", r"what(?:'s| is) the",
    ),
    "routine": (
        r"reply", r"respond", r"e-?mail", r"mail", r"msg", r"message", r"text (?:for|to)", r"dm", r"slack", r"whatsapp",
        r"alphabeti[sz]e", r"title case", r"lower ?case", r"upper ?case", r"duplicates?", r"dedupe", r"numbered list",
        r"checklist", r"to-?do(?: list)?", r"table", r"markdown", r"template", r"grocery", r"recipes?", r"b-?day",
        r"birthday", r"thank(?:s| you)", r"invite", r"rsvp", r"cancel(?:ling)? (?:my )?(?:membership|subscription|order|booking)",
        r"remind(?:er)?", r"replace (?:every|all)", r"change all", r"turn (?:this|these|my|the) [\w ]{0,40}into",
        r"convert (?:this|these|my|the)", r"put (?:this|these|my) [\w ]{0,30}into", r"shorten", r"clean up", r"lists?",
        r"notes?", r"bullets?", r"spell ?check", r"spelling", r"sort(?:ed)?(?: alphabetically)?", r"reformat", r"headings?",
    ),
}
for _name, _extra in EXTRA_PATTERNS.items():
    PATTERNS[_name] = PATTERNS.get(_name, ()) + _extra

RULES_VERSION = "rules-2026-09-25.4"
_ARTIFACT_REQUEST = re.compile(
    r"^(?:(?:a|an|quick|simple|small|just|pls|please|need)\s+){0,3}(?:bash|python|shell|node|react|sql|typescript|ts|js|go)?\s*"
    r"(?:script|component|function|query|endpoint|regex|makefile|cli|hook|class|unit tests?|tests?|workflow|dockerfile)s?\b",
    re.IGNORECASE,
)
# A coding noun alone ("summarize this post on vector databases") is not a
# coding task; an action or a problem report on the code makes it one.
_CODING_ACTION = re.compile(
    r"\b(?:fix(?:es|ed|ing)?|implement\w*|write|add|build|refactor\w*|migrat\w*|swap|debug\w*|wire|rename|convert|port|"
    r"create|make|set ?up|update|change|remove|delete|upgrade|optimi[sz]e|speed up|help|why|what am i missing|doesn'?t|"
    r"encrypt|generate|clean|center|overlap\w*|breaks?|overflow\w*|goes through|pulls?|reads?|"
    r"does not|isn'?t working|not working|fails?|failing|broken|error|crash\w*|wrong|misses|skips|shows|returns)\b",
    re.IGNORECASE,
)
_CHOICE_QUESTION = re.compile(
    r"(?:\bshould (?:i|we|my|our|the|this) (?:[\w-]+ ){0,4}(?:use|pick|go with|choose|switch to|move to|be)\b|\bwhich (?:is|one is|would be) better\b|\bwhat(?:'s| is) better\b"
    r"|\b[\w.+#-]{1,40} (?:or|vs\.?|versus) [\w.+#-]{1,40}\b[^.!\n]*\?)",
    re.IGNORECASE,
)
_RISK_ACTION = re.compile(
    r"\b(?:audit|handle[sd]?|handling|stor(?:e|es|ing)|encrypt\w*|decrypt\w*|implement\w*|build|automat\w*|script|"
    r"runs? (?:monthly|daily|weekly|nightly)|cron|api|wire|integrat\w*|code|migrat\w*|log(?:s|ging)?|load(?:s|ed|ing)?|"
    r"add|button|feature|flow|clone|app|endpoint|trigger\w*|generat\w*|commit(?:ted)?|push(?:ed)?)\b",
    re.IGNORECASE,
)
_CODE_MARKERS = re.compile(
    # Linear-time: horizontal whitespace only, bounded identifier lengths.
    r"(?m)^[ \t]*(?:def |class |import |from \S{1,80} import|function |const |let |var |return |if [^\n]{0,200}:|"
    r"for [^\n]{0,200}:|#include|SELECT |UPDATE |INSERT |//[ \t]*\w|\}|[\w.\[\]]{1,80}[ \t]*(?:=|\+=|-=)[ \t]*\S|"
    r"[\w.]{1,80}\([^\n]{0,500}\)[ \t]*$)"
    r"|Traceback \(most recent call last\)|^[ \t]+File \"[^\n]{0,300}\", line \d+|=>|\);|\{[ \t]*$",
)
_DATA_REFERENCE = re.compile(
    r"\b(?:this|these|below|following|attached|pasted|here'?s|here is|the text|the notes|the email|the log|the code)\b",
    re.IGNORECASE,
)
_OPERATION_ON_DATA = re.compile(
    r"\b(?:summari[sz]e|extract|fix|format|reformat|rewrite|translate|convert|reply|respond|review|count|clean|sort|"
    r"list|pull|tidy|explain|check|spell|turn|make|debug|add|improve|polish|shorten|edit|proofread|compare|"
    r"categori[sz]e|group|parse|analy[sz]e|dedupe|alphabeti[sz]e|number|merge|split|find|give me|tell me)\b",
    re.IGNORECASE,
)
MAX_CLASSIFIED_CHARS = 60_000

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
    re.compile(r"(?<=[\s:(])'[^'\n]{12,600}'(?=[\s.,;:)!?]|$)"),
    re.compile(r"(?m)^[ \t]*>.*$"),
)

_ARCH_REFERENCE = re.compile(
    r"(?:(?:agreed|approved|accepted|existing|finali[sz]ed|signed[- ]off)(?: \w+){0,2} architecture"
    r"|(?:per|from|following|according to|matching|in) (?:the|our|this|my) (?:\w+ ){0,2}(?:architecture|design doc|design document|spec|handoff))"
    r"|architecture(?:'s| is| has been) (?:approved|agreed|final|signed off)",
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


def split_pasted(text: str) -> tuple[str, str]:
    """Split "instruction: <newline> pasted material" into (instruction, pasted).

    Material pasted after a colon-newline, or a code/log block after a blank
    line, is data: it can show *that* the task involves code, but its words
    never set risk or task kind.
    """
    match = re.search(r":[ \t]*\n", text)
    if match and match.start() >= 3:
        head, tail = text[: match.start()], text[match.end():]
        looks_like_data = bool(_CODE_MARKERS.search(tail)) or tail.lstrip()[:1] in {'"', "'", ">", "|", "{", "["}
        # Split only when the head is an operation on referenced material;
        # "Requirements:\n- store passwords..." keeps its tail as instructions.
        if looks_like_data or (_DATA_REFERENCE.search(head) and _OPERATION_ON_DATA.search(head)):
            return head, tail
        return text, ""
    head, sep, tail = text.partition("\n\n")
    if sep and _CODE_MARKERS.search(tail):
        return head, tail
    return text, ""


def split_instruction(text: str) -> tuple[str, list[str]]:
    """Return (instruction text with quoted material removed, quoted passages)."""
    quoted: list[str] = []
    instruction, pasted = split_pasted(text)
    if pasted:
        quoted.append(pasted)
    for pattern in _QUOTE_PATTERNS:
        def _cut(match: re.Match[str]) -> str:
            quoted.append(match.group(0))
            return " [quoted] "

        instruction = pattern.sub(_cut, instruction)
    return instruction, quoted


def _hits(name: str, text: str) -> list[str]:
    # No negation handling for risk words: "does not leak api keys" is still a
    # security task. Over-routing is the safe direction.
    return [match.group(0) for match in _COMPILED[name].finditer(text)]


def _snippet(text: str, word: str, width: int = 40) -> str:
    index = text.lower().find(word.lower())
    if index < 0:
        return word
    start = max(0, index - width)
    return text[start : index + len(word) + width].strip().replace("\n", " ")


def classify(item: ClassifierInput) -> TaskAssessment:
    text = item.text
    too_long = len(text) > MAX_CLASSIFIED_CHARS
    if too_long:
        text = text[:MAX_CLASSIFIED_CHARS]  # classification only; the full text is still what gets sent
    instruction, quoted = split_instruction(text)
    lowered = instruction.lower()
    _, pasted = split_pasted(text)
    code_context = bool(pasted and _CODE_MARKERS.search(pasted))
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
    coding_intent = bool(_CODING_ACTION.search(instruction) or _ARTIFACT_REQUEST.search(instruction.strip()))
    is_coding = bool(hits["coding"]) and (coding_intent or not (hits["routine"] or is_extraction)) or code_context
    if coding_intent and quoted:
        # Building or changing what was pasted/quoted: its risk is part of the task.
        material = "\n".join(quoted).lower()
        for name in ("money_movement", "security", "privacy", "destructive"):
            extra = _hits(name, material)
            if extra:
                hits[name] = hits[name] + extra
                reasons.append("RISK_IN_MATERIAL_BEING_CHANGED")
    if code_context and not hits["coding"]:
        reasons.append("PASTED_CODE_CONTEXT")

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
    elif _CHOICE_QUESTION.search(instruction) and not (hits["routine"] or hits["extraction"]):
        add(TaskKind.TRADEOFF, "CHOICE_QUESTION", [_CHOICE_QUESTION.search(instruction).group(0)])

    # High-credibility writing: a credibility noun plus a writing/judging verb.
    # Pure extraction from the same document is different (handled below).
    writes_publication = bool(hits["pub_noun"]) and (
        _writes(hits) or any(re.match(r"(?:turn|convert|put)", w) for w in hits["routine"])
    )
    if (writes_publication or (hits["publish"] and (hits["hc_verb"] or hits["routine"] or _writes(hits)))) and not (
        is_extraction and not has_judgement
    ):
        add(TaskKind.HIGH_CREDIBILITY_WRITING, "PUBLICATION_WRITING", hits["publish"])
        flags.append(RiskFlag.HIGH_CREDIBILITY)
    if hits["hc_noun"]:
        hc_verbs = [v for v in hits["hc_verb"] if v not in {"document"}]
        transformation = [w for w in hits["routine"] if re.match(r"(?:turn|convert|put|shorten|clean up)", w)]
        hc_verbs = hc_verbs + transformation
        writing_code = bool(_ARTIFACT_REQUEST.search(instruction.strip()) or re.search(
            r"\bwrite (?:a |an |me a )?(?:python|bash|shell|node|sql)?\s*(?:script|function|program|parser|scraper)", lowered))
        if hc_verbs and not writing_code and not (is_extraction and not has_judgement and not _writes(hits)):
            add(TaskKind.HIGH_CREDIBILITY_WRITING, "HIGH_CREDIBILITY", hits["hc_noun"] + hc_verbs)
            flags.append(RiskFlag.HIGH_CREDIBILITY)
        elif not is_extraction and not hits["routine"] and not writing_code:
            uncertainty.append("credibility-sensitive document mentioned without a clear operation")
            reasons.append("HC_NOUN_UNCLEAR_OPERATION")

    money = hits["money_movement"]
    security = hits["security"]
    privacy = hits["privacy"]
    risk_action_early = bool(_RISK_ACTION.search(instruction)) and bool(hits["money_movement"] or hits["security"] or hits["privacy"])
    pure_extraction = (
        is_extraction and not has_judgement and not _writes(hits) and not (is_coding and coding_intent) and not risk_action_early
    )
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
    risk_action = bool(_RISK_ACTION.search(instruction))
    routine_only = bool(hits["routine"]) and not is_coding
    if risky_coding and not pure_extraction and (is_coding or risk_action):
        add(TaskKind.HIGH_RISK_CODING, "HIGH_RISK_CODING", money + security + privacy)
    elif (security or privacy) and not pure_extraction and not routine_only:
        # Security/privacy matters (incidents, policies, "is this ok?") are consequential.
        add(TaskKind.CONSEQUENTIAL_ASSESSMENT, "SECURITY_PRIVACY_MATTER", security + privacy)
    elif is_coding:
        add(TaskKind.IMPLEMENTATION, "IMPLEMENTATION", hits["coding"])
    elif risky_coding and not is_extraction and not hits["routine"]:
        uncertainty.append("money/security/privacy terms without a clear operation")
        reasons.append("RISK_TERMS_UNCLEAR_OPERATION")

    if hits["production"] and re.search(r"\b(?:delet\w*|drop\w*|truncat\w*|migrat\w*|wipe\w*|update\w* all|backfill\w*)\b", lowered):
        hits["destructive"] = hits["destructive"] + hits["production"]
    if hits["assessment"] or hits["destructive"]:
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

    if too_long:
        uncertainty.append(f"input longer than {MAX_CLASSIFIED_CHARS} characters; only the start was classified")
        reasons.append("LONG_INPUT_ROUTED_UP")
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
        classifier_version=RULES_VERSION,
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
