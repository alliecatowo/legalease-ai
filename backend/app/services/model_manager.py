"""
Model Manager Service

Handles downloading and caching ML models for self-hosted inference.
HuggingFace token optional - uses direct download URLs with auth if token provided.
"""
import os
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict
import httpx
from tqdm import tqdm

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages ML model downloads and caching."""

    # Pyannote model URLs (direct download, no HF token needed)
    PYANNOTE_MODELS = {
        "segmentation": {
            "url": "https://huggingface.co/pyannote/segmentation-3.0/resolve/main/pytorch_model.bin",
            "filename": "segmentation-3.0.bin",
            "sha256": None,  # Optional: add checksum for verification
            "size_mb": 5.91,
        },
        "embedding": {
            "url": "https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM/resolve/main/pytorch_model.bin",
            "filename": "wespeaker-voxceleb-resnet34-LM.bin",
            "sha256": None,
            "size_mb": 26.6,
        },
    }

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize model manager.

        Args:
            cache_dir: Directory to cache models (default: ./models)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Default to models/ in backend directory
            backend_dir = Path(__file__).parent.parent.parent
            self.cache_dir = backend_dir / "models" / "pyannote"

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Model cache directory: {self.cache_dir}")

    def get_model_path(self, model_name: str) -> Path:
        """
        Get path to cached model file.

        Args:
            model_name: Name of model (segmentation, embedding)

        Returns:
            Path to model file
        """
        if model_name not in self.PYANNOTE_MODELS:
            raise ValueError(f"Unknown model: {model_name}. Available: {list(self.PYANNOTE_MODELS.keys())}")

        model_info = self.PYANNOTE_MODELS[model_name]
        return self.cache_dir / model_info["filename"]

    def is_model_cached(self, model_name: str) -> bool:
        """
        Check if model is already downloaded and cached.

        Args:
            model_name: Name of model

        Returns:
            True if model exists in cache
        """
        model_path = self.get_model_path(model_name)
        exists = model_path.exists() and model_path.stat().st_size > 0

        if exists:
            logger.debug(f"Model '{model_name}' found in cache: {model_path}")
        else:
            logger.debug(f"Model '{model_name}' not in cache")

        return exists

    def download_model(
        self,
        model_name: str,
        force: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Path:
        """
        Download model from direct URL if not cached.

        Args:
            model_name: Name of model to download
            force: Force re-download even if cached
            progress_callback: Optional callback(downloaded_bytes, total_bytes)

        Returns:
            Path to downloaded model file

        Raises:
            ValueError: If model_name is unknown
            RuntimeError: If download fails
        """
        if model_name not in self.PYANNOTE_MODELS:
            raise ValueError(f"Unknown model: {model_name}")

        model_info = self.PYANNOTE_MODELS[model_name]
        model_path = self.get_model_path(model_name)

        # Check if already cached
        if not force and self.is_model_cached(model_name):
            logger.info(f"Model '{model_name}' already cached at {model_path}")
            return model_path

        # Download model
        logger.info(f"Downloading model '{model_name}' from {model_info['url']}")
        logger.info(f"Expected size: {model_info['size_mb']} MB")

        # Prepare headers with HF token if available
        headers = {}
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"
            logger.info("Using HuggingFace authentication token")
        else:
            logger.info("No HF_TOKEN found - attempting unauthenticated download")

        try:
            with httpx.stream("GET", model_info["url"], headers=headers, timeout=600, follow_redirects=True) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))

                # Use temp file during download
                temp_path = model_path.with_suffix(".tmp")

                with open(temp_path, "wb") as f:
                    downloaded = 0

                    # Progress bar
                    with tqdm(total=total_size, unit="B", unit_scale=True, desc=model_info["filename"]) as pbar:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            pbar.update(len(chunk))

                            # Call progress callback if provided
                            if progress_callback:
                                progress_callback(downloaded, total_size)

                # Verify download size
                actual_size = temp_path.stat().st_size
                if total_size > 0 and actual_size != total_size:
                    temp_path.unlink()
                    raise RuntimeError(
                        f"Download size mismatch: expected {total_size} bytes, got {actual_size} bytes"
                    )

                # Verify checksum if provided
                if model_info.get("sha256"):
                    logger.info("Verifying checksum...")
                    actual_hash = self._calculate_sha256(temp_path)
                    if actual_hash != model_info["sha256"]:
                        temp_path.unlink()
                        raise RuntimeError(
                            f"Checksum mismatch: expected {model_info['sha256']}, got {actual_hash}"
                        )

                # Move temp file to final location
                temp_path.replace(model_path)
                logger.info(f"Model '{model_name}' downloaded successfully to {model_path}")
                logger.info(f"File size: {actual_size / 1024 / 1024:.2f} MB")

                return model_path

        except httpx.HTTPError as e:
            logger.error(f"HTTP error downloading model '{model_name}': {e}")
            raise RuntimeError(f"Failed to download model: {e}")
        except Exception as e:
            logger.error(f"Error downloading model '{model_name}': {e}")
            raise RuntimeError(f"Failed to download model: {e}")

    def ensure_models_available(
        self,
        models: Optional[list] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Path]:
        """
        Ensure required models are available, downloading if necessary.

        Args:
            models: List of model names (default: all Pyannote models)
            progress_callback: Optional progress callback

        Returns:
            Dict mapping model names to paths
        """
        if models is None:
            models = list(self.PYANNOTE_MODELS.keys())

        model_paths = {}

        for model_name in models:
            try:
                model_paths[model_name] = self.download_model(
                    model_name,
                    progress_callback=progress_callback
                )
            except Exception as e:
                logger.error(f"Failed to ensure model '{model_name}' is available: {e}")
                raise

        return model_paths

    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha256.update(chunk)

        return sha256.hexdigest()

    def delete_model(self, model_name: str) -> bool:
        """
        Delete cached model.

        Args:
            model_name: Name of model to delete

        Returns:
            True if deleted, False if not found
        """
        model_path = self.get_model_path(model_name)

        if model_path.exists():
            model_path.unlink()
            logger.info(f"Deleted model '{model_name}' from cache")
            return True
        else:
            logger.warning(f"Model '{model_name}' not found in cache")
            return False

    def list_cached_models(self) -> Dict[str, Dict]:
        """
        List all cached models with their info.

        Returns:
            Dict mapping model names to info (path, size, etc.)
        """
        cached = {}

        for model_name in self.PYANNOTE_MODELS:
            if self.is_model_cached(model_name):
                model_path = self.get_model_path(model_name)
                stat = model_path.stat()

                cached[model_name] = {
                    "path": str(model_path),
                    "size_bytes": stat.st_size,
                    "size_mb": stat.st_size / 1024 / 1024,
                    "modified": stat.st_mtime,
                }

        return cached


# Singleton instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get singleton ModelManager instance."""
    global _model_manager

    if _model_manager is None:
        _model_manager = ModelManager()
        logger.info("Created ModelManager singleton")

    return _model_manager


# Convenience functions
def ensure_pyannote_models() -> Dict[str, Path]:
    """
    Ensure Pyannote models are available for diarization.

    Downloads on first run, then uses cached versions.
    No HuggingFace token required.

    Returns:
        Dict with paths to segmentation and embedding models
    """
    manager = get_model_manager()
    return manager.ensure_models_available(["segmentation", "embedding"])


def get_pyannote_model_paths() -> Dict[str, str]:
    """
    Get paths to Pyannote models (download if needed).

    Returns:
        Dict with string paths for compatibility
    """
    model_paths = ensure_pyannote_models()
    return {name: str(path) for name, path in model_paths.items()}
