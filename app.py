import logging
from pathlib import Path
from models import DatabaseManager
from manager import BackupManager
from core import CompressionType


def main():
    try:
        db = DatabaseManager()
        db.create_db()
        logging.info("Database created successfully.")
        docs_path = Path.home() / "Desktop/DataSafe"
        backup_mgr = BackupManager(
            docs_path,
            calculate_size=True,
            compressed=True,
            compression_type=CompressionType.ZIP,  # TAR, TAR_GZ, ZIP
        )
        backup_mgr.save_backup_metadata()
        logging.debug(f"Backup archive: {backup_mgr.backup_archive}")
        logging.info("Backup completed successfully.")
        backup_mgr.close()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    main()
