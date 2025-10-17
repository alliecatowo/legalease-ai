"""Forensic Export API endpoints."""

from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.schemas.forensic_export import (
    ForensicExportResponse,
    ForensicExportListItem,
    ForensicExportListResponse,
    ScanLocationRequest,
    ScanLocationResponse,
    VerifyExportResponse,
    DeleteForensicExportResponse,
)
from app.services.forensic_export_service import ForensicExportService

router = APIRouter()


@router.get(
    "/cases/{case_id}/forensic-exports",
    response_model=ForensicExportListResponse,
    summary="List forensic exports for a case",
    description="Get all forensic exports associated with a specific case",
)
async def list_exports_for_case(
    case_id: int,
    db: Session = Depends(get_db),
):
    """
    List all forensic exports for a specific case.

    Args:
        case_id: Case ID
        db: Database session

    Returns:
        List of forensic exports for the case
    """
    exports = ForensicExportService.list_exports_for_case(case_id, db)
    return ForensicExportListResponse(
        exports=exports,
        total=len(exports)
    )


@router.get(
    "/forensic-exports",
    response_model=ForensicExportListResponse,
    summary="List all forensic exports",
    description="Get all forensic exports across all cases",
)
async def list_all_exports(
    db: Session = Depends(get_db),
):
    """
    List all forensic exports across all cases.

    Args:
        db: Database session

    Returns:
        List of all forensic exports
    """
    exports = ForensicExportService.list_all_exports(db)
    return ForensicExportListResponse(
        exports=exports,
        total=len(exports)
    )


@router.get(
    "/forensic-exports/{export_id}",
    response_model=ForensicExportResponse,
    summary="Get forensic export details",
    description="Get detailed information about a specific forensic export including full JSON data",
)
async def get_export(
    export_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a forensic export.

    Args:
        export_id: Export ID
        db: Database session

    Returns:
        Detailed export information including summary, options, and problems JSON

    Raises:
        HTTPException: If export not found
    """
    export = ForensicExportService.get_export(export_id, db)
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forensic export {export_id} not found"
        )

    return export


@router.post(
    "/cases/{case_id}/forensic-exports/scan",
    response_model=ScanLocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan location for forensic exports",
    description="Recursively scan a directory for forensic export folders and register them",
)
async def scan_location(
    case_id: int,
    request: ScanLocationRequest,
    db: Session = Depends(get_db),
):
    """
    Scan a directory for forensic exports.

    Recursively scans the provided path looking for folders containing both
    ExportSummary.json and Report.html. When found, registers the export and
    stops recursing into that folder (critical for performance).

    Args:
        case_id: ID of the case to associate exports with
        request: Scan request with path to scan
        db: Database session

    Returns:
        Scan results including newly found exports, existing exports, and errors

    Raises:
        HTTPException: If case not found or path is invalid
    """
    # Validate case exists
    from app.models.case import Case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )

    # Perform scan
    try:
        results = ForensicExportService.scan_for_exports(
            request.path,
            case_id,
            db
        )

        return ScanLocationResponse(
            scanned_path=request.path,
            case_id=case_id,
            found=results["found"],
            existing=results["existing"],
            errors=results["errors"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan location: {str(e)}"
        )


@router.post(
    "/forensic-exports/{export_id}/verify",
    response_model=VerifyExportResponse,
    summary="Verify export exists",
    description="Verify that the export folder still exists on disk",
)
async def verify_export(
    export_id: int,
    db: Session = Depends(get_db),
):
    """
    Verify that the export folder still exists on disk.

    Updates the last_verified_at timestamp.

    Args:
        export_id: Export ID
        db: Database session

    Returns:
        Verification result with exists flag and path

    Raises:
        HTTPException: If export not found
    """
    try:
        exists, path = ForensicExportService.verify_export_exists(export_id, db)
        return VerifyExportResponse(
            exists=exists,
            path=path,
            verified_at=datetime.utcnow()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/forensic-exports/{export_id}",
    response_model=DeleteForensicExportResponse,
    summary="Delete forensic export record",
    description="Delete the export record from database (files remain on disk)",
)
async def delete_export(
    export_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a forensic export record from the database.

    NOTE: This does NOT delete files from disk, only the database record.
    The export folder and all its contents remain on the filesystem.

    Args:
        export_id: Export ID
        db: Database session

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If export not found
    """
    try:
        export = ForensicExportService.delete_export(export_id, db)
        return DeleteForensicExportResponse(
            id=export.id,
            folder_path=export.folder_path,
            message=f"Export record deleted (files remain at {export.folder_path})"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/forensic-exports/{export_id}/report",
    response_class=HTMLResponse,
    summary="Get Report.html",
    description="Serve the Report.html file from the forensic export",
)
async def get_export_report(
    export_id: int,
    db: Session = Depends(get_db),
):
    """
    Serve the Report.html file from the forensic export.

    Args:
        export_id: Export ID
        db: Database session

    Returns:
        HTML content of the Report.html file

    Raises:
        HTTPException: If export not found or Report.html doesn't exist
    """
    export = ForensicExportService.get_export(export_id, db)
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forensic export {export_id} not found"
        )

    report_path = Path(export.folder_path) / "Report.html"

    if not report_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report.html not found in export folder"
        )

    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read Report.html: {str(e)}"
        )


@router.get(
    "/forensic-exports/{export_id}/files",
    response_model=Dict[str, Any],
    summary="List files in export",
    description="List files and directories in the forensic export folder",
)
async def list_export_files(
    export_id: int,
    subpath: str = "",
    db: Session = Depends(get_db),
):
    """
    List files and directories in the forensic export folder.

    Args:
        export_id: Export ID
        subpath: Optional subdirectory path (relative to export root)
        db: Database session

    Returns:
        Dictionary with files and directories lists

    Raises:
        HTTPException: If export not found or path is invalid
    """
    export = ForensicExportService.get_export(export_id, db)
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forensic export {export_id} not found"
        )

    export_path = Path(export.folder_path)
    target_path = export_path / subpath if subpath else export_path

    # Security: Ensure target_path is within export_path
    try:
        target_path = target_path.resolve()
        export_path = export_path.resolve()
        if not str(target_path).startswith(str(export_path)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path: cannot access files outside export folder"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path"
        )

    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path not found: {subpath}"
        )

    if not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a directory"
        )

    try:
        items = []
        for item in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "path": str(item.relative_to(export_path)),
                    "is_directory": item.is_dir(),
                    "size": stat.st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception:
                # Skip items we can't access
                continue

        return {
            "export_id": export_id,
            "current_path": str(target_path.relative_to(export_path)) if subpath else "",
            "parent_path": str(target_path.parent.relative_to(export_path)) if target_path != export_path else None,
            "items": items,
            "total": len(items),
        }
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to access this path"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )
