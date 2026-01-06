import re

from typing import List, Optional


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


def extract_contracts(text: str) -> List[dict]:
    """
    从文本中提取所有合约地址

    返回: [{'address': '0x...', 'chain': 'EVM'}, {'address': '...', 'chain': 'SOL'}]
    """
    contracts = []

    # 提取 EVM 合约地址
    for match in EVM_CONTRACT_PATTERN.finditer(text):
        addr = match.group()
        # 避免重复
        if not any(c['address'].lower() == addr.lower() for c in contracts):
            contracts.append({'address': addr, 'chain': 'BSC'})

    # 提取 Solana 合约地址
    for match in SOLANA_CONTRACT_PATTERN.finditer(text):
        addr = match.group()
        # Solana 地址通常以特定字符开头，排除一些明显不是地址的
        # 排除纯数字、常见单词等
        if addr.isdigit():
            continue
        if len(addr) < 32:
            continue
        # 检查是否包含足够的大写字母（Solana 地址通常混合大小写）
        if sum(1 for c in addr if c.isupper()) < 3:
            continue
        # 避免重复
        if not any(c['address'] == addr for c in contracts):
            contracts.append({'address': addr, 'chain': 'SOL'})

    return contracts


def find_matched_keyword(filters: List[str], text: str) -> Optional[str]:
    """
    查找并返回第一个匹配的关键词

    特殊关键词：
    - "0x" → 匹配 EVM 合约地址，返回实际匹配到的地址
    - "ca" → 匹配 Solana 合约地址，返回实际匹配到的地址
    """
    for keyword in filters:
        keyword_lower = keyword.lower().strip()

        # 特殊关键词：EVM 合约地址
        if keyword_lower == "0x":
            match = EVM_CONTRACT_PATTERN.search(text)
            if match:
                return match.group()  # 返回实际匹配到的地址
            continue

        # 特殊关键词：Solana 合约地址
        if keyword_lower == "ca":
            match = SOLANA_CONTRACT_PATTERN.search(text)
            if match:
                return match.group()  # 返回实际匹配到的地址
            continue

        # 普通关键词：单词边界匹配
        pattern = r"(?:^|[\s\W])" + re.escape(keyword) + r"(?:$|[\s\W])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return keyword

    return None
