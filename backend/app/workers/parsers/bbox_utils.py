"""
Bounding Box Normalization Utilities

Utilities for converting between different bbox formats used by various PDF parsers:
- Marker: polygon format [[x1,y1], [x2,y2], ...]
- Docling: {"l": left, "t": top, "r": right, "b": bottom}
- PyMuPDF: {"x0": left, "y0": top, "x1": right, "y1": bottom}

All formats are normalized to a standard format for consistent processing and frontend rendering.
"""

import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


# Standard bbox format returned by all normalization functions
BBoxDict = Dict[str, Union[int, float, str]]


def normalize_bbox(
    bbox: Dict[str, Any],
    page_num: int,
    source: str = "auto",
    text: Optional[str] = None,
    bbox_type: Optional[str] = None,
) -> BBoxDict:
    """
    Convert any bbox format to standard normalized format.

    Args:
        bbox: Bounding box in any supported format
        page_num: Page number (1-indexed)
        source: Source format ("auto", "marker", "docling", "pymupdf", "polygon")
        text: Optional text content for this bbox
        bbox_type: Optional type/category (e.g., "Text", "Table", "Figure")

    Returns:
        Normalized bbox dictionary with keys:
        - page: Page number (int)
        - left: Left x-coordinate (float)
        - top: Top y-coordinate (float)
        - right: Right x-coordinate (float)
        - bottom: Bottom y-coordinate (float)
        - text: Text content (str)
        - type: Bbox type/category (str)

    Raises:
        ValueError: If bbox format cannot be determined or is invalid

    Examples:
        >>> # Marker polygon format
        >>> marker_bbox = {"polygon": [[10, 20], [100, 20], [100, 50], [10, 50]]}
        >>> normalize_bbox(marker_bbox, page_num=1, source="marker")
        {'page': 1, 'left': 10.0, 'top': 20.0, 'right': 100.0, 'bottom': 50.0, ...}

        >>> # Docling format
        >>> docling_bbox = {"l": 10, "t": 20, "r": 100, "b": 50}
        >>> normalize_bbox(docling_bbox, page_num=1, source="docling")
        {'page': 1, 'left': 10.0, 'top': 20.0, 'right': 100.0, 'bottom': 50.0, ...}

        >>> # PyMuPDF format
        >>> pymupdf_bbox = {"x0": 10, "y0": 20, "x1": 100, "y1": 50}
        >>> normalize_bbox(pymupdf_bbox, page_num=1, source="pymupdf")
        {'page': 1, 'left': 10.0, 'top': 20.0, 'right': 100.0, 'bottom': 50.0, ...}
    """
    # Auto-detect source format if needed
    if source == "auto":
        source = _detect_bbox_format(bbox)
        logger.debug(f"Auto-detected bbox format: {source}")

    # Convert based on source format
    if source == "marker" or source == "polygon":
        # Marker can have polygon directly or nested
        polygon = bbox.get("polygon") or bbox
        if not isinstance(polygon, list):
            raise ValueError(f"Expected polygon list, got {type(polygon)}")
        normalized = polygon_to_bbox(polygon)

    elif source == "docling":
        # Docling format: {"l": left, "t": top, "r": right, "b": bottom}
        if not all(k in bbox for k in ["l", "t", "r", "b"]):
            raise ValueError(f"Docling format requires keys: l, t, r, b. Got: {bbox.keys()}")
        normalized = {
            "left": float(bbox["l"]),
            "top": float(bbox["t"]),
            "right": float(bbox["r"]),
            "bottom": float(bbox["b"]),
        }

    elif source == "pymupdf":
        # PyMuPDF format: {"x0": left, "y0": top, "x1": right, "y1": bottom}
        if not all(k in bbox for k in ["x0", "y0", "x1", "y1"]):
            raise ValueError(f"PyMuPDF format requires keys: x0, y0, x1, y1. Got: {bbox.keys()}")
        normalized = {
            "left": float(bbox["x0"]),
            "top": float(bbox["y0"]),
            "right": float(bbox["x1"]),
            "bottom": float(bbox["y1"]),
        }

    elif source == "standard":
        # Already in standard format
        if not all(k in bbox for k in ["left", "top", "right", "bottom"]):
            raise ValueError(f"Standard format requires keys: left, top, right, bottom. Got: {bbox.keys()}")
        normalized = {
            "left": float(bbox["left"]),
            "top": float(bbox["top"]),
            "right": float(bbox["right"]),
            "bottom": float(bbox["bottom"]),
        }

    else:
        raise ValueError(f"Unknown bbox source format: {source}")

    # Validate coordinates
    if normalized["left"] > normalized["right"]:
        logger.warning(f"Invalid bbox: left > right ({normalized['left']} > {normalized['right']})")
    if normalized["top"] > normalized["bottom"]:
        logger.warning(f"Invalid bbox: top > bottom ({normalized['top']} > {normalized['bottom']})")

    # Add metadata
    normalized["page"] = page_num
    normalized["text"] = text or bbox.get("text", "")
    normalized["type"] = bbox_type or bbox.get("type") or bbox.get("block_type", "Unknown")

    return normalized


