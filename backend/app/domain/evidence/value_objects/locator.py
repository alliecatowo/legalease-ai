"""
Locator value object for the Evidence domain.

Represents specific locations within evidence sources, including
page numbers, timestamps, message IDs, and bounding boxes.
"""

from dataclasses import dataclass
from typing import Optional, Protocol


class Locator(Protocol):
    """
    Protocol for locator types.

    All locators must implement a way to describe their location
    in a human-readable format.
    """

    def describe(self) -> str:
        """Return a human-readable description of the location."""
        ...


@dataclass(frozen=True)
class PageLocator:
    """
    Immutable page-based locator for documents.

    Attributes:
        page: Page number (1-indexed)
        paragraph: Optional paragraph number on the page
        line: Optional line number within paragraph
        bates_number: Optional Bates stamp identifier

    Example:
        >>> loc = PageLocator(page=5, paragraph=2)
        >>> loc.describe()
        'Page 5, Paragraph 2'
        >>> loc.page
        5
    """

    page: int
    paragraph: Optional[int] = None
    line: Optional[int] = None
    bates_number: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate locator invariants."""
        if self.page < 1:
            raise ValueError(f"Page must be >= 1, got {self.page}")
        if self.paragraph is not None and self.paragraph < 1:
            raise ValueError(f"Paragraph must be >= 1, got {self.paragraph}")
        if self.line is not None and self.line < 1:
            raise ValueError(f"Line must be >= 1, got {self.line}")

    def describe(self) -> str:
        """Return a human-readable description."""
        parts = [f"Page {self.page}"]
        if self.paragraph:
            parts.append(f"Paragraph {self.paragraph}")
        if self.line:
            parts.append(f"Line {self.line}")
        if self.bates_number:
            parts.append(f"Bates: {self.bates_number}")
        return ", ".join(parts)


@dataclass(frozen=True)
class TimecodeLocator:
    """
    Immutable timecode locator for audio/video transcripts.

    Attributes:
        start: Start time in seconds
        end: Optional end time in seconds
        segment_id: Optional segment identifier

    Example:
        >>> loc = TimecodeLocator(start=125.5, end=130.2)
        >>> loc.describe()
        '02:05.5 - 02:10.2'
        >>> loc.duration
        4.7
    """

    start: float
    end: Optional[float] = None
    segment_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate locator invariants."""
        if self.start < 0:
            raise ValueError(f"Start time must be >= 0, got {self.start}")
        if self.end is not None:
            if self.end < 0:
                raise ValueError(f"End time must be >= 0, got {self.end}")
            if self.end < self.start:
                raise ValueError(f"End time ({self.end}) must be >= start time ({self.start})")

    @property
    def duration(self) -> Optional[float]:
        """Calculate duration in seconds."""
        if self.end is None:
            return None
        return self.end - self.start

    def describe(self) -> str:
        """Return a human-readable description."""
        start_str = self._format_timecode(self.start)
        if self.end is not None:
            end_str = self._format_timecode(self.end)
            result = f"{start_str} - {end_str}"
        else:
            result = start_str

        if self.segment_id:
            result += f" (Segment: {self.segment_id})"
        return result

    @staticmethod
    def _format_timecode(seconds: float) -> str:
        """Format seconds as MM:SS.s"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:04.1f}"


@dataclass(frozen=True)
class MessageLocator:
    """
    Immutable message locator for communications.

    Attributes:
        message_id: Unique message identifier
        thread_id: Thread or conversation identifier
        position: Optional position within thread

    Example:
        >>> loc = MessageLocator(message_id="msg_12345", thread_id="thread_001", position=5)
        >>> loc.describe()
        'Message msg_12345 (Thread: thread_001, Position: 5)'
    """

    message_id: str
    thread_id: Optional[str] = None
    position: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate locator invariants."""
        if not self.message_id:
            raise ValueError("Message ID cannot be empty")
        if self.position is not None and self.position < 1:
            raise ValueError(f"Position must be >= 1, got {self.position}")

    def describe(self) -> str:
        """Return a human-readable description."""
        parts = [f"Message {self.message_id}"]
        if self.thread_id:
            parts.append(f"Thread: {self.thread_id}")
        if self.position:
            parts.append(f"Position: {self.position}")
        return " (" + ", ".join(parts[1:]) + ")" if len(parts) > 1 else parts[0]


@dataclass(frozen=True)
class BoundingBox:
    """
    Immutable bounding box for spatial locations (e.g., OCR, image regions).

    Attributes:
        x: X-coordinate of top-left corner (0.0-1.0, normalized)
        y: Y-coordinate of top-left corner (0.0-1.0, normalized)
        width: Width of the box (0.0-1.0, normalized)
        height: Height of the box (0.0-1.0, normalized)
        page: Optional page number for multi-page documents

    Example:
        >>> box = BoundingBox(x=0.1, y=0.2, width=0.5, height=0.3, page=1)
        >>> box.describe()
        'BoundingBox(x=0.10, y=0.20, w=0.50, h=0.30) on Page 1'
        >>> box.area
        0.15
    """

    x: float
    y: float
    width: float
    height: float
    page: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate bounding box invariants."""
        if not 0.0 <= self.x <= 1.0:
            raise ValueError(f"x must be between 0.0 and 1.0, got {self.x}")
        if not 0.0 <= self.y <= 1.0:
            raise ValueError(f"y must be between 0.0 and 1.0, got {self.y}")
        if not 0.0 <= self.width <= 1.0:
            raise ValueError(f"width must be between 0.0 and 1.0, got {self.width}")
        if not 0.0 <= self.height <= 1.0:
            raise ValueError(f"height must be between 0.0 and 1.0, got {self.height}")
        if self.x + self.width > 1.0:
            raise ValueError(f"x + width must be <= 1.0, got {self.x + self.width}")
        if self.y + self.height > 1.0:
            raise ValueError(f"y + height must be <= 1.0, got {self.y + self.height}")
        if self.page is not None and self.page < 1:
            raise ValueError(f"Page must be >= 1, got {self.page}")

    @property
    def area(self) -> float:
        """Calculate the area of the bounding box."""
        return self.width * self.height

    def describe(self) -> str:
        """Return a human-readable description."""
        result = f"BoundingBox(x={self.x:.2f}, y={self.y:.2f}, w={self.width:.2f}, h={self.height:.2f})"
        if self.page:
            result += f" on Page {self.page}"
        return result
