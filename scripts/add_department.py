"""
CLI để thêm phòng ban mới (alternative cho UI).

Usage:
    python scripts/add_department.py --id sales --name SALES --vi "Bán hàng"
"""
import argparse
import yaml
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--vi", required=True, help="Tên tiếng Việt")
    parser.add_argument("--icon", default="🏢")
    parser.add_argument("--color", default="#58a6ff")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    dept_dir = root / "config" / "departments" / args.id
    dept_dir.mkdir(parents=True, exist_ok=True)
    (dept_dir / "workers").mkdir(exist_ok=True)

    # 1. Tạo department.yaml
    dept_yaml = {
        "id": args.id,
        "name": args.name,
        "name_vi": args.vi,
        "icon": args.icon,
        "color": args.color,
        "description": f"Phòng ban {args.vi}",
        "system_prompt": f"Bạn là quản lý phòng {args.name}. (Cập nhật prompt tại đây.)",
        "workers_path": "./workers",
        "workers": [],
        "default_tools": [],
    }
    (dept_dir / "department.yaml").write_text(
        yaml.safe_dump(dept_yaml, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    # 2. Update _registry.yaml
    reg_path = root / "config" / "departments" / "_registry.yaml"
    reg = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    reg["departments"].append({
        "id": args.id,
        "name": args.name,
        "name_vi": args.vi,
        "icon": args.icon,
        "color": args.color,
        "enabled": True,
        "config_path": f"./config/departments/{args.id}/department.yaml",
    })
    reg_path.write_text(
        yaml.safe_dump(reg, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(f"✓ Created department '{args.name}' at {dept_dir}")
    print(f"✓ Registered in {reg_path}")
    print("Next: thêm worker bằng python scripts/add_worker.py --dept {id} --id <worker_id>")


if __name__ == "__main__":
    main()
