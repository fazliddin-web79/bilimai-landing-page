import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import os


def main() -> None:
    load_dotenv()
    database_path = Path(os.getenv("DATABASE_PATH", "bot.db"))
    if not database_path.exists():
        raise SystemExit(f"Baza topilmadi: {database_path}")

    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{database_path.stem}_{timestamp}.db"
    shutil.copy2(database_path, backup_path)
    print(f"Zaxira nusxa tayyor: {backup_path}")


if __name__ == "__main__":
    main()
