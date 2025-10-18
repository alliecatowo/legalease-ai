"""Service for managing forensic discovery exports."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.forensic_export import ForensicExport
from app.models.case import Case

logger = logging.getLogger(__name__)


class ForensicExportService:
    """Service for discovering, registering, and managing forensic exports."""

    MAX_SCAN_DEPTH = 10  # Safety limit for directory recursion

    @staticmethod
    def is_forensic_export(path: Path) -> bool:
        """
        Check if a folder is a forensic export.

        A folder is considered a forensic export if it contains both:
        - ExportSummary.json
        - Report.html
        """
        return (
            (path / "ExportSummary.json").exists() and
            (path / "Report.html").exists()
        )

    @staticmethod
    def scan_for_exports(
        root_path: str,
        case_gid: str,
        db: Session
    ) -> Dict[str, List]:
        """
        Recursively scan a directory for forensic exports.

        Stops recursion when an export folder is found (critical for performance).

        Args:
            root_path: Root directory to start scanning from
            case_gid: GID of the case to associate exports with
            db: Database session

        Returns:
            Dictionary with keys: 'found', 'existing', 'errors'
        """
        results = {
            "found": [],
            "existing": [],
            "errors": []
        }

        def scan_recursive(current_path: Path, depth: int = 0):
            """Recursively scan directory, stopping at export folders."""
            if depth > ForensicExportService.MAX_SCAN_DEPTH:
                logger.warning(f"Max depth reached at {current_path}")
                return

            if not current_path.is_dir():
                return

            # Check if THIS folder is an export
            if ForensicExportService.is_forensic_export(current_path):
                logger.info(f"Found forensic export at {current_path}")

                # Check if already registered
                existing = db.query(ForensicExport).filter(
                    ForensicExport.folder_path == str(current_path.absolute())
                ).first()

                if existing:
                    results["existing"].append(str(current_path.absolute()))
                    logger.info(f"Export already registered: {current_path}")
                else:
                    # Register new export
                    try:
                        export = ForensicExportService.register_export(
                            current_path, case_gid, db
                        )
                        results["found"].append({
                            "gid": export.gid,
                            "path": str(current_path.absolute()),
                            "name": export.folder_name
                        })
                        logger.info(f"Registered new export: {export.folder_name}")
                    except Exception as e:
                        logger.error(f"Failed to register export at {current_path}: {e}")
                        results["errors"].append({
                            "path": str(current_path.absolute()),
                            "error": str(e)
                        })

                # CRITICAL: Don't recurse into export folders
                return

            # Not an export, continue scanning subdirectories
            try:
                for item in current_path.iterdir():
                    if item.is_dir():
                        scan_recursive(item, depth + 1)
            except PermissionError as e:
                logger.warning(f"Permission denied: {current_path}")
                results["errors"].append({
                    "path": str(current_path.absolute()),
                    "error": f"Permission denied: {e}"
                })
            except Exception as e:
                logger.error(f"Error scanning {current_path}: {e}")
                results["errors"].append({
                    "path": str(current_path.absolute()),
                    "error": str(e)
                })

        try:
            root = Path(root_path)
            if not root.exists():
                raise ValueError(f"Path does not exist: {root_path}")
            if not root.is_dir():
                raise ValueError(f"Path is not a directory: {root_path}")

            scan_recursive(root)
        except Exception as e:
            logger.error(f"Failed to start scan at {root_path}: {e}")
            results["errors"].append({
                "path": root_path,
                "error": f"Failed to start scan: {e}"
            })

        return results

    @staticmethod
    def register_export(
        export_path: Path,
        case_gid: str,
        db: Session
    ) -> ForensicExport:
        """
        Parse ExportSummary.json and create ForensicExport record.

        Args:
            export_path: Path to the export folder
            case_gid: GID of the case to associate with
            db: Database session

        Returns:
            Created ForensicExport instance

        Raises:
            ValueError: If ExportSummary.json is missing or invalid
        """
        summary_file = export_path / "ExportSummary.json"
        if not summary_file.exists():
            raise ValueError(f"ExportSummary.json not found in {export_path}")

        # Read and parse JSON
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in ExportSummary.json: {e}")
        except Exception as e:
            raise ValueError(f"Failed to read ExportSummary.json: {e}")

        # Extract fields from summary array (they're name/value pairs)
        summary_dict = {
            item["name"]: item["value"]
            for item in summary_data.get("summary", [])
        }

        # Helper functions for parsing
        def parse_cellebrite_date(date_str: Optional[str]) -> Optional[datetime]:
            """Parse dates like '7/17/2025 9:48:42 AM'."""
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, "%m/%d/%Y %I:%M:%S %p")
            except Exception as e:
                logger.warning(f"Failed to parse date '{date_str}': {e}")
                return None

        def parse_size(size_str: Optional[str]) -> Optional[int]:
            """Parse size strings with commas like '50,223,053,681'."""
            if not size_str:
                return None
            try:
                return int(size_str.replace(",", ""))
            except Exception as e:
                logger.warning(f"Failed to parse size '{size_str}': {e}")
                return None

        def parse_count(count_str: Optional[str]) -> Optional[int]:
            """Parse count strings with commas like '1,101,071'."""
            if not count_str:
                return None
            try:
                return int(count_str.replace(",", ""))
            except Exception as e:
                logger.warning(f"Failed to parse count '{count_str}': {e}")
                return None

        # Get case by GID to get the case_id
        case = db.query(Case).filter(Case.gid == case_gid).first()
        if not case:
            raise ValueError(f"Case with GID {case_gid} not found")

        # Create export record
        export = ForensicExport(
            case_id=case.id,
            folder_path=str(export_path.absolute()),
            folder_name=export_path.name,

            # From root level
            export_uuid=summary_data.get("id"),

            # From summary array
            axiom_version=summary_dict.get("AXIOM version"),
            total_records=parse_count(summary_dict.get("Total number of records")),
            exported_records=parse_count(summary_dict.get("Number of records in export")),
            num_attachments=parse_count(summary_dict.get("Number of attachments in export")),
            export_start_date=parse_cellebrite_date(summary_dict.get("Start date")),
            export_end_date=parse_cellebrite_date(summary_dict.get("End date")),
            export_duration=summary_dict.get("Duration"),
            size_bytes=parse_size(summary_dict.get("Size (bytes)")),
            export_status=summary_dict.get("Status"),
            case_directory=summary_dict.get("Case directory"),
            case_storage_location=summary_dict.get("Case storage location"),

            # Store full JSON
            summary_json=summary_data.get("summary"),
            export_options_json=summary_data.get("options"),
            problems_json=summary_data.get("problems"),

            # Metadata
            discovered_at=datetime.utcnow(),
            last_verified_at=datetime.utcnow()
        )

        db.add(export)
        db.commit()
        db.refresh(export)

        logger.info(f"Created ForensicExport(gid={export.gid}, name='{export.folder_name}')")
        return export

    @staticmethod
    def get_export(export_gid: str, db: Session) -> Optional[ForensicExport]:
        """Get a forensic export by GID."""
        return db.query(ForensicExport).filter(
            ForensicExport.gid == export_gid
        ).first()

    @staticmethod
    def list_exports_for_case(case_gid: str, db: Session) -> List[ForensicExport]:
        """List all forensic exports for a case."""
        case = db.query(Case).filter(Case.gid == case_gid).first()
        if not case:
            return []
        return db.query(ForensicExport).filter(
            ForensicExport.case_id == case.id
        ).order_by(ForensicExport.discovered_at.desc()).all()

    @staticmethod
    def list_all_exports(db: Session) -> List[ForensicExport]:
        """List all forensic exports across all cases."""
        return db.query(ForensicExport).order_by(
            ForensicExport.discovered_at.desc()
        ).all()

    @staticmethod
    def verify_export_exists(export_gid: str, db: Session) -> Tuple[bool, str]:
        """
        Verify that the export folder still exists on disk.

        Returns:
            Tuple of (exists: bool, path: str)
        """
        export = ForensicExportService.get_export(export_gid, db)
        if not export:
            raise ValueError(f"Export with GID {export_gid} not found")

        exists = Path(export.folder_path).exists()
        export.last_verified_at = datetime.utcnow()
        db.commit()

        return exists, export.folder_path

    @staticmethod
    def delete_export(export_gid: str, db: Session) -> ForensicExport:
        """
        Delete a forensic export record from the database.

        Note: This does NOT delete files from disk, only the database record.
        """
        export = ForensicExportService.get_export(export_gid, db)
        if not export:
            raise ValueError(f"Export with GID {export_gid} not found")

        db.delete(export)
        db.commit()

        logger.info(f"Deleted ForensicExport(gid={export_gid})")
        return export
