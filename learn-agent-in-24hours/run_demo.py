from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOUR_PATTERN = re.compile(r"^第(\d+)小时")


def discover_hours() -> dict[int, Path]:
    hours: dict[int, Path] = {}
    for child in ROOT.iterdir():
        if not child.is_dir():
            continue
        match = HOUR_PATTERN.match(child.name)
        if match:
            script_path = child / "src" / "main.py"
            readme_path = child / "README.md"
            # 只把真正落地了教程文件的目录视为可运行章节，避免空占位目录污染结果。
            if not script_path.exists() or not readme_path.exists():
                continue
            hours[int(match.group(1))] = child
    return dict(sorted(hours.items()))


def list_hours(hours: dict[int, Path]) -> None:
    print("可运行章节：")
    for number, path in hours.items():
        print(f"  {number:>2} -> {path.name}")


def run_hour(hour: int, hours: dict[int, Path]) -> int:
    target = hours.get(hour)
    if target is None:
        print(f"未找到第 {hour} 小时的目录。")
        print("你可以先运行 `python run_demo.py --list` 查看可用章节。")
        return 1

    script_path = target / "src" / "main.py"
    if not script_path.exists():
        print(f"{target.name} 下还没有 `src/main.py`。")
        return 1

    print(f"正在运行：{target.name}", flush=True)
    print("-" * 60, flush=True)
    completed = subprocess.run([sys.executable, str(script_path)], cwd=str(ROOT))
    print("-" * 60, flush=True)
    if completed.returncode != 0:
        print("章节运行失败。若这是框架章节，请先执行 `pip install -r requirements.txt`。")
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行《24小时学会 Agent 开发》的指定章节案例。")
    parser.add_argument("hour", nargs="?", type=int, help="要运行的章节号，例如 1 或 12")
    parser.add_argument("--list", action="store_true", help="列出所有可运行章节")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    hours = discover_hours()
    if args.list or args.hour is None:
        list_hours(hours)
        return 0

    return run_hour(args.hour, hours)


if __name__ == "__main__":
    raise SystemExit(main())
