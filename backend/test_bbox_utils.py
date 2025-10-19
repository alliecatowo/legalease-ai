"""
Test script demonstrating bbox_utils.py functionality.

This script shows examples of converting between different bbox formats
and validates the utility functions work correctly.
"""

from app.workers.parsers.bbox_utils import (
    normalize_bbox,
    polygon_to_bbox,
    normalize_bboxes,
    bbox_area,
    bbox_iou,
    merge_overlapping_bboxes,
)


def test_polygon_to_bbox():
    """Test converting Marker polygon to bounding box."""
    print("\n" + "=" * 60)
    print("TEST: Polygon to BBox Conversion")
    print("=" * 60)

    # Example 1: Simple rectangle
    polygon = [[10, 20], [100, 20], [100, 50], [10, 50]]
    bbox = polygon_to_bbox(polygon)
    print(f"\nPolygon (rectangle): {polygon}")
    print(f"BBox: {bbox}")
    assert bbox == {"l": 10.0, "t": 20.0, "r": 100.0, "b": 50.0}
    print("✓ Rectangle conversion passed")

    # Example 2: Irregular polygon
    irregular = [[10, 20], [50, 15], [100, 30], [80, 60], [20, 55]]
    bbox = polygon_to_bbox(irregular)
    print(f"\nPolygon (irregular): {irregular}")
    print(f"BBox: {bbox}")
    assert bbox == {"l": 10.0, "t": 15.0, "r": 100.0, "b": 60.0}
    print("✓ Irregular polygon conversion passed")


def test_normalize_marker_bbox():
    """Test normalizing Marker format bbox."""
    print("\n" + "=" * 60)
    print("TEST: Normalize Marker BBox")
    print("=" * 60)

    marker_bbox = {
        "polygon": [[10, 20], [100, 20], [100, 50], [10, 50]],
        "text": "Hello World",
        "block_type": "Text",
    }

    normalized = normalize_bbox(marker_bbox, page_num=1, source="marker")
    print(f"\nMarker BBox: {marker_bbox}")
    print(f"Normalized: {normalized}")

    assert normalized["page"] == 1
    assert normalized["l"] == 10.0
    assert normalized["t"] == 20.0
    assert normalized["r"] == 100.0
    assert normalized["b"] == 50.0
    assert normalized["text"] == "Hello World"
    assert normalized["type"] == "Text"
    print("✓ Marker normalization passed")


def test_normalize_docling_bbox():
    """Test normalizing Docling format bbox."""
    print("\n" + "=" * 60)
    print("TEST: Normalize Docling BBox")
    print("=" * 60)

    docling_bbox = {
        "l": 10,
        "t": 20,
        "r": 100,
        "b": 50,
        "text": "Docling text",
        "type": "Paragraph",
    }

    normalized = normalize_bbox(docling_bbox, page_num=2, source="docling")
    print(f"\nDocling BBox: {docling_bbox}")
    print(f"Normalized: {normalized}")

    assert normalized["page"] == 2
    assert normalized["l"] == 10.0
    assert normalized["t"] == 20.0
    assert normalized["r"] == 100.0
    assert normalized["b"] == 50.0
    assert normalized["text"] == "Docling text"
    assert normalized["type"] == "Paragraph"
    print("✓ Docling normalization passed")


def test_normalize_pymupdf_bbox():
    """Test normalizing PyMuPDF format bbox."""
    print("\n" + "=" * 60)
    print("TEST: Normalize PyMuPDF BBox")
    print("=" * 60)

    pymupdf_bbox = {
        "x0": 10,
        "y0": 20,
        "x1": 100,
        "y1": 50,
        "text": "PyMuPDF text",
    }

    normalized = normalize_bbox(pymupdf_bbox, page_num=3, source="pymupdf")
    print(f"\nPyMuPDF BBox: {pymupdf_bbox}")
    print(f"Normalized: {normalized}")

    assert normalized["page"] == 3
    assert normalized["l"] == 10.0
    assert normalized["t"] == 20.0
    assert normalized["r"] == 100.0
    assert normalized["b"] == 50.0
    assert normalized["text"] == "PyMuPDF text"
    print("✓ PyMuPDF normalization passed")


def test_auto_detect():
    """Test auto-detection of bbox format."""
    print("\n" + "=" * 60)
    print("TEST: Auto-Detect BBox Format")
    print("=" * 60)

    # Test Marker auto-detection
    marker = {"polygon": [[10, 20], [100, 50]]}
    normalized = normalize_bbox(marker, page_num=1, source="auto")
    print(f"\nAuto-detected Marker: {normalized['type']}")
    assert normalized["l"] == 10.0
    print("✓ Marker auto-detection passed")

    # Test Docling auto-detection
    docling = {"l": 10, "t": 20, "r": 100, "b": 50}
    normalized = normalize_bbox(docling, page_num=1, source="auto")
    print(f"Auto-detected Docling: {normalized}")
    assert normalized["l"] == 10.0
    print("✓ Docling auto-detection passed")

    # Test PyMuPDF auto-detection
    pymupdf = {"x0": 10, "y0": 20, "x1": 100, "y1": 50}
    normalized = normalize_bbox(pymupdf, page_num=1, source="auto")
    print(f"Auto-detected PyMuPDF: {normalized}")
    assert normalized["l"] == 10.0
    print("✓ PyMuPDF auto-detection passed")


