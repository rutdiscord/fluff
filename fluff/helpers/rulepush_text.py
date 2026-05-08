"""Pure text-processing helpers for the rulepush system.

Mods delimit eligible insertion areas in rule content with {{ }}:
  - "{{}}"                       -> one direct insertion slot
  - "{{some words here}}"        -> one slot per gap between/around the words

Keyword selection and rendering are split into separate functions so a session
can be re-rendered later (e.g. after a leave/rejoin) with the *same* keywords
in random slots.
"""

import random
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Union

from database.model.Rule import Rule

KEYWORDS_PER_PUSH = 5

BRACKET_PATTERN = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)


@dataclass
class EmptySlot:
    """Represents a {{}} direct insertion point"""
    rule_index: int
    match_start: int  # start of the {{}} match in the rule content
    match_end: int    # end of the {{}} match


@dataclass
class WordSlot:
    """Represents a position between words inside {{ ... }}"""
    rule_index: int
    match_start: int  # start of the {{ ... }} match in the rule content
    match_end: int    # end of the {{ ... }} match
    inner_text: str   # the text inside the brackets
    insert_index: int # which gap between words (0 = before first word, etc.)


def collect_slots(rules: list[Rule]) -> list[Union[EmptySlot, WordSlot]]:
    """Scans all rules and collects every eligible insertion slot"""
    slots = []

    for rule_index, rule in enumerate(rules):
        for match in BRACKET_PATTERN.finditer(rule.content):
            inner = match.group(1)
            if inner.strip() == "":
                # empty (or whitespace-only) {{}} - single direct slot
                slots.append(EmptySlot(rule_index, match.start(), match.end()))
            else:
                # {{ some words }} - one slot per gap between/around words
                words = inner.split()
                for insert_index in range(len(words) + 1):
                    slots.append(WordSlot(
                        rule_index=rule_index,
                        match_start=match.start(),
                        match_end=match.end(),
                        inner_text=inner,
                        insert_index=insert_index,
                    ))

    return slots


def select_push_keywords(keywords: list[str], count: int = KEYWORDS_PER_PUSH) -> list[str] | None:
    """Picks `count` distinct keywords at random.
    Returns: the chosen keywords, or None if there aren't enough distinct keywords"""
    distinct = list(dict.fromkeys(keywords))
    if len(distinct) < count:
        return None
    return random.sample(distinct, count)


def render_rules(rules: list[Rule], chosen_keywords: list[str]) -> list[Rule] | None:
    """Renders the rules with the given keywords inserted into random slots and
    all remaining {{ }} markers stripped.

    Returns: a new list of Rules, or None if there aren't enough slots"""
    if chosen_keywords is None or rules is None:
        return None

    slots = collect_slots(rules)
    if len(slots) < len(chosen_keywords):
        return None

    chosen_slots = random.sample(slots, len(chosen_keywords))
    return _apply_slots(rules, list(zip(chosen_slots, chosen_keywords)))

def _apply_slots(rules: list[Rule], chosen: list[tuple]) -> list[Rule]:
    """Applies the chosen (slot, keyword) pairs to their rules.

    All replacements for a rule (both empty and word slots) are collected as
    (start, end, new_text) spans against the ORIGINAL content, then applied
    right-to-left in one pass so earlier replacements can't shift the
    positions of later ones."""
    slots_by_rule: dict[int, list] = defaultdict(list)
    for slot, keyword in chosen:
        slots_by_rule[slot.rule_index].append((slot, keyword))

    result = []
    for rule_index, rule in enumerate(rules):
        content = rule.content
        replacements: list[tuple[int, int, str]] = []  # (start, end, new_text)

        rule_slots = slots_by_rule.get(rule_index, [])
        empty_slots = [(s, kw) for s, kw in rule_slots if isinstance(s, EmptySlot)]
        word_slots = [(s, kw) for s, kw in rule_slots if isinstance(s, WordSlot)]

        # empty slots: the whole {{}} marker becomes the keyword
        for slot, keyword in empty_slots:
            replacements.append((slot.match_start, slot.match_end, keyword))

        # word slots: group by bracket so multiple insertions into the same
        # {{ ... }} are rebuilt together
        word_slots_by_match: dict[int, list] = defaultdict(list)
        for slot, keyword in word_slots:
            word_slots_by_match[slot.match_start].append((slot, keyword))

        for match_start, match_slots in word_slots_by_match.items():
            first_slot = match_slots[0][0]
            words = first_slot.inner_text.split()

            insertions: dict[int, list[str]] = defaultdict(list)
            for slot, keyword in match_slots:
                insertions[slot.insert_index].append(keyword)

            new_tokens: list[str] = []
            for i, word in enumerate(words):
                new_tokens.extend(insertions.get(i, []))
                new_tokens.append(word)
            new_tokens.extend(insertions.get(len(words), []))

            replacements.append((match_start, first_slot.match_end, " ".join(new_tokens)))

        for start, end, new_text in sorted(replacements, key=lambda r: r[0], reverse=True):
            content = content[:start] + new_text + content[end:]

        # strip all remaining {{ and }} markers
        content = content.replace("{{", "").replace("}}", "")
        result.append(Rule(rule.rule_number, rule.title, content))

    return result