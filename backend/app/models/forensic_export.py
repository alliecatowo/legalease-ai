"""Forensic Export model for digital discovery."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class ForensicExport(Base):
    """
    ForensicExport model representing a forensic discovery export (e.g., Cellebrite AXIOM).

    A forensic export is a folder structure containing:
    - ExportSummary.json (metadata about the export)
    - Report.html (entry point for the interactive HTML report)
    - Attachments/ (binary and text files)
    - Resources/ (site assets and data pages)
    - Chat preview report/ (HTML pages with attachments)

    This model stores metadata about the export without copying the files,
    just referencing the folder path on disk.
    """

    __tablename__ = "forensic_exports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Folder reference
    folder_path = Column(String(1024), nullable=False, unique=True)
    folder_name = Column(String(512), nullable=True)

    # Parsed from ExportSummary.json - root level
    export_uuid = Column(String(36), index=True, nullable=True)

    # Parsed from summary array
    axiom_version = Column(String(50), nullable=True)
    total_records = Column(Integer, nullable=True)
    exported_records = Column(Integer, nullable=True)
    num_attachments = Column(Integer, nullable=True)
    export_start_date = Column(DateTime, nullable=True)
    export_end_date = Column(DateTime, nullable=True)
    export_duration = Column(String(50), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    export_status = Column(String(50), nullable=True)
    case_directory = Column(String(512), nullable=True)
    case_storage_location = Column(String(256), nullable=True)

    # Store full JSON for flexibility
    summary_json = Column(JSONB, nullable=True)
    export_options_json = Column(JSONB, nullable=True)
    problems_json = Column(JSONB, nullable=True)

    # Metadata
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_verified_at = Column(DateTime, nullable=True)

    # Relationships
    case = relationship("Case", back_populates="forensic_exports")

    def __repr__(self) -> str:
        return (
            f"<ForensicExport(id={self.id}, "
            f"folder_name='{self.folder_name}', "
            f"case_id={self.case_id}, "
            f"records={self.total_records})>"
        )
