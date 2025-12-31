import re

from typing import List


# EVM 合约地址：0x + 40位十六进制
EVM_CONTRACT_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")

# Solana 合约地址：Base58，32-44字符（排除常见短词干扰）
SOLANA_CONTRACT_PATTERN = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")


def predicate_text(filters: List[str], text: str) -> bool:
    """
    检查消息是否匹配过滤条件

    特殊关键词：
    - "0x" → 匹配 EVM 合约地址 (0x + 40位十六进制)
    - "ca" → 匹配 Solana 合约地址 (Base58, 32-44字符)

    普通关键词：使用单词边界匹配（不区分大小写）
    """
    for keyword in filters:
        keyword_lower = keyword.lower().strip()

        # 特殊关键词：EVM 合约地址
        if keyword_lower == "0x":
            if EVM_CONTRACT_PATTERN.search(text):
                return True
            continue

        # 特殊关键词：Solana 合约地址
        if keyword_lower == "ca":
            if SOLANA_CONTRACT_PATTERN.search(text):
                return True
            continue

        # 普通关键词：单词边界匹配
        pattern = r"(?:^|[\s\W])" + re.escape(keyword) + r"(?:$|[\s\W])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True

    return False