def test_batch_normalize():
    """Test batch normalization of multiple bboxes."""
    print("\n" + "=" * 60)
    print("TEST: Batch Normalize BBoxes")
    print("=" * 60)

    marker_bboxes = [
        {
            "polygon": [[10, 20], [100, 20], [100, 50], [10, 50]],
            "text": "First block",
            "block_type": "Text",
        },
        {
            "polygon": [[10, 60], [100, 60], [100, 90], [10, 90]],
            "text": "Second block",
            "block_type": "Text",
        },
        {
            "polygon": [[10, 100], [200, 100], [200, 150], [10, 150]],
            "text": "Third block (wider)",
            "block_type": "Table",
        },
    ]

    normalized = normalize_bboxes(marker_bboxes, page_num=1, source="marker")
    print(f"\nOriginal count: {len(marker_bboxes)}")
    print(f"Normalized count: {len(normalized)}")

    assert len(normalized) == 3
    assert normalized[0]["text"] == "First block"
    assert normalized[1]["text"] == "Second block"
    assert normalized[2]["text"] == "Third block (wider)"
    assert normalized[2]["type"] == "Table"

    print("\nNormalized BBoxes:")
    for i, bbox in enumerate(normalized, 1):
        print(f"  {i}. Page {bbox['page']}: [{bbox['l']}, {bbox['t']}, {bbox['r']}, {bbox['b']}] - {bbox['text'][:20]}...")

    print("✓ Batch normalization passed")


def test_bbox_area():
    """Test bbox area calculation."""
    print("\n" + "=" * 60)
    print("TEST: BBox Area Calculation")
    print("=" * 60)

    bbox = {"l": 10, "t": 20, "r": 100, "b": 50}
    area = bbox_area(bbox)
    print(f"\nBBox: {bbox}")
    print(f"Area: {area}")

    # Width = 90, Height = 30, Area = 2700
    assert area == 2700.0
    print("✓ Area calculation passed")


def test_bbox_iou():
    """Test IoU calculation."""
    print("\n" + "=" * 60)
    print("TEST: BBox IoU (Intersection over Union)")
    print("=" * 60)

    # Overlapping bboxes
    bbox1 = {"l": 10, "t": 20, "r": 100, "b": 50}
    bbox2 = {"l": 50, "t": 30, "r": 150, "b": 60}

    iou = bbox_iou(bbox1, bbox2)
    print(f"\nBBox1: {bbox1}")
    print(f"BBox2: {bbox2}")
    print(f"IoU: {iou:.4f}")

    assert 0 < iou < 1
    print("✓ IoU calculation passed (partial overlap)")

    # Non-overlapping bboxes
    bbox3 = {"l": 200, "t": 200, "r": 300, "b": 300}
    iou = bbox_iou(bbox1, bbox3)
    print(f"\nBBox1: {bbox1}")
    print(f"BBox3: {bbox3}")
    print(f"IoU: {iou:.4f}")

    assert iou == 0.0
    print("✓ IoU calculation passed (no overlap)")


def test_merge_overlapping():
    """Test merging overlapping bboxes."""
    print("\n" + "=" * 60)
    print("TEST: Merge Overlapping BBoxes")
    print("=" * 60)

    bboxes = [
        {"l": 10, "t": 20, "r": 100, "b": 50, "page": 1, "text": "Hello", "type": "Text"},
        {"l": 50, "t": 30, "r": 150, "b": 60, "page": 1, "text": "World", "type": "Text"},
        {"l": 200, "t": 20, "r": 300, "b": 50, "page": 1, "text": "Separate", "type": "Text"},
    ]

    print(f"\nOriginal BBoxes: {len(bboxes)}")
    for i, bbox in enumerate(bboxes, 1):
        print(f"  {i}. [{bbox['l']}, {bbox['t']}, {bbox['r']}, {bbox['b']}] - {bbox['text']}")

    merged = merge_overlapping_bboxes(bboxes, iou_threshold=0.3)

    print(f"\nMerged BBoxes: {len(merged)}")
    for i, bbox in enumerate(merged, 1):
        print(f"  {i}. [{bbox['l']}, {bbox['t']}, {bbox['r']}, {bbox['b']}] - {bbox['text']}")

    # Should merge first two, keep third separate
    assert len(merged) == 2
    assert "Hello" in merged[0]["text"] and "World" in merged[0]["text"]
    assert merged[1]["text"] == "Separate"
    print("✓ Merge overlapping passed")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("BBox Utils Test Suite")
    print("=" * 60)

    try:
        test_polygon_to_bbox()
        test_normalize_marker_bbox()
        test_normalize_docling_bbox()
        test_normalize_pymupdf_bbox()
        test_auto_detect()
        test_batch_normalize()
        test_bbox_area()
        test_bbox_iou()
        test_merge_overlapping()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
