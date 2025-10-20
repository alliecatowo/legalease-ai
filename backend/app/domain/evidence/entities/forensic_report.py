"""
ForensicReport entity for the Evidence domain.

Represents forensic examination reports from tools like Cellebrite AXIOM,
including device information, extraction metadata, and findings.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID


class ReportType(str, Enum):
    """Type of forensic report."""

    MOBILE_DEVICE = "MOBILE_DEVICE"
    COMPUTER = "COMPUTER"
    CLOUD_EXTRACTION = "CLOUD_EXTRACTION"
    NETWORK_CAPTURE = "NETWORK_CAPTURE"
    MEMORY_DUMP = "MEMORY_DUMP"
    DISK_IMAGE = "DISK_IMAGE"
    OTHER = "OTHER"


class ExtractionStatus(str, Enum):
    """Status of the forensic extraction."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DeviceInfo:
    """
    Immutable device information.

    Attributes:
        device_id: Unique device identifier
        make: Device manufacturer (e.g., 'Apple', 'Samsung')
        model: Device model (e.g., 'iPhone 13', 'Galaxy S21')
        os_version: Operating system version
        serial_number: Device serial number
        imei: International Mobile Equipment Identity (for mobile devices)
        metadata: Additional device-specific metadata
    """

    device_id: str
    make: Optional[str] = None
    model: Optional[str] = None
    os_version: Optional[str] = None
    serial_number: Optional[str] = None
    imei: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    """
    Immutable finding from forensic examination.

    Attributes:
        category: Category of finding (e.g., 'DELETED_FILE', 'ENCRYPTED_DATA')
        description: Description of the finding
        severity: Severity level (e.g., 'HIGH', 'MEDIUM', 'LOW')
        location: Location where finding was discovered
        timestamp: When the finding was created/modified (in device time)
        metadata: Additional finding-specific metadata
    """

    category: str
    description: str
    severity: Optional[str] = None
    location: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ForensicReport:
    """
    ForensicReport entity representing a forensic examination report.

    Represents the complete output from forensic tools like Cellebrite AXIOM,
    including device information, extraction metadata, and examination findings.

    Attributes:
        id: Unique identifier for the report
        case_id: ID of the case this report belongs to
        report_type: Type of forensic report
        examiner: Name/ID of the forensic examiner
        findings: List of examination findings
        metadata: Report-level metadata (tool version, parameters, etc.)
        export_path: Path to the export folder/archive
        device_info: Information about the examined device
        extraction_start: When extraction started
        extraction_end: When extraction completed
        status: Current status of the extraction
        created_at: When this report record was created
        updated_at: When this report record was last modified
        total_items: Total number of items in the report
        extracted_items: Number of successfully extracted items

    Example:
        >>> report = ForensicReport(
        ...     id=UUID('...'),
        ...     case_id=UUID('...'),
        ...     report_type=ReportType.MOBILE_DEVICE,
        ...     examiner="Detective Smith",
        ...     findings=[
        ...         Finding(
        ...             category="DELETED_MESSAGES",
        ...             description="Recovered 127 deleted text messages",
        ...             severity="HIGH",
        ...         ),
        ...     ],
        ...     metadata={"tool": "Cellebrite AXIOM", "version": "7.0"},
        ...     export_path="/exports/case_001/device_001",
        ...     device_info=DeviceInfo(
        ...         device_id="device_001",
        ...         make="Apple",
        ...         model="iPhone 13",
        ...         os_version="iOS 16.2",
        ...     ),
        ...     status=ExtractionStatus.COMPLETED,
        ... )
        >>> report.has_findings()
        True
        >>> report.get_high_severity_findings()
        [Finding(...)]
    """

    id: UUID
    case_id: UUID
    report_type: ReportType
    examiner: str
    findings: List[Finding]
    metadata: Dict[str, Any]
    export_path: str
    created_at: datetime
    device_info: Optional[DeviceInfo] = None
    extraction_start: Optional[datetime] = None
    extraction_end: Optional[datetime] = None
    status: ExtractionStatus = ExtractionStatus.PENDING
    updated_at: Optional[datetime] = None
    total_items: Optional[int] = None
    extracted_items: Optional[int] = None

    def has_findings(self) -> bool:
        """Check if report has any findings."""
        return len(self.findings) > 0

    def get_findings_by_category(self, category: str) -> List[Finding]:
        """
        Get all findings in a specific category.

        Args:
            category: Category to filter by

        Returns:
            List of findings in the specified category
        """
        return [f for f in self.findings if f.category == category]

    def get_high_severity_findings(self) -> List[Finding]:
        """Get all high-severity findings."""
        return [f for f in self.findings if f.severity == "HIGH"]

    def mark_in_progress(self) -> None:
        """Mark extraction as in progress."""
        self.status = ExtractionStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()
        if not self.extraction_start:
            self.extraction_start = datetime.utcnow()

    def mark_completed(self) -> None:
        """Mark extraction as completed."""
        self.status = ExtractionStatus.COMPLETED
        self.updated_at = datetime.utcnow()
        if not self.extraction_end:
            self.extraction_end = datetime.utcnow()

    def mark_partial(self, reason: str) -> None:
        """
        Mark extraction as partially completed.

        Args:
            reason: Reason for partial completion
        """
        self.status = ExtractionStatus.PARTIAL
        self.updated_at = datetime.utcnow()
        self.metadata["partial_reason"] = reason
        if not self.extraction_end:
            self.extraction_end = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        """
        Mark extraction as failed.

        Args:
            error: Error message describing the failure
        """
        self.status = ExtractionStatus.FAILED
        self.updated_at = datetime.utcnow()
        self.metadata["error"] = error
        self.metadata["failed_at"] = datetime.utcnow().isoformat()

    def add_finding(self, finding: Finding) -> None:
        """
        Add a new finding to the report.

        Args:
            finding: Finding to add
        """
        self.findings.append(finding)
        self.updated_at = datetime.utcnow()

    def get_extraction_duration(self) -> Optional[float]:
        """
        Get extraction duration in seconds.

        Returns:
            Duration in seconds, or None if not completed
        """
        if self.extraction_start and self.extraction_end:
            return (self.extraction_end - self.extraction_start).total_seconds()
        return None

    def __eq__(self, other: object) -> bool:
        """Reports are equal if they have the same ID."""
        if not isinstance(other, ForensicReport):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on report ID."""
        return hash(self.id)