def polygon_to_bbox(polygon: List[List[float]]) -> Dict[str, float]:
    """
    Convert polygon coordinates to bounding box.

    Extracts minimum and maximum x/y coordinates from polygon points
    to create a rectangular bounding box.

    Args:
        polygon: List of [x, y] coordinate pairs
                 Example: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]

    Returns:
        Dictionary with keys: left, top, right, bottom

    Raises:
        ValueError: If polygon is empty or has invalid format

    Examples:
        >>> polygon = [[10, 20], [100, 20], [100, 50], [10, 50]]
        >>> polygon_to_bbox(polygon)
        {'left': 10.0, 'top': 20.0, 'right': 100.0, 'bottom': 50.0}

        >>> # Works with non-rectangular polygons too
        >>> irregular = [[10, 20], [50, 15], [100, 30], [80, 60], [20, 55]]
        >>> polygon_to_bbox(irregular)
        {'left': 10.0, 'top': 15.0, 'right': 100.0, 'bottom': 60.0}
    """
    if not polygon:
        raise ValueError("Polygon is empty")

    if not isinstance(polygon, list):
        raise ValueError(f"Polygon must be a list, got {type(polygon)}")

    # Validate polygon points
    for i, point in enumerate(polygon):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f"Polygon point {i} must be [x, y] pair, got {point}")

    # Extract x and y coordinates
    x_coords = [float(point[0]) for point in polygon]
    y_coords = [float(point[1]) for point in polygon]

    # Find bounding box
    return {
        "left": min(x_coords),
        "top": min(y_coords),
        "right": max(x_coords),
        "bottom": max(y_coords),
    }


def normalize_bboxes(
    bboxes: List[Dict[str, Any]],
    page_num: int,
    source: str = "auto",
) -> List[BBoxDict]:
    """
    Batch normalize a list of bboxes.

    Args:
        bboxes: List of bboxes in any supported format
        page_num: Page number for all bboxes (1-indexed)
        source: Source format ("auto", "marker", "docling", "pymupdf")

    Returns:
        List of normalized bbox dictionaries

    Examples:
        >>> marker_bboxes = [
        ...     {"polygon": [[10, 20], [100, 20], [100, 50], [10, 50]], "text": "Hello"},
        ...     {"polygon": [[10, 60], [100, 60], [100, 90], [10, 90]], "text": "World"},
        ... ]
        >>> normalize_bboxes(marker_bboxes, page_num=1, source="marker")
        [{'page': 1, 'left': 10.0, 'top': 20.0, ...}, {'page': 1, 'left': 10.0, 'top': 60.0, ...}]
    """
    normalized = []
    errors = 0

    for i, bbox in enumerate(bboxes):
        try:
            # Extract text and type if available
            text = bbox.get("text")
            bbox_type = bbox.get("type") or bbox.get("block_type")

            # Normalize the bbox
            norm_bbox = normalize_bbox(
                bbox=bbox,
                page_num=page_num,
                source=source,
                text=text,
                bbox_type=bbox_type,
            )
            normalized.append(norm_bbox)

        except Exception as e:
            errors += 1
            logger.warning(f"Failed to normalize bbox {i} on page {page_num}: {e}")
            logger.debug(f"Problematic bbox: {bbox}")

    if errors > 0:
        logger.warning(f"Failed to normalize {errors}/{len(bboxes)} bboxes on page {page_num}")

    return normalized


