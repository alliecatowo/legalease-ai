"""
Custom Haystack component for converting Cellebrite AXIOM exports to Documents.

This component parses Cellebrite forensic exports (SMS, WhatsApp, Signal, etc.)
and converts them into Haystack Document objects with comprehensive metadata.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from haystack import component, Document
from haystack.dataclasses import ByteStream

logger = logging.getLogger(__name__)


@component
class CellebriteConverter:
    """
    Convert Cellebrite AXIOM exports to Haystack Documents.

    This component processes forensic exports containing communication data
    from various platforms (SMS, WhatsApp, Signal, Instagram, etc.) and
    converts them into structured Document objects.

    **Supported Platforms:**
    - SMS/MMS
    - WhatsApp
    - Signal
    - Instagram Direct
    - Facebook Messenger
    - iMessage
    - Telegram

    **Input:**
    - Path to Cellebrite export folder
    - Or parsed export data (dict)

    **Output:**
    - List[Document] with message data and metadata

    **Document Metadata:**
    - thread_id: Conversation identifier
    - message_id: Unique message ID
    - sender: Sender identifier
    - participants: List of all participants
    - timestamp: Message timestamp
    - platform: Communication platform
    - device_id: Source device
    - attachments: List of attachment references
    - deleted: Whether message was deleted
    - case_id: Associated case UUID
    - source_type: Always "COMMUNICATION"

    Usage:
        ```python
        converter = CellebriteConverter(case_id="case-uuid-here")
        documents = converter.run(
            export_path="/path/to/cellebrite/export"
        )["documents"]
        ```
    """

    def __init__(
        self,
        case_id: Optional[Union[str, UUID]] = None,
        platform_filter: Optional[List[str]] = None,
        include_deleted: bool = True,
        include_attachments: bool = True,
    ):
        """
        Initialize the Cellebrite converter.

        Args:
            case_id: UUID of the case (optional, can be set per run)
            platform_filter: List of platforms to include (None = all)
            include_deleted: Whether to include deleted messages
            include_attachments: Whether to include attachment references
        """
        self.case_id = str(case_id) if case_id else None
        self.platform_filter = platform_filter
        self.include_deleted = include_deleted
        self.include_attachments = include_attachments

        logger.info(
            f"Initialized CellebriteConverter(case_id={self.case_id}, "
            f"platforms={platform_filter or 'ALL'}, "
            f"include_deleted={include_deleted})"
        )

    @component.output_types(documents=List[Document])
    def run(
        self,
        export_path: Optional[str] = None,
        export_data: Optional[Dict[str, Any]] = None,
        case_id: Optional[Union[str, UUID]] = None,
    ) -> Dict[str, List[Document]]:
        """
        Convert Cellebrite export to Haystack Documents.

        Args:
            export_path: Path to Cellebrite export folder
            export_data: Pre-parsed export data (alternative to export_path)
            case_id: Case UUID (overrides instance case_id)

        Returns:
            Dictionary with "documents" key containing List[Document]

        Raises:
            ValueError: If neither export_path nor export_data provided
        """
        # Determine case_id
        active_case_id = str(case_id) if case_id else self.case_id

        # Load export data
        if export_path:
            export_data = self._load_export_folder(export_path)
        elif export_data is None:
            raise ValueError("Either export_path or export_data must be provided")

        # Parse messages from export
        messages = self._parse_messages(export_data)

        # Filter by platform
        if self.platform_filter:
            messages = [
                msg for msg in messages
                if msg.get("platform") in self.platform_filter
            ]

        # Filter deleted messages
        if not self.include_deleted:
            messages = [msg for msg in messages if not msg.get("deleted", False)]

        # Convert to Documents
        documents = []
        for msg in messages:
            try:
                doc = self._message_to_document(msg, active_case_id)
                documents.append(doc)
            except Exception as e:
                logger.warning(f"Failed to convert message {msg.get('message_id')}: {e}")
                continue

        logger.info(f"Converted {len(documents)} messages from Cellebrite export")
        return {"documents": documents}

    def _load_export_folder(self, export_path: str) -> Dict[str, Any]:
        """
        Load and parse Cellebrite export folder.

        Args:
            export_path: Path to export folder

        Returns:
            Parsed export data dictionary
        """
        path = Path(export_path)

        if not path.exists():
            raise ValueError(f"Export path does not exist: {export_path}")

        if not path.is_dir():
            raise ValueError(f"Export path is not a directory: {export_path}")

        # Load ExportSummary.json
        summary_file = path / "ExportSummary.json"
        if not summary_file.exists():
            raise ValueError(f"ExportSummary.json not found in {export_path}")

        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)

        # Load Report.html metadata
        report_file = path / "Report.html"
        report_exists = report_file.exists()

        # Scan for message files in Resources folder
        resources_path = path / "Resources"
        message_files = []

        if resources_path.exists():
            # Look for JSON message files
            for file_path in resources_path.rglob("*.json"):
                if self._is_message_file(file_path):
                    message_files.append(file_path)

            # Also look for HTML chat files
            for file_path in resources_path.rglob("*.html"):
                if self._is_message_file(file_path):
                    message_files.append(file_path)

        logger.info(f"Found {len(message_files)} message files in export")

        return {
            "summary": summary,
            "report_exists": report_exists,
            "message_files": message_files,
            "export_path": str(path.absolute()),
        }

    def _is_message_file(self, file_path: Path) -> bool:
        """
        Check if a file contains message data.

        Args:
            file_path: Path to file

        Returns:
            True if file appears to contain messages
        """
        # Common message file patterns
        message_patterns = [
            r"message",
            r"chat",
            r"conversation",
            r"sms",
            r"whatsapp",
            r"signal",
            r"telegram",
            r"instagram",
            r"facebook",
        ]

        filename_lower = file_path.name.lower()
        return any(re.search(pattern, filename_lower) for pattern in message_patterns)

    def _parse_messages(self, export_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse messages from export data.

        Args:
            export_data: Export data dictionary

        Returns:
            List of message dictionaries
        """
        messages = []

        # Parse each message file
        for file_path in export_data.get("message_files", []):
            try:
                if file_path.suffix == ".json":
                    file_messages = self._parse_json_messages(file_path)
                elif file_path.suffix == ".html":
                    file_messages = self._parse_html_messages(file_path)
                else:
                    continue

                messages.extend(file_messages)
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")
                continue

        return messages

    def _parse_json_messages(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse messages from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            List of message dictionaries
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        messages = []

        # Handle different JSON structures
        if isinstance(data, list):
            # Array of messages
            for item in data:
                msg = self._normalize_message(item, file_path)
                if msg:
                    messages.append(msg)
        elif isinstance(data, dict):
            # Check for common container fields
            for key in ["messages", "data", "items", "records"]:
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        msg = self._normalize_message(item, file_path)
                        if msg:
                            messages.append(msg)
                    break
            else:
                # Single message object
                msg = self._normalize_message(data, file_path)
                if msg:
                    messages.append(msg)

        return messages

    def _parse_html_messages(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse messages from HTML file.

        This is a simplified parser. For production, consider using BeautifulSoup.

        Args:
            file_path: Path to HTML file

        Returns:
            List of message dictionaries
        """
        # For now, skip HTML parsing (requires BeautifulSoup)
        # In production, implement HTML parsing here
        logger.debug(f"Skipping HTML file (not implemented): {file_path}")
        return []

    def _normalize_message(
        self,
        raw_message: Dict[str, Any],
        source_file: Path,
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize message from various formats to standard structure.

        Args:
            raw_message: Raw message data
            source_file: Source file path

        Returns:
            Normalized message dictionary or None if invalid
        """
        # Extract core fields (try common field names)
        message_id = self._extract_field(
            raw_message,
            ["id", "message_id", "messageId", "Id", "MessageId"]
        )

        body = self._extract_field(
            raw_message,
            ["body", "text", "message", "content", "Body", "Text", "Message"]
        )

        # Skip if no body
        if not body:
            return None

        sender = self._extract_field(
            raw_message,
            ["sender", "from", "author", "Sender", "From", "Author"]
        )

        # Parse timestamp
        timestamp_raw = self._extract_field(
            raw_message,
            ["timestamp", "time", "date", "created", "Timestamp", "Time", "Date"]
        )
        timestamp = self._parse_timestamp(timestamp_raw)

        # Extract participants
        participants = self._extract_participants(raw_message)

        # Detect platform from source file or metadata
        platform = self._detect_platform(raw_message, source_file)

        # Extract thread/conversation ID
        thread_id = self._extract_field(
            raw_message,
            ["thread_id", "conversation_id", "chat_id", "ThreadId", "ConversationId"]
        )

        # Check if deleted
        deleted = self._is_deleted(raw_message)

        # Extract attachments
        attachments = []
        if self.include_attachments:
            attachments = self._extract_attachments(raw_message)

        # Device ID
        device_id = self._extract_field(
            raw_message,
            ["device_id", "device", "source_device", "DeviceId"]
        )

        return {
            "message_id": message_id or self._generate_message_id(raw_message),
            "body": body,
            "sender": sender or "Unknown",
            "timestamp": timestamp,
            "participants": participants,
            "platform": platform,
            "thread_id": thread_id,
            "deleted": deleted,
            "attachments": attachments,
            "device_id": device_id,
            "raw_data": raw_message,  # Store raw for debugging
        }

    def _extract_field(
        self,
        data: Dict[str, Any],
        field_names: List[str],
    ) -> Optional[Any]:
        """
        Extract field trying multiple possible names.

        Args:
            data: Data dictionary
            field_names: List of possible field names

        Returns:
            Field value or None
        """
        for field in field_names:
            if field in data:
                value = data[field]
                # Skip empty values
                if value is not None and value != "":
                    return value
        return None

    def _parse_timestamp(self, timestamp_raw: Any) -> Optional[datetime]:
        """
        Parse timestamp from various formats.

        Args:
            timestamp_raw: Raw timestamp value

        Returns:
            Parsed datetime or None
        """
        if timestamp_raw is None:
            return None

        # If already datetime
        if isinstance(timestamp_raw, datetime):
            return timestamp_raw

        # Unix timestamp (int or float)
        if isinstance(timestamp_raw, (int, float)):
            try:
                # Handle milliseconds
                if timestamp_raw > 1e12:
                    return datetime.fromtimestamp(timestamp_raw / 1000)
                else:
                    return datetime.fromtimestamp(timestamp_raw)
            except Exception as e:
                logger.warning(f"Failed to parse unix timestamp {timestamp_raw}: {e}")
                return None

        # String timestamp
        if isinstance(timestamp_raw, str):
            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%m/%d/%Y %I:%M:%S %p",  # Cellebrite format
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_raw, fmt)
                except ValueError:
                    continue

            logger.warning(f"Failed to parse timestamp string: {timestamp_raw}")

        return None

    def _extract_participants(self, message: Dict[str, Any]) -> List[str]:
        """
        Extract participant list from message.

        Args:
            message: Message dictionary

        Returns:
            List of participant identifiers
        """
        participants = []

        # Try common fields
        participants_raw = self._extract_field(
            message,
            ["participants", "members", "Participants", "Members"]
        )

        if participants_raw:
            if isinstance(participants_raw, list):
                participants = [str(p) for p in participants_raw]
            elif isinstance(participants_raw, str):
                # Split comma-separated
                participants = [p.strip() for p in participants_raw.split(",")]

        # Add sender if not in participants
        sender = self._extract_field(message, ["sender", "from", "Sender", "From"])
        if sender and sender not in participants:
            participants.append(str(sender))

        # Add recipient if not in participants
        recipient = self._extract_field(message, ["recipient", "to", "Recipient", "To"])
        if recipient and recipient not in participants:
            participants.append(str(recipient))

        return participants

    def _detect_platform(
        self,
        message: Dict[str, Any],
        source_file: Path,
    ) -> str:
        """
        Detect communication platform.

        Args:
            message: Message dictionary
            source_file: Source file path

        Returns:
            Platform identifier
        """
        # Try explicit field
        platform = self._extract_field(
            message,
            ["platform", "source", "type", "Platform", "Source", "Type"]
        )

        if platform:
            return str(platform).upper()

        # Detect from filename
        filename_lower = source_file.name.lower()

        platform_patterns = {
            "SMS": r"sms|text",
            "WHATSAPP": r"whatsapp",
            "SIGNAL": r"signal",
            "INSTAGRAM": r"instagram",
            "FACEBOOK": r"facebook|messenger",
            "IMESSAGE": r"imessage|apple",
            "TELEGRAM": r"telegram",
        }

        for platform_name, pattern in platform_patterns.items():
            if re.search(pattern, filename_lower):
                return platform_name

        return "UNKNOWN"

    def _is_deleted(self, message: Dict[str, Any]) -> bool:
        """
        Check if message was deleted.

        Args:
            message: Message dictionary

        Returns:
            True if deleted
        """
        deleted = self._extract_field(
            message,
            ["deleted", "is_deleted", "Deleted", "IsDeleted"]
        )

        if deleted is not None:
            return bool(deleted)

        # Check for deletion markers
        status = self._extract_field(message, ["status", "state", "Status", "State"])
        if status and "deleted" in str(status).lower():
            return True

        return False

    def _extract_attachments(self, message: Dict[str, Any]) -> List[str]:
        """
        Extract attachment references.

        Args:
            message: Message dictionary

        Returns:
            List of attachment paths/URLs
        """
        attachments = []

        # Try common fields
        attachments_raw = self._extract_field(
            message,
            ["attachments", "media", "files", "Attachments", "Media", "Files"]
        )

        if attachments_raw:
            if isinstance(attachments_raw, list):
                for att in attachments_raw:
                    if isinstance(att, dict):
                        # Extract path or URL
                        path = self._extract_field(
                            att,
                            ["path", "url", "file", "Path", "URL", "File"]
                        )
                        if path:
                            attachments.append(str(path))
                    else:
                        attachments.append(str(att))
            elif isinstance(attachments_raw, str):
                attachments.append(attachments_raw)

        return attachments

    def _generate_message_id(self, message: Dict[str, Any]) -> str:
        """
        Generate a message ID from message content.

        Args:
            message: Message dictionary

        Returns:
            Generated ID
        """
        # Use hash of message content
        import hashlib

        content = json.dumps(message, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _message_to_document(
        self,
        message: Dict[str, Any],
        case_id: Optional[str],
    ) -> Document:
        """
        Convert message to Haystack Document.

        Args:
            message: Normalized message dictionary
            case_id: Case UUID

        Returns:
            Haystack Document
        """
        # Build metadata
        meta = {
            "thread_id": message.get("thread_id"),
            "message_id": message["message_id"],
            "sender": message["sender"],
            "participants": message["participants"],
            "timestamp": message.get("timestamp").isoformat() if message.get("timestamp") else None,
            "platform": message["platform"],
            "device_id": message.get("device_id"),
            "attachments": message.get("attachments", []),
            "deleted": message["deleted"],
            "source_type": "COMMUNICATION",
        }

        if case_id:
            meta["case_id"] = case_id

        # Create Document
        return Document(
            content=message["body"],
            meta=meta,
        )
