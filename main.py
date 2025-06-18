import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import re
import tarfile
import zipfile
import shutil
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    create_engine,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# إعداد اللوجينج
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# ----------------------------------------------------------------------
# أنواع الضغط كـ Enum
# ----------------------------------------------------------------------
class CompressionType(Enum):
    TAR = "tar"
    TAR_GZ = "tar.gz"
    ZIP = "zip"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


# ----------------------------------------------------------------------
# كلاس يمثل مجلد المصدر
# ----------------------------------------------------------------------
@dataclass
class SourceDirectory:
    path: Path
    name: str = field(init=False)
    size: Optional[int] = field(init=False, default=None)
    date: datetime = field(init=False)
    calculate_size: bool = True

    def __post_init__(self):
        if not self.path.exists() or not self.path.is_dir():
            logging.error(f"Directory: '{self.path}' is not a valid directory.")
            raise ValueError(f"Directory: '{self.path}' is not a valid directory.")
        self.name = self._make_safe_name(self.path.name)
        try:now
            self.date = datetime.fromtimestamp(self.path.stat().st_mtime)
        except Exception as e:
            logging.error(f"Could not get modification date: {e}")
            self.date = datetime.now()
        self.size = self._get_size() if self.calculate_size else None

    @staticmethod
    def _make_safe_name(name: str) -> str:
        name = name.replace(" ", "_")
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def _get_size(self) -> int:
        try:
            return sum(
                f.stat().st_size for file in self.path.rglob("*") if file.is_file()
            )
        except Exception as e:
            logging.error(f"Error calculating directory size: {e}")
            return 0

    def __repr__(self) -> str:
        size_str = f"{(self.size // 1024)} Kb" if self.size is not None else "Unknown"
        return (
            f"SourceDirectory: '{self.name}'\n"
            f"Path: {self.path}\n"
            f"Size: {size_str}\n"
            f"Last Modified: {self.date.strftime('%Y-%m-%d %H:%M')}"
        )

    def __str__(self):
        return self.__repr__()


# ----------------------------------------------------------------------
# كلاس يمثل أرشيف النسخة الاحتياطية
# ----------------------------------------------------------------------
@dataclass
class BackupArchive:
    source: SourceDirectory
    compressed: bool
    backup_path: Path = field(default_factory=lambda: Path.home() / ".backups")
    backup_name: Optional[str] = None
    backup_date: datetime = field(default_factory=datetime.now)
    compression_type: CompressionType = CompressionType.ZIP
    compressed_size: Optional[int] = field(init=False, default=None)
    backup_file: Optional[Path] = field(init=False, default=None)

    def __post_init__(self):
        if self.compressed and not CompressionType.has_value(
            self.compression_type.value
        ):
            raise ValueError(
                f"Unsupported compression type: {self.compression_type.value}. "
                f"Supported: {[c.value for c in CompressionType]}"
            )
        try:
            self.backup_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create backup path: {e}")
            raise
        self.backup_name = self._make_backup_name()
        self.backup_file = self._get_backup_file_path()

        if self.compressed:
            try:
                self._compress()
                self.compressed_size = (
                    self.backup_file.stat().st_size
                    if self.backup_file.exists()
                    else None
                )
            except Exception as e:
                logging.error(f"Compression failed: {e}")
                self.compressed_size = None
        else:
            try:
                self._move()
                self.compressed_size = None
            except Exception as e:
                logging.error(f"Move failed: {e}")
                self.compressed_size = None

    def _make_backup_name(self) -> str:
        base_name = self.backup_name or self.source.name
        safe_name = SourceDirectory._make_safe_name(base_name)
        return f"{safe_name}-{self.backup_date.strftime('%Y-%m-%d-%H%M%S')}"

    def _get_backup_file_path(self) -> Path:
        ext = self.compression_type.value if self.compressed else ""
        return (
            self.backup_path / f"{self.backup_name}.{ext}"
            if ext
            else self.backup_path / self.backup_name
        )

    def _compress(self):
        if self.compression_type == CompressionType.TAR:
            with tarfile.open(str(self.backup_file), "w") as tar:
                tar.add(str(self.source.path), arcname=self.source.name)
        elif self.compression_type == CompressionType.TAR_GZ:
            with tarfile.open(str(self.backup_file), "w:gz") as tar:
                tar.add(str(self.source.path), arcname=self.source.name)
        elif self.compression_type == CompressionType.ZIP:
            with zipfile.ZipFile(
                str(self.backup_file), "w", zipfile.ZIP_DEFLATED
            ) as zipf:
                for file in self.source.path.rglob("*"):
                    arcname = str(
                        Path(self.source.name) / file.relative_to(self.source.path)
                    )
                    zipf.write(str(file), arcname=arcname)
        else:
            raise ValueError(f"Unknown compression type: {self.compression_type.value}")

    def _move(self):
        dest = self.backup_path / self.source.name
        if dest.exists():
            logging.warning(f"Destination '{dest}' already exists. Skipping move.")
        else:
            shutil.copytree(self.source.path, dest)

    def __repr__(self) -> str:
        size_str = (
            f"{(self.compressed_size // 1024)} Kb"
            if self.compressed_size is not None
            else "Unknown"
        )
        backup_file_str = self.backup_file if self.backup_file else "N/A"
        return (
            f"BackupArchive for: '{self.source.name}'\n"
            f"Backup Name: '{self.backup_name}.{self.compression_type.value if self.compressed else ''}'\n"
            f"Backup Path: {self.backup_path}\n"
            f"Backup File: {backup_file_str}\n"
            f"Compressed: {'Yes' if self.compressed else 'No'}\n"
            f"Size: {size_str}\n"
            f"Backup Date: {self.backup_date.strftime('%Y-%m-%d %H:%M')}"
        )

    def __str__(self):
        return self.__repr__()


# ----------------------------------------------------------------------
# قاعدة بيانات ORM
# ----------------------------------------------------------------------
Base = declarative_base()


class DatabaseManager:
    def __init__(self):
        try:
            self.engine = create_engine("sqlite:///backups.db")
            self.Session = sessionmaker(bind=self.engine)
            self.session = self.Session()
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            raise

    def create_db(self):
        try:
            Base.metadata.create_all(self.engine)
        except Exception as e:
            logging.error(f"Failed to create tables: {e}")
            raise

    def get_session(self):
        return self.session


class DirectoryModel(Base):
    __tablename__ = "directories"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    size = Column(Integer)
    date = Column(DateTime)
    backups = relationship("BackupModel", back_populates="directory")


class BackupModel(Base):
    __tablename__ = "backups"
    id = Column(Integer, primary_key=True)
    directory_id = Column(Integer, ForeignKey("directories.id"))
    backup_name = Column(String)
    backup_path = Column(String)
    backup_size = Column(Integer)
    backup_date = Column(DateTime)
    compressed = Column(Boolean)
    compression_type = Column(String, nullable=True)
    compressed_size = Column(Integer, nullable=True)
    directory = relationship("DirectoryModel", back_populates="backups")


# ----------------------------------------------------------------------
# مدير النسخ الاحتياطي
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
def main():
    try:
        db = DatabaseManager()
        db.create_db()
        docs_path = Path.home() / "Desktop/DataSafe"
        backup_mgr = BackupManager(
            docs_path,
            calculate_size=True,
            compressed=True,
            compression_type=CompressionType.ZIP,  # TAR, TAR_GZ, ZIP
        )
        backup_mgr.save_backup_metadata()
        print(backup_mgr.backup_archive)
        backup_mgr.close()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")


if __name__ == "__main__":
    main()
