"""
First-time setup script.

Usage:
    python scripts/setup.py
"""
import shutil
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent

    # 1. Copy .env.example → .env if not exists
    env_example = root / ".env.example"
    env_file = root / ".env"
    if not env_file.exists():
        shutil.copy(env_example, env_file)
        print(f"✓ Created {env_file} — vui lòng điền API keys")

    # 2. Tạo folder traces (nếu chưa)
    (root / "traces").mkdir(exist_ok=True)
    print("✓ Created ./traces/")

    # 3. Verify vault tồn tại
    vault = root / "vault"
    if not vault.exists():
        vault.mkdir()
        print("✓ Created ./vault/")
    else:
        print("✓ Vault already exists")

    print("\n--- Next steps ---")
    print("1. Edit .env and fill API keys + bot tokens")
    print("2. docker-compose up -d        # start Postgres")
    print("3. python scripts/init_db.py   # create tables")
    print("4. bash scripts/start_dev.sh   # run Pio_lab")


if __name__ == "__main__":
    main()
