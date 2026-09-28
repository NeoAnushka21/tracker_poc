"""Rule-based routing: what kind of message this is (intent) and which model tier it needs.

Rules are free and deterministic. They lean towards the large tier when unsure: a wrong
"complex" only costs quota, while a wrong "simple" is caught by validation and escalated.
Each intent also gets only the tools and prompt sections it needs, which roughly halves the
tokens of most calls.
"""
import re
from dataclasses import dataclass

QUERY_TOOLS = ["get_logs", "get_daily_summary", "get_food"]
EDIT_TOOLS = ["propose_edit", "propose_delete", "propose_move", "propose_entry", "get_logs", "get_daily_summary", "get_food"]
LOG_TOOLS = ["propose_entry", "propose_water", "get_food"]
LOG_LARGE_TOOLS = LOG_TOOLS + ["propose_recipe"]
ALL_TOOLS = None   # every tool

# Prompt sections (by their "## " heading in prompt.SYSTEM_STABLE) per intent. "intro" and
# "style" are always included.
SECTIONS = {
    "query": ["queries", "date"],
    "edit": ["logging", "library", "confirmation", "date", "editing"],
    "log": ["logging", "library", "confirmation", "date"],
    "log_large": ["logging", "library", "recipes", "confirmation", "date"],
    "full": None,   # every section
}


@dataclass(frozen=True)
class Route:
    intent: str          # query | edit | log | full
    tier: str            # small | large
    tools: list[str] | None
    sections: list[str] | None
    reason: str


_QUESTION_START = re.compile(
    r"^\s*(?:what|how|when|which|where|why|did|do i|does|have i|has|am i|was|were|is my|are my|"
    r"show|list|tell me|give me|summari[sz]e|compare|check)\b", re.I)
_EDIT = re.compile(
    r"\b(?:move|shift|copy|duplicate|delete|remove|undo|change|update|edit|correct|replace|swap|"
    r"instead|actually|wrong|mistake|wasn'?t|was not|make (?:it|that|the)|should be|not \d)\b", re.I)
_RECIPE = re.compile(r"\brecipes?\b", re.I)
_QTY = re.compile(r"\d|\b(?:a|an|one|two|three|four|five|six|half|couple)\b", re.I)
# Portions or dishes whose contents vary a lot: worth the large model's judgement.
_VAGUE = re.compile(
    r"\b(?:sandwich|burger|pizza|wrap|roll|thali|plate|bowl|some|few|bit|biryani|pulao|curry|"
    r"sabzi|sabji|gravy|salad|smoothie|shake|restaurant|takeaway|combo|meal deal|homemade|"
    r"home-made|leftover|buffet|party|dessert|sweets?|mithai|snacks)\b", re.I)
_MEALS = re.compile(r"\b(?:breakfast|lunch|dinner|brunch|supper|snack)\b", re.I)
_SPLIT = re.compile(r"\s*(?:,|;|\band\b|&|\+|\bwith\b|\bplus\b)\s*", re.I)


def count_items(text: str) -> int:
    return len([p for p in _SPLIT.split(text) if p.strip()])


def route(text: str, *, feedback: bool = False) -> Route:
    words = len(text.split())
    if feedback:
        return Route("full", "large", ALL_TOOLS, SECTIONS["full"], "feedback on a card")
    if _RECIPE.search(text):
        return Route("full", "large", ALL_TOOLS, SECTIONS["full"], "recipe")
    if words > 40:
        return Route("full", "large", ALL_TOOLS, SECTIONS["full"], "long message")
    if _EDIT.search(text):
        tier = "large" if count_items(text) >= 3 or _VAGUE.search(text) else "small"
        return Route("edit", tier, EDIT_TOOLS, SECTIONS["edit"], "edit words")
    if _QUESTION_START.search(text) and not re.search(r"\b(?:had|ate|drank|eaten)\b", text, re.I):
        return Route("query", "small", QUERY_TOOLS, SECTIONS["query"], "question")
    # Food logging (the default).
    if len(set(m.lower() for m in _MEALS.findall(text))) >= 2:
        return Route("log", "large", LOG_LARGE_TOOLS, SECTIONS["log_large"], "several meals")
    if count_items(text) >= 3:
        return Route("log", "large", LOG_LARGE_TOOLS, SECTIONS["log_large"], "3+ foods")
    if _VAGUE.search(text):
        return Route("log", "large", LOG_LARGE_TOOLS, SECTIONS["log_large"], "vague portion or mixed dish")
    if not _QTY.search(text):
        return Route("log", "large", LOG_LARGE_TOOLS, SECTIONS["log_large"], "no amounts")
    return Route("log", "small", LOG_TOOLS, SECTIONS["log"], "simple food log")


def escalate(r: Route) -> Route:
    """After repeated validation errors on the small tier: large tier, every tool and section."""
    return Route("full", "large", ALL_TOOLS, SECTIONS["full"], f"escalated from {r.intent}/{r.tier}")
