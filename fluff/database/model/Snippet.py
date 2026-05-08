from dataclasses import dataclass


@dataclass
class Snippet:
    name: str #the name of the snippet
    content: str #the actual body text to display for this snippet
    aliases: list[str] | None #optional list of aliases that can be used to invoke this snippet