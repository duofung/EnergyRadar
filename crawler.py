#!/usr/bin/env python3
"""
crawler.py — 全球能源招标数据抓取脚本（德国已接入真实数据）
用法: python crawler.py
输出: 更新当前目录下的 data.json

数据源:
├── 德国/欧洲 ✅ 真实数据
│   ├── TED Search API（欧盟官方，免费，无需API Key）
│   └── Bundesnetzagentur 招标日程（官网结构化数据）
└── 其他地区 🔜 模拟数据（待逐个替换）
"""

import json
import os
from datetime import datetime, timedelta

# ═══════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OUTPUT_FILE = "data.json"

# TED Search API — 免费，匿名访问，无需注册
TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"


# ═══════════════════════════════════════════
# AI 翻译
# ═══════════════════════════════════════════

def translate_to_chinese(text: str) -> str:
    """将外语翻译为简洁中文"""
    if not text:
        return text
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    if chinese_chars > len(text) * 0.3:
        return text

    if OPENAI_API_KEY:
        try:
            import requests
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "你是能源行业翻译。将招标信息翻译成简洁中文，保留MW、地点等数据。只输出翻译。"},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 200, "temperature": 0.1,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"  [翻译] OpenAI 失败: {e}")

    if GEMINI_API_KEY:
        try:
            import requests
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": f"翻译为简洁中文，保留数据：\n{text}"}]}]},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"  [翻译] Gemini 失败: {e}")

    return text


# ═══════════════════════════════════════════
# 数据源 1: TED Search API（德国 + 欧洲）
# ═══════════════════════════════════════════
# 官方文档: https://docs.ted.europa.eu/api/latest/search.html
# ✅ 免费 | ✅ 无需API Key | ✅ 匿名访问
#
# CPV 代码（欧盟通用采购分类）:
#   09330000 - 太阳能 (Solar energy)
#   09331200 - 光伏模块 (Solar photovoltaic modules)
#   09332000 - 太阳能安装 (Solar installation)
#   31440000 - 蓄电池 (Batteries)
#   45261215 - 太阳能屋顶工程

