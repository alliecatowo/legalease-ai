"""Import batch model for tracking bulk discovery item imports."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base


class ImportStatus(str, PyEnum):
    """Import batch status enumeration."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImportBatch(Base):
    """
    ImportBatch model for tracking bulk imports of discovery items.

    This model tracks the progress and status of bulk imports from various
    sources (e.g., Cellebrite exports, prosecutor discovery packages).
    Helps monitor import progress and troubleshoot issues.
    """

    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_type = Column(String(100), nullable=False, index=True)  # cellebrite, prosecutor_package, evidence_bundle, etc.
    total_items = Column(Integer, nullable=False, default=0)  # Total number of items to import
    processed_items = Column(Integer, nullable=False, default=0)  # Number of items processed so far
    status = Column(
        Enum(ImportStatus, native_enum=True, create_constraint=True),
        nullable=False,
        default=ImportStatus.PENDING,
        index=True
    )
    import_path = Column(String(1024), nullable=False)  # Path to source data
    error_log = Column(Text, nullable=True)  # Error messages and logs
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)  # When import finished (success or failure)

    # Relationships
    case = relationship("Case", back_populates="import_batches")

    def __repr__(self) -> str:
        return f"<ImportBatch(id={self.id}, case_id={self.case_id}, status='{self.status.value}', progress={self.processed_items}/{self.total_items})>"
