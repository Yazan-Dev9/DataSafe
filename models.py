from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


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


class DatabaseManager:
    def __init__(self):
        self.engine = create_engine("sqlite:///backups.db")
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def create_db(self):
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return self.session
