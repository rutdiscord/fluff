from dataclasses import dataclass


@dataclass
class Rule:
    rule_number: int #the rule number in the list of all rules for this server
    title: str #the title of this rule
    content: str #the raw content of this rule