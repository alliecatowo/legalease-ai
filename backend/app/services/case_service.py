"""Case service for managing legal cases and their resources."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from minio import Minio
from minio.error import S3Error

from app.models.case import Case, CaseStatus
from app.core.config import settings


class CaseServiceError(Exception):
    """Base exception for case service errors."""

    pass


class CaseNotFoundError(CaseServiceError):
    """Raised when a case is not found."""

    pass


class CaseAlreadyExistsError(CaseServiceError):
    """Raised when trying to create a case with duplicate case_number."""

    pass


class ResourceCreationError(CaseServiceError):
    """Raised when Qdrant or MinIO resource creation fails."""

    pass


class CaseService:
    """
    Service for managing legal cases.

    Handles case CRUD operations and coordinates with Qdrant and MinIO
    to create/manage case-specific resources (collections and buckets).
    """

    def __init__(self, db: Session):
        """
        Initialize the case service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(url=settings.QDRANT_URL)

        # Initialize MinIO client
        self.minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    def _generate_collection_name(self, case_number: str) -> str:
        """
        Generate Qdrant collection name from case number.

        Args:
            case_number: The case number

        Returns:
            Normalized collection name
        """
        # Normalize case number to valid collection name
        # Replace special chars with underscores, lowercase
        return f"case_{case_number.lower().replace('-', '_').replace(' ', '_')}"

    def _generate_bucket_name(self, case_number: str) -> str:
        """
        Generate MinIO bucket name from case number.

        Args:
            case_number: The case number

        Returns:
            Normalized bucket name (lowercase, alphanumeric + hyphens)
        """
        # MinIO bucket names must be lowercase, alphanumeric + hyphens
        return f"case-{case_number.lower().replace('_', '-').replace(' ', '-')}"

    def _create_qdrant_collection(self, collection_name: str) -> None:
        """
        Create a Qdrant collection for the case.

        Args:
            collection_name: Name of the collection to create

        Raises:
            ResourceCreationError: If collection creation fails
        """
        try:
            # Check if collection already exists
            collections = self.qdrant_client.get_collections().collections
            if any(c.name == collection_name for c in collections):
                return  # Collection already exists

            # Create collection with vector configuration
            # Using 1536 dimensions for OpenAI embeddings (text-embedding-3-small/large)
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=1536,
                    distance=Distance.COSINE,
                ),
            )
        except Exception as e:
            raise ResourceCreationError(
                f"Failed to create Qdrant collection '{collection_name}': {str(e)}"
            )

    def _create_minio_bucket(self, bucket_name: str) -> None:
        """
        Create a MinIO bucket for the case.

        Args:
            bucket_name: Name of the bucket to create

        Raises:
            ResourceCreationError: If bucket creation fails
        """
        try:
            # Check if bucket already exists
            if self.minio_client.bucket_exists(bucket_name):
                return  # Bucket already exists

            # Create bucket
            self.minio_client.make_bucket(bucket_name)
        except S3Error as e:
            raise ResourceCreationError(
                f"Failed to create MinIO bucket '{bucket_name}': {str(e)}"
            )

    def _delete_qdrant_collection(self, collection_name: str) -> None:
        """
        Delete a Qdrant collection.

        Args:
            collection_name: Name of the collection to delete
        """
        try:
            collections = self.qdrant_client.get_collections().collections
            if any(c.name == collection_name for c in collections):
                self.qdrant_client.delete_collection(collection_name)
        except Exception:
            # Log but don't fail if collection deletion fails
            pass

    def _delete_minio_bucket(self, bucket_name: str) -> None:
        """
        Delete a MinIO bucket and all its contents.

        Args:
            bucket_name: Name of the bucket to delete
        """
        try:
            if not self.minio_client.bucket_exists(bucket_name):
                return

            # Delete all objects in the bucket first
            objects = self.minio_client.list_objects(bucket_name, recursive=True)
            for obj in objects:
                self.minio_client.remove_object(bucket_name, obj.object_name)

            # Delete the bucket
            self.minio_client.remove_bucket(bucket_name)
        except S3Error:
            # Log but don't fail if bucket deletion fails
            pass

    def create_case(
        self,
        name: str,
        case_number: str,
        client: str,
        matter_type: Optional[str] = None,
        team_id: Optional[UUID] = None,
    ) -> Case:
        """
        Create a new case with associated Qdrant collection and MinIO bucket.

        Args:
            name: Case name
            case_number: Unique case number
            client: Client name
            matter_type: Type of legal matter (optional)

        Returns:
            Created Case object

        Raises:
            CaseAlreadyExistsError: If case_number already exists
            ResourceCreationError: If resource creation fails
        """
        # Check if case already exists
        existing = self.db.query(Case).filter(Case.case_number == case_number).first()
        if existing:
            raise CaseAlreadyExistsError(
                f"Case with case_number '{case_number}' already exists"
            )

        # Create the case in STAGING status
        case = Case(
            name=name,
            case_number=case_number,
            client=client,
            matter_type=matter_type,
            status=CaseStatus.STAGING,
            team_id=team_id,
        )

        try:
            # Create Qdrant collection
            collection_name = self._generate_collection_name(case_number)
            self._create_qdrant_collection(collection_name)

            # Create MinIO bucket
            bucket_name = self._generate_bucket_name(case_number)
            self._create_minio_bucket(bucket_name)

            # Save case to database
            self.db.add(case)
            self.db.commit()
            self.db.refresh(case)

            return case

        except Exception as e:
            # Rollback database changes
            self.db.rollback()

            # Cleanup created resources
            try:
                collection_name = self._generate_collection_name(case_number)
                self._delete_qdrant_collection(collection_name)
            except Exception:
                pass

            try:
                bucket_name = self._generate_bucket_name(case_number)
                self._delete_minio_bucket(bucket_name)
            except Exception:
                pass

            if isinstance(e, (CaseServiceError, ResourceCreationError)):
                raise
            raise ResourceCreationError(f"Failed to create case: {str(e)}")

    def get_case(self, case_id: int, team_id: Optional[UUID] = None) -> Case:
        """
        Get a case by ID.

        Args:
            case_id: Case ID

        Returns:
            Case object

        Raises:
            CaseNotFoundError: If case not found
        """
        query = self.db.query(Case).filter(Case.id == case_id)
        if team_id:
            query = query.filter(Case.team_id == team_id)
        case = query.first()
        if not case:
            raise CaseNotFoundError(f"Case with id {case_id} not found")
        return case

    def get_case_by_number(self, case_number: str, team_id: Optional[UUID] = None) -> Case:
        """
        Get a case by case number.

        Args:
            case_number: Case number

        Returns:
            Case object

        Raises:
            CaseNotFoundError: If case not found
        """
        query = self.db.query(Case).filter(Case.case_number == case_number)
        if team_id:
            query = query.filter(Case.team_id == team_id)
        case = query.first()
        if not case:
            raise CaseNotFoundError(f"Case with case_number '{case_number}' not found")
        return case

    def list_cases(
        self,
        status: Optional[CaseStatus] = None,
        skip: int = 0,
        limit: int = 50,
        team_id: Optional[UUID] = None,
    ) -> tuple[List[Case], int]:
        """
        List cases with optional status filter.

        Args:
            status: Filter by case status (optional)
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of cases, total count)
        """
        query = self.db.query(Case)
        if team_id:
            query = query.filter(Case.team_id == team_id)

        # Apply status filter if provided
        if status:
            query = query.filter(Case.status == status)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        cases = query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()

        return cases, total

    def update_case(
        self,
        case_id: int,
        name: Optional[str] = None,
        case_number: Optional[str] = None,
        client: Optional[str] = None,
        matter_type: Optional[str] = None,
        team_id: Optional[UUID] = None,
    ) -> Case:
        """
        Update case details.

        Args:
            case_id: Case ID
            name: New case name (optional)
            case_number: New case number (optional)
            client: New client name (optional)
            matter_type: New matter type (optional)

        Returns:
            Updated Case object

        Raises:
            CaseNotFoundError: If case not found
            CaseAlreadyExistsError: If new case_number already exists
        """
        case = self.get_case(case_id, team_id=team_id)

        # Check if new case_number conflicts with existing cases
        if case_number and case_number != case.case_number:
            existing = (
                self.db.query(Case).filter(Case.case_number == case_number).first()
            )
            if existing:
                raise CaseAlreadyExistsError(
                    f"Case with case_number '{case_number}' already exists"
                )
            case.case_number = case_number

        # Update fields if provided
        if name is not None:
            case.name = name
        if client is not None:
            case.client = client
        if matter_type is not None:
            case.matter_type = matter_type

        self.db.commit()
        self.db.refresh(case)
        return case

    def activate_case(self, case_id: int, team_id: Optional[UUID] = None) -> Case:
        """
        Activate a case (change status to ACTIVE).

        This makes the case available for document processing and search.

        Args:
            case_id: Case ID

        Returns:
            Updated Case object

        Raises:
            CaseNotFoundError: If case not found
        """
        case = self.get_case(case_id, team_id=team_id)
        case.status = CaseStatus.ACTIVE
        self.db.commit()
        self.db.refresh(case)
        return case

    def unload_case(self, case_id: int, team_id: Optional[UUID] = None) -> Case:
        """
        Unload a case (change status to UNLOADED).

        This removes the case from active processing while preserving data.
        The Qdrant collection and MinIO bucket remain but are not actively used.

        Args:
            case_id: Case ID

        Returns:
            Updated Case object

        Raises:
            CaseNotFoundError: If case not found
        """
        case = self.get_case(case_id, team_id=team_id)
        case.status = CaseStatus.UNLOADED
        self.db.commit()
        self.db.refresh(case)
        return case

    def delete_case(self, case_id: int, team_id: Optional[UUID] = None) -> None:
        """
        Permanently delete a case and all associated resources.

        This deletes:
        - The case record from the database
        - All associated documents, chunks, entities (via cascade)
        - The Qdrant collection
        - The MinIO bucket and all files

        Args:
            case_id: Case ID

        Raises:
            CaseNotFoundError: If case not found
        """
        case = self.get_case(case_id, team_id=team_id)

        # Generate resource names
        collection_name = self._generate_collection_name(case.case_number)
        bucket_name = self._generate_bucket_name(case.case_number)

        # Delete Qdrant collection
        self._delete_qdrant_collection(collection_name)

        # Delete MinIO bucket
        self._delete_minio_bucket(bucket_name)

        # Delete case from database (cascades to related records)
        self.db.delete(case)
        self.db.commit()