def fetch_ted_germany() -> list:
    """从 TED API 抓取德国能源招标（真实数据）"""
    import requests

    print("[抓取] 🇩🇪 TED Europa — 德国能源招标")
    tenders = []

    # TED Expert Query 语法
    queries = [
        'country = "DEU" AND cpv = "09330000"',   # 太阳能
        'country = "DEU" AND cpv = "31440000"',   # 储能/电池
        'country = "DEU" AND cpv = "45261215"',   # 光伏屋顶工程
    ]

    for query in queries:
        try:
            resp = requests.post(
                TED_API_URL,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json={
                    "query": query,
                    "fields": ["publication-number", "notice-title", "submission-deadline",
                               "buyer-name", "cpv-code", "place-of-performance"],
                    "pageSize": 20,
                    "pageNum": 1,
                    "scope": "ACTIVE",
                },
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                notices = data.get("notices", data.get("results", []))

                if isinstance(notices, list):
                    for notice in notices[:10]:
                        if not isinstance(notice, dict):
                            continue

                        title = (notice.get("notice-title") or notice.get("title") or
                                 notice.get("TI") or "")
                        if isinstance(title, list):
                            title = title[0] if title else ""
                        if isinstance(title, dict):
                            title = title.get("de", title.get("en", str(title)))

                        deadline = str(notice.get("submission-deadline") or
                                       notice.get("deadline") or notice.get("DT") or "")[:10]

                        pub_number = str(notice.get("publication-number") or
                                         notice.get("ND") or "")

                        if title:
                            name_cn = translate_to_chinese(str(title))
                            tenders.append({
                                "country": "德国",
                                "location": "德国",
                                "name": name_cn,
                                "capacity_mw": 0,
                                "deadline": deadline or "见公告",
                                "status": "进行中",
                                "source": "TED Europa",
                                "ref": pub_number,
                            })

                print(f"  ✅ [{query[:50]}] → {len(notices) if isinstance(notices, list) else 0} 条")
            else:
                print(f"  ⚠️ HTTP {resp.status_code}")

        except Exception as e:
            print(f"  ❌ 查询失败: {e}")

    # 去重
    seen = set()
    unique = []
    for t in tenders:
        if t["name"] not in seen:
            seen.add(t["name"])
            unique.append(t)

    print(f"  📊 去重后共 {len(unique)} 条")
    return unique


def fetch_bundesnetzagentur() -> list:
    """
    德国联邦网络管理局 (BNetzA) 太阳能招标轮次
    来源: bundesnetzagentur.de
    没有公开API，数据为官网公告结构化整理
    2026年日程:
    - 地面光伏 Segment 1: 3/1, 7/1, 12/1（年总量 9,900 MW）
    - 屋顶光伏 Segment 2: 2/1, 6/1, 10/1（年总量 1,100 MW）
    """
    print("[抓取] 🇩🇪 Bundesnetzagentur 太阳能招标日程")

    today = datetime.now()
    tenders = []

    schedule = [
        {"name": "BNetzA 地面光伏招标 第一轮", "deadline": "2026-03-01", "capacity_mw": 3300,
         "detail": "~3,300 MW | Segment 1 Freifläche"},
        {"name": "BNetzA 地面光伏招标 第二轮", "deadline": "2026-07-01", "capacity_mw": 3300,
         "detail": "~3,300 MW | Segment 1"},
        {"name": "BNetzA 地面光伏招标 第三轮", "deadline": "2026-12-01", "capacity_mw": 3300,
         "detail": "~3,300 MW | Segment 1"},
        {"name": "BNetzA 屋顶光伏招标 第一轮", "deadline": "2026-02-01", "capacity_mw": 367,
         "detail": "~367 MW | Segment 2 Gebäude"},
        {"name": "BNetzA 屋顶光伏招标 第二轮", "deadline": "2026-06-01", "capacity_mw": 367,
         "detail": "~367 MW | Segment 2"},
        {"name": "BNetzA 屋顶光伏招标 第三轮", "deadline": "2026-10-01", "capacity_mw": 367,
         "detail": "~367 MW | Segment 2"},
    ]

    for item in schedule:
        d = datetime.strptime(item["deadline"], "%Y-%m-%d")
        if d >= today - timedelta(days=30):
            tenders.append({
                "country": "德国", "location": "全德国",
                "name": item["name"],
                "capacity_mw": item["capacity_mw"],
                "deadline": item["deadline"],
                "status": "进行中" if d >= today else "已截止",
                "source": "Bundesnetzagentur",
            })

    print(f"  ✅ {len(tenders)} 条活跃招标")
    return tenders


# ═══════════════════════════════════════════
# 其他地区（模拟数据，待逐个替换）
# ═══════════════════════════════════════════

def fetch_vietnam():
    print("[抓取] 🇻🇳 越南 — 模拟数据")
    b = datetime.now()
    return [
        {"country":"越南","location":"海防","name":"LG 工厂 5MW 工商业光伏需求","capacity_mw":5,
         "deadline":(b+timedelta(days=44)).strftime("%Y-%m-%d"),"status":"进行中","source":"模拟"},
        {"country":"越南","location":"胡志明市","name":"政府大楼光伏试点项目","capacity_mw":2,
         "deadline":(b+timedelta(days=60)).strftime("%Y-%m-%d"),"status":"进行中","source":"模拟"},
    ]

def fetch_usa():
    print("[抓取] 🇺🇸 美国 — 模拟数据")
    b = datetime.now()
    return [
        {"country":"美国","location":"加州","name":"50MW 公用事业级太阳能+储能项目","capacity_mw":50,
         "deadline":(b+timedelta(days=90)).strftime("%Y-%m-%d"),"status":"进行中","source":"模拟"},
        {"country":"美国","location":"德州","name":"独立储能项目咨询","capacity_mw":30,
         "deadline":(b+timedelta(days=70)).strftime("%Y-%m-%d"),"status":"进行中","source":"模拟"},
    ]

def fetch_brazil():
    print("[抓取] 🇧🇷 巴西 — 模拟数据")
    b = datetime.now()
    return [
        {"country":"巴西","location":"圣保罗","name":"分布式光伏项目采购","capacity_mw":12,
         "deadline":(b+timedelta(days=35)).strftime("%Y-%m-%d"),"status":"进行中","source":"模拟"},
    ]

def fetch_africa():
    print("[抓取] 🌍 南非 — 模拟数据")
    b = datetime.now()
    return [
        {"country":"南非","location":"开普敦","name":"10MW 私人电力采购协议需求","capacity_mw":10,
         "deadline":(b+timedelta(days=50)).strftime("%Y-%m-%d"),"status":"进行中","source":"模拟"},
    ]

def fetch_australia():
    print("[抓取] 🇦🇺 澳大利亚 — 模拟数据")
    b = datetime.now()
    return [
        {"country":"澳大利亚","location":"新南威尔士","name":"100MW 大电池项目招标","capacity_mw":100,
         "deadline":(b+timedelta(days=100)).strftime("%Y-%m-%d"),"status":"进行中","source":"模拟"},
    ]


# ═══════════════════════════════════════════
# 分类 + 主流程
# ═══════════════════════════════════════════

def classify_continent(country):
    m = {
        "europe": ["德国","法国","英国","西班牙","意大利","荷兰","全德国"],
        "asia": ["越南","印度","泰国","日本","韩国","中国","马来西亚"],
        "north_america": ["美国","加拿大","墨西哥"],
        "south_america": ["巴西","智利","阿根廷"],
        "africa": ["南非","肯尼亚","尼日利亚","埃及"],
        "oceania": ["澳大利亚","新西兰"],
    }
    for k, v in m.items():
        if any(c in country for c in v):
            return k
    return "asia"

def run():
    print("=" * 60)
    print(f"🔄 招标数据更新 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_tenders = []

    sources = [
        ("TED 德国", fetch_ted_germany),
        ("BNetzA", fetch_bundesnetzagentur),
        ("越南", fetch_vietnam),
        ("美国", fetch_usa),
        ("巴西", fetch_brazil),
        ("南非", fetch_africa),
        ("澳大利亚", fetch_australia),
    ]

    for name, fn in sources:
        try:
            items = fn()
            all_tenders.extend(items)
        except Exception as e:
            print(f"  ❌ {name}: {e}")

    grouped = {"europe":[],"asia":[],"north_america":[],"south_america":[],"africa":[],"oceania":[]}
    for t in all_tenders:
        grouped[classify_continent(t.get("country",""))].append(t)

    for k in grouped:
        grouped[k].sort(key=lambda x: x.get("deadline","9999"))

    grouped["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 写入 {OUTPUT_FILE} — 共 {len(all_tenders)} 条")
    for k in ["europe","asia","north_america","south_america","africa","oceania"]:
        print(f"   {k}: {len(grouped[k])} 条")

if __name__ == "__main__":
    run()
