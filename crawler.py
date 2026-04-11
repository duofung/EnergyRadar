#!/usr/bin/env python3
"""
crawler.py — 全球能源招标数据自动抓取 & 翻译脚本
用法: python crawler.py
输出: 更新当前目录下的 data.json

架构说明:
- 目前使用模拟数据填充，保留了真实抓取的接口结构
- 当你准备好接入真实数据源时，只需替换各 fetch_* 函数的实现
- AI 翻译使用 OpenAI API（也可切换为 Google Gemini）
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional
import random

# ═══════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════

# 从环境变量读取 API Key（GitHub Secrets 注入）
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

OUTPUT_FILE = "data.json"

# ═══════════════════════════════════════════
# AI 翻译模块
# ═══════════════════════════════════════════

def translate_to_chinese(text: str, source_lang: str = "auto") -> str:
    """
    将外语文本翻译为简洁的中文。
    优先使用 OpenAI，备选 Gemini。
    如果都没有 API Key，则返回原文。
    """
    if not text or all('\u4e00' <= c <= '\u9fff' for c in text if c.strip()):
        return text  # 已经是中文

    # ── OpenAI 翻译 ──
    if OPENAI_API_KEY:
        try:
            import requests
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "你是一个专业的能源行业翻译。"
                                "请将以下招标信息翻译成简洁的中文，保留关键数据（MW、地点、日期）。"
                                "只输出翻译结果，不要解释。"
                            ),
                        },
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.1,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[翻译] OpenAI 调用失败: {e}")

    # ── Gemini 翻译（备选）──
    if GEMINI_API_KEY:
        try:
            import requests
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}",
                json={
                    "contents": [{
                        "parts": [{
                            "text": f"将以下能源招标信息翻译成简洁的中文，保留MW、地点等数据。只输出翻译：\n{text}"
                        }]
                    }]
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"[翻译] Gemini 调用失败: {e}")

    # 无 API Key 时返回原文
    print(f"[翻译] 无可用 API，返回原文: {text[:50]}...")
    return text


def classify_continent(country: str) -> str:
    """根据国家名判断所属大洲 key"""
    mapping = {
        "europe": [
            "Germany", "France", "UK", "Spain", "Italy", "Netherlands",
            "Poland", "Sweden", "Denmark", "Norway", "Austria", "Belgium",
            "Portugal", "Greece", "Romania", "Czech", "Finland", "Ireland",
            "德国", "法国", "英国", "西班牙", "意大利", "荷兰", "波兰",
        ],
        "asia": [
            "Vietnam", "India", "Thailand", "Japan", "Korea", "Indonesia",
            "Malaysia", "Philippines", "China", "Singapore", "Pakistan",
            "Saudi Arabia", "UAE", "Qatar", "Oman",
            "越南", "印度", "泰国", "日本", "韩国", "中国", "马来西亚",
            "沙特", "阿联酋",
        ],
        "north_america": [
            "USA", "United States", "Canada", "Mexico",
            "美国", "加拿大", "墨西哥",
        ],
        "south_america": [
            "Brazil", "Chile", "Argentina", "Colombia", "Peru",
            "巴西", "智利", "阿根廷",
        ],
        "africa": [
            "South Africa", "Kenya", "Nigeria", "Egypt", "Morocco",
            "Ethiopia", "Tanzania", "Ghana",
            "南非", "肯尼亚", "尼日利亚", "埃及",
        ],
        "oceania": [
            "Australia", "New Zealand",
            "澳大利亚", "新西兰",
        ],
    }
    for continent, countries in mapping.items():
        if any(c.lower() in country.lower() for c in countries):
            return continent
    return "asia"  # 默认


# ═══════════════════════════════════════════
# 数据源抓取（模拟）
# ═══════════════════════════════════════════
# 当你准备好接入真实网站时，替换下面每个函数的实现即可。
# 保持返回格式不变：list[dict]

def fetch_eu_ted() -> list:
    """
    欧盟 TED 招标网 (https://ted.europa.eu)
    真实接入时：使用 TED API 或 RSS feed
    """
    print("[抓取] 欧盟 TED — 使用模拟数据")
    base = datetime.now()
    return [
        {
            "country": "德国",
            "location": "柏林",
            "name": "2MW 市政屋顶光伏招标",
            "capacity_mw": 2,
            "deadline": (base + timedelta(days=random.randint(20, 60))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "TED",
        },
        {
            "country": "德国",
            "location": "汉堡",
            "name": "港口太阳能+储能项目",
            "capacity_mw": 5,
            "deadline": (base + timedelta(days=random.randint(30, 70))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "TED",
        },
        {
            "country": "法国",
            "location": "里昂",
            "name": "工业园区 10MW 地面光伏电站",
            "capacity_mw": 10,
            "deadline": (base + timedelta(days=random.randint(40, 90))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "TED",
        },
        {
            "country": "西班牙",
            "location": "巴塞罗那",
            "name": "港口微电网储能系统",
            "capacity_mw": 8,
            "deadline": (base + timedelta(days=random.randint(25, 55))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "TED",
        },
    ]


def fetch_vietnam() -> list:
    """越南政府采购网"""
    print("[抓取] 越南采购网 — 使用模拟数据")
    base = datetime.now()
    return [
        {
            "country": "越南",
            "location": "海防",
            "name": "LG 工厂 5MW 工商业光伏需求",
            "capacity_mw": 5,
            "deadline": (base + timedelta(days=random.randint(20, 50))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "Vietnam Procurement",
        },
        {
            "country": "越南",
            "location": "胡志明市",
            "name": "政府大楼光伏试点项目",
            "capacity_mw": 2,
            "deadline": (base + timedelta(days=random.randint(30, 60))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "Vietnam Procurement",
        },
    ]


def fetch_sam_gov() -> list:
    """美国 SAM.gov 联邦采购"""
    print("[抓取] SAM.gov — 使用模拟数据")
    base = datetime.now()
    return [
        {
            "country": "美国",
            "location": "加州",
            "name": "50MW 公用事业级太阳能+储能项目",
            "capacity_mw": 50,
            "deadline": (base + timedelta(days=random.randint(60, 120))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "SAM.gov",
        },
        {
            "country": "美国",
            "location": "德州",
            "name": "独立储能项目咨询",
            "capacity_mw": 30,
            "deadline": (base + timedelta(days=random.randint(40, 80))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "SAM.gov",
        },
        {
            "country": "美国",
            "location": "纽约",
            "name": "公共事业屋顶光伏招标",
            "capacity_mw": 15,
            "deadline": (base + timedelta(days=random.randint(50, 100))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "SAM.gov",
        },
    ]


def fetch_brazil() -> list:
    """巴西 ComprasNet"""
    print("[抓取] ComprasNet — 使用模拟数据")
    base = datetime.now()
    return [
        {
            "country": "巴西",
            "location": "圣保罗",
            "name": "分布式光伏项目采购",
            "capacity_mw": 12,
            "deadline": (base + timedelta(days=random.randint(15, 45))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "ComprasNet",
        },
        {
            "country": "巴西",
            "location": "里约",
            "name": "储能系统试验项目咨询",
            "capacity_mw": 5,
            "deadline": (base + timedelta(days=random.randint(30, 60))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "ComprasNet",
        },
    ]


def fetch_africa() -> list:
    """南非 eTenders"""
    print("[抓取] eTenders — 使用模拟数据")
    base = datetime.now()
    return [
        {
            "country": "南非",
            "location": "开普敦",
            "name": "10MW 私人电力采购协议需求",
            "capacity_mw": 10,
            "deadline": (base + timedelta(days=random.randint(20, 50))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "eTenders",
        },
        {
            "country": "南非",
            "location": "约翰内斯堡",
            "name": "市政微电网项目招标",
            "capacity_mw": 3,
            "deadline": (base + timedelta(days=random.randint(40, 80))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "eTenders",
        },
    ]


def fetch_australia() -> list:
    """澳大利亚 AusTender"""
    print("[抓取] AusTender — 使用模拟数据")
    base = datetime.now()
    return [
        {
            "country": "澳大利亚",
            "location": "新南威尔士",
            "name": "100MW 大电池项目招标",
            "capacity_mw": 100,
            "deadline": (base + timedelta(days=random.randint(60, 120))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "AusTender",
        },
        {
            "country": "澳大利亚",
            "location": "维多利亚",
            "name": "户用储能补贴计划需求",
            "capacity_mw": 0,
            "deadline": (base + timedelta(days=random.randint(40, 80))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "AusTender",
        },
        {
            "country": "澳大利亚",
            "location": "昆士兰",
            "name": "太阳能农场开发权招标",
            "capacity_mw": 75,
            "deadline": (base + timedelta(days=random.randint(30, 70))).strftime("%Y-%m-%d"),
            "status": "进行中",
            "source": "AusTender",
        },
    ]


# ═══════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════

def run():
    print("=" * 50)
    print(f"🔄 开始抓取 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 1) 从所有数据源收集原始数据
    all_tenders = []
    sources = [
        fetch_eu_ted,
        fetch_vietnam,
        fetch_sam_gov,
        fetch_brazil,
        fetch_africa,
        fetch_australia,
    ]
    for fn in sources:
        try:
            items = fn()
            all_tenders.extend(items)
            print(f"  ✅ {fn.__doc__.strip().split(chr(10))[0]} — {len(items)} 条")
        except Exception as e:
            print(f"  ❌ {fn.__name__} 失败: {e}")

    # 2) 翻译（如果有 API Key 且文本非中文）
    for t in all_tenders:
        t["name"] = translate_to_chinese(t.get("name", ""))

    # 3) 按大洲分类
    grouped = {
        "europe": [],
        "asia": [],
        "north_america": [],
        "south_america": [],
        "africa": [],
        "oceania": [],
    }
    for t in all_tenders:
        continent = classify_continent(t.get("country", ""))
        grouped[continent].append(t)

    # 4) 每个大洲按截止日期排序（最近的在前）
    for key in grouped:
        grouped[key].sort(key=lambda x: x.get("deadline", "9999-12-31"))

    # 5) 加时间戳
    grouped["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 6) 写入 data.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已更新 {OUTPUT_FILE}（共 {len(all_tenders)} 条招标信息）")
    print(f"   文件大小: {os.path.getsize(OUTPUT_FILE)} bytes")


if __name__ == "__main__":
    run()
