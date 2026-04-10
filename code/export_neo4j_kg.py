import json
import os
import re
from pathlib import Path
from typing import Dict, List

from py2neo import Graph

SUPPORTED_DATASET_NAMES = ["REDD", "UK-DALE", "REFIT"]


# =========================
# 直接在这里改参数（无需命令行）
# =========================
DATA_ROOT = r"F:/研究生文件/节能减排/云端功率分析代码/output/按日分析结果_全部"   # 支持：总根目录 / 单个数据集目录 / 单个house目录
OUT_ROOT = r"F:\研究生文件\节能减排\云端功率分析代码\output\kg_export"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "20010908")
NEO4J_DB = os.getenv("NEO4J_DB", "neo4j")

# 可选过滤：留空表示导出全部
ONLY_DATASET = ""   # 例如 "REDD"
ONLY_HOUSE = ""     # 例如 "House1_stats"


def extract_house_number(name: str) -> str:
    match = re.search(r"House[_\-]?(\d+)", name, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    digits = re.findall(r"\d+", name)
    return digits[-1] if digits else "1"


def scan_houses(data_root: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if not data_root.exists() or not data_root.is_dir():
        return rows

    # 情况1：总根目录（下级是 REDD/UK-DALE/REFIT）
    dataset_dirs = [p for p in data_root.iterdir() if p.is_dir() and p.name in SUPPORTED_DATASET_NAMES]

    # 情况2：传入的是单个数据集目录（如 .../output/REDD）
    if not dataset_dirs and data_root.name in SUPPORTED_DATASET_NAMES:
        dataset_dirs = [data_root]

    # 情况3：传入的是单个 house 目录（如 .../REDD/House1_stats）
    if not dataset_dirs and any(data_root.glob("*.xlsx")):
        dataset_name = data_root.parent.name if data_root.parent.name in SUPPORTED_DATASET_NAMES else "CUSTOM"
        no = extract_house_number(data_root.name)
        rows.append(
            {
                "dataset": dataset_name,
                "house_key": data_root.name,
                "user_name": f"用户{no}",
            }
        )
        return rows

    for ds in sorted(dataset_dirs):
        for house_dir in sorted([p for p in ds.iterdir() if p.is_dir()]):
            has_excel = any(house_dir.glob("*.xlsx"))
            if not has_excel:
                continue
            no = extract_house_number(house_dir.name)
            rows.append(
                {
                    "dataset": ds.name,
                    "house_key": house_dir.name,
                    "user_name": f"用户{no}",
                }
            )
    return rows


def export_one_user(graph: Graph, user_name: str) -> Dict[str, object]:
    user_rows = graph.run(
        """
        MATCH (u:用户 {名称:$name})
        RETURN u.名称 AS name, u.`平均日用电量（kwh）` AS avg_kwh, u.统计天数 AS days
        """,
        name=user_name,
    ).data()

    if not user_rows:
        return {"ok": False, "error": f"未找到用户节点: {user_name}"}

    app_rows = graph.run(
        """
        MATCH (:用户 {名称:$name})-[:拥有]->(a:电器)
        RETURN a.名称 AS name,
               a.工作日开启时段 AS weekday_periods,
               a.周末开启时段 AS weekend_periods,
               a.额定功率 AS rated_power
        ORDER BY name
        """,
        name=user_name,
    ).data()

    edge_rows = graph.run(
        """
        MATCH (:用户 {名称:$name})-[:拥有]->(a1:电器)-[r:同时开启]->(a2:电器)
        RETURN a1.名称 AS source,
               a2.名称 AS target,
               r.工作日重叠时段文本 AS weekday_overlap,
               r.周末重叠时段文本 AS weekend_overlap
        """,
        name=user_name,
    ).data()

    return {
        "ok": True,
        "user": user_rows[0],
        "appliances": app_rows,
        "edges": edge_rows,
    }


def main() -> None:
    data_root = Path(DATA_ROOT)
    out_root = Path(OUT_ROOT)
    out_root.mkdir(parents=True, exist_ok=True)

    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), name=NEO4J_DB)

    houses = scan_houses(data_root)
    if ONLY_DATASET:
        houses = [h for h in houses if h["dataset"] == ONLY_DATASET]
    if ONLY_HOUSE:
        houses = [h for h in houses if h["house_key"] == ONLY_HOUSE]

    if not houses:
        print("未扫描到可导出的 house。请检查 DATA_ROOT / ONLY_DATASET / ONLY_HOUSE 配置。")
        return

    ok_count = 0
    skip_count = 0

    for item in houses:
        dataset = item["dataset"]
        house_key = item["house_key"]
        user_name = item["user_name"]

        result = export_one_user(graph, user_name)
        if not result.get("ok"):
            print(f"[跳过] {dataset}/{house_key} -> {result.get('error')}")
            skip_count += 1
            continue

        out_file = out_root / dataset / f"{house_key}.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_payload = {
            "user": result["user"],
            "appliances": result["appliances"],
            "edges": result["edges"],
        }
        out_file.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[成功] {dataset}/{house_key} -> {out_file}")
        ok_count += 1

    print(f"导出完成：成功 {ok_count}，跳过 {skip_count}，总计 {len(houses)}")


if __name__ == "__main__":
    main()
