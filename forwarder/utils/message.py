import re

from typing import List


def predicate_text(filters: List[str], text: str) -> bool:
    """Check if the text contains any of the filters (包含匹配)"""
    text_lower = text.lower()
    for keyword in filters:
        if keyword.lower() in text_lower:
            return True
    return False
