from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import re
import tarfile
import zipfile
import shutil
from enum import Enum
import logging


class CompressionType(Enum):
    TAR = "tar"
    TAR_GZ = "tar.gz"
    ZIP = "zip"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


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
        try:
            self.date = datetime.fromtimestamp(self.path.stat().st_mtime)
        except Exception as e:
            logging.error(f"Could not get modification date: {e}")
            self.date = datetime.now().replace(microsecond=0)
        self.size = self._get_size() if self.calculate_size else None

    @staticmethod
    def _make_safe_name(name: str) -> str:
        name = name.replace(" ", "_")
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def _get_size(self) -> int:
        try:
            return sum(f.stat().st_size for f in self.path.rglob("*") if f.is_file())
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
                f"Unsupported compression type: {self.compression_type.value}."
                f"Supported: {[c.value for c in CompressionType]}"
            )
        try:
            self.backup_path.mkdir(parents=True, exist_ok=True)
            logging.debug(f"Created backup path: {self.backup_path}")
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
        if self.backup_name is None:
            raise ValueError("backup_name cannot be None")
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
                logging.debug(f"Added {self.source.path} to archive")
        elif self.compression_type == CompressionType.TAR_GZ:
            with tarfile.open(str(self.backup_file), "w:gz") as tar:
                tar.add(str(self.source.path), arcname=self.source.name)
                logging.debug(f"Added {self.source.path} to archive")
        elif self.compression_type == CompressionType.ZIP:
            with zipfile.ZipFile(
                str(self.backup_file), "w", zipfile.ZIP_DEFLATED
            ) as zipf:
                for file in self.source.path.rglob("*"):
                    arcname = str(
                        Path(self.source.name) / file.relative_to(self.source.path)
                    )
                    zipf.write(str(file), arcname=arcname)
                    logging.debug(f"Added {file} to archive")
        else:
            raise ValueError(f"Unknown compression type: {self.compression_type.value}")

    def _move(self):
        dest = self.backup_path / self.source.name
        logging.debug(f"Moving {self.source.path} to {dest}")
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
