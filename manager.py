import logging
from pathlib import Path
from core import SourceDirectory, BackupArchive, CompressionType
from models import DatabaseManager, DirectoryModel, BackupModel


class BackupManager:
    def __init__(
        self,
        path: Path | str,
        calculate_size: bool,
        compressed: bool,
        compression_type: CompressionType = CompressionType.ZIP,
    ):
        try:
            self.db = DatabaseManager()
            self.session = self.db.get_session()

            if isinstance(path, str):
                path = Path(path)

            self.source_dir = SourceDirectory(path, calculate_size)
            self.backup_archive = BackupArchive(
                self.source_dir, compressed, compression_type=compression_type
            )
        except Exception as e:
            logging.error(f"BackupManager initialization failed: {e}")
            raise

    def save_backup_metadata(self):
        try:
            dir_mod = DirectoryModel(
                name=self.source_dir.name,
                path=str(self.source_dir.path),
                size=self.source_dir.size,
                date=self.source_dir.date,
            )
            self.session.add(dir_mod)
            self.session.flush()

            backup_mod = BackupModel(
                directory_id=dir_mod.id,
                backup_name=self.backup_archive.backup_name,
                backup_path=str(self.backup_archive.backup_path),
                backup_size=self.backup_archive.compressed_size,
                backup_date=self.backup_archive.backup_date,
                compressed=self.backup_archive.compressed,
                compression_type=(
                    self.backup_archive.compression_type.value
                    if self.backup_archive.compressed
                    else None
                ),
                compressed_size=self.backup_archive.compressed_size,
            )
            self.session.add(backup_mod)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logging.error(f"Failed to save backup metadata: {e}")
            raise

    def close(self):
        try:
            self.session.close()
        except Exception as e:
            logging.error(f"Failed to close session: {e}")

    def __repr__(self) -> str:
        return (
            f"SourceDirectory: '{self.source_dir.name}'\n"
            f"Path: {self.source_dir.path}\n"
            f"Backed up to {self.backup_archive.backup_path}."
        )

    def __str__(self):
        return self.__repr__()