def _detect_bbox_format(bbox: Dict[str, Any]) -> str:
    """
    Auto-detect the bbox format.

    Args:
        bbox: Bounding box dictionary

    Returns:
        Detected format: "marker", "docling", "pymupdf", or "standard"

    Raises:
        ValueError: If format cannot be determined
    """
    # Check for polygon (Marker)
    if "polygon" in bbox:
        return "marker"

    # Check for direct polygon list
    if isinstance(bbox, list):
        return "polygon"

    # Check for Docling format
    if all(k in bbox for k in ["l", "t", "r", "b"]):
        return "docling"

    # Check for PyMuPDF format
    if all(k in bbox for k in ["x0", "y0", "x1", "y1"]):
        return "pymupdf"

    # Check for standard format
    if all(k in bbox for k in ["left", "top", "right", "bottom"]):
        return "standard"

    # Cannot determine format
    raise ValueError(f"Cannot auto-detect bbox format. Available keys: {bbox.keys()}")


def bbox_area(bbox: Dict[str, float]) -> float:
    """
    Calculate the area of a bounding box.

    Args:
        bbox: Bounding box with keys: left, top, right, bottom

    Returns:
        Area in square units

    Examples:
        >>> bbox = {"left": 10, "top": 20, "right": 100, "bottom": 50}
        >>> bbox_area(bbox)
        2700.0
    """
    width = bbox["right"] - bbox["left"]
    height = bbox["bottom"] - bbox["top"]
    return width * height


def bbox_iou(bbox1: Dict[str, float], bbox2: Dict[str, float]) -> float:
    """
    Calculate Intersection over Union (IoU) of two bounding boxes.

    Args:
        bbox1: First bounding box
        bbox2: Second bounding box

    Returns:
        IoU value between 0.0 and 1.0

    Examples:
        >>> bbox1 = {"left": 10, "top": 20, "right": 100, "bottom": 50}
        >>> bbox2 = {"left": 50, "top": 30, "right": 150, "bottom": 60}
        >>> iou = bbox_iou(bbox1, bbox2)
        >>> 0 < iou < 1  # Partial overlap
        True
    """
    # Calculate intersection
    left = max(bbox1["left"], bbox2["left"])
    top = max(bbox1["top"], bbox2["top"])
    right = min(bbox1["right"], bbox2["right"])
    bottom = min(bbox1["bottom"], bbox2["bottom"])

    # Check if there's no intersection
    if left >= right or top >= bottom:
        return 0.0

    # Calculate intersection area
    intersection = (right - left) * (bottom - top)

    # Calculate union area
    area1 = bbox_area(bbox1)
    area2 = bbox_area(bbox2)
    union = area1 + area2 - intersection

    # Return IoU
    return intersection / union if union > 0 else 0.0


def merge_overlapping_bboxes(
    bboxes: List[BBoxDict],
    iou_threshold: float = 0.5,
) -> List[BBoxDict]:
    """
    Merge overlapping bounding boxes.

    Args:
        bboxes: List of normalized bboxes
        iou_threshold: IoU threshold for merging (0.0 to 1.0)

    Returns:
        List of merged bboxes

    Examples:
        >>> bboxes = [
        ...     {"left": 10, "top": 20, "right": 100, "bottom": 50, "page": 1, "text": "Hello", "type": "Text"},
        ...     {"left": 50, "top": 30, "right": 150, "bottom": 60, "page": 1, "text": " World", "type": "Text"},
        ... ]
        >>> merged = merge_overlapping_bboxes(bboxes, iou_threshold=0.3)
        >>> len(merged) < len(bboxes)  # Should merge overlapping boxes
        True
    """
    if not bboxes:
        return []

    # Sort by left coordinate
    sorted_bboxes = sorted(bboxes, key=lambda b: b["left"])
    merged = []
    current = sorted_bboxes[0].copy()

    for bbox in sorted_bboxes[1:]:
        # Check if bboxes overlap significantly
        iou = bbox_iou(current, bbox)

        if iou >= iou_threshold:
            # Merge: expand current bbox
            current["left"] = min(current["left"], bbox["left"])
            current["top"] = min(current["top"], bbox["top"])
            current["right"] = max(current["right"], bbox["right"])
            current["bottom"] = max(current["bottom"], bbox["bottom"])
            # Concatenate text
            current["text"] = f"{current['text']} {bbox['text']}".strip()
        else:
            # No overlap: save current and start new
            merged.append(current)
            current = bbox.copy()

    # Add final bbox
    merged.append(current)

    return merged
