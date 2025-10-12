"""
Device Manager for CUDA and ROCm Support

Handles automatic detection and configuration for both NVIDIA (CUDA) and AMD (ROCm) GPUs.
Provides a unified interface for device selection and compute type determination.
"""
import logging
import os
from typing import Optional, Tuple, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Supported device types."""
    CUDA = "cuda"
    ROCM = "rocm"
    CPU = "cpu"


class DeviceManager:
    """
    Manages device detection and configuration for CUDA and ROCm.

    Provides automatic detection of available accelerators and optimal
    compute type selection based on hardware capabilities.
    """

    def __init__(self):
        """Initialize device manager and detect available hardware."""
        self._device_type: Optional[DeviceType] = None
        self._device_name: Optional[str] = None
        self._device_count: int = 0
        self._compute_capability: Optional[str] = None
        self._vram_gb: Optional[float] = None

        self._detect_device()

    def _detect_device(self) -> None:
        """Detect available GPU hardware (CUDA or ROCm) or fallback to CPU."""
        # Check for forced CPU mode via environment variable
        if os.getenv('FORCE_CPU', '').lower() in ('1', 'true', 'yes'):
            logger.info("FORCE_CPU enabled, using CPU mode")
            self._device_type = DeviceType.CPU
            self._device_name = "CPU"
            self._device_count = 1
            return

        # Try CUDA first
        if self._detect_cuda():
            self._device_type = DeviceType.CUDA
            return

        # Try ROCm next
        if self._detect_rocm():
            self._device_type = DeviceType.ROCM
            return

        # Fallback to CPU
        self._device_type = DeviceType.CPU
        self._device_name = "CPU"
        self._device_count = 1
        logger.info("No GPU detected, using CPU")

    def _detect_cuda(self) -> bool:
        """
        Detect NVIDIA CUDA GPUs.

        Returns:
            True if CUDA is available, False otherwise
        """
        try:
            import torch

            if not torch.cuda.is_available():
                return False

            self._device_count = torch.cuda.device_count()
            if self._device_count == 0:
                return False

            # Get device properties
            device_props = torch.cuda.get_device_properties(0)
            self._device_name = device_props.name
            self._compute_capability = f"{device_props.major}.{device_props.minor}"
            self._vram_gb = device_props.total_memory / (1024**3)

            logger.info(f"CUDA detected: {self._device_name}")
            logger.info(f"  Compute Capability: {self._compute_capability}")
            logger.info(f"  VRAM: {self._vram_gb:.2f} GB")
            logger.info(f"  Device Count: {self._device_count}")

            return True

        except ImportError:
            logger.debug("PyTorch not available, skipping CUDA detection")
            return False
        except Exception as e:
            logger.warning(f"CUDA detection failed: {e}")
            return False

    def _detect_rocm(self) -> bool:
        """
        Detect AMD ROCm GPUs.

        Returns:
            True if ROCm is available, False otherwise
        """
        try:
            import torch

            # Check for ROCm-specific environment variable
            if not os.getenv('ROCM_HOME') and not os.path.exists('/opt/rocm'):
                logger.debug("ROCm installation not found")
                return False

            # PyTorch with ROCm uses the same API as CUDA
            # but the backend is different
            if not torch.cuda.is_available():
                return False

            # Verify it's actually ROCm by checking backend
            if not hasattr(torch.version, 'hip') or torch.version.hip is None:
                # If torch.version.hip exists, it's ROCm build
                return False

            self._device_count = torch.cuda.device_count()
            if self._device_count == 0:
                return False

            # Get device properties (same API as CUDA)
            device_props = torch.cuda.get_device_properties(0)
            self._device_name = device_props.name
            self._vram_gb = device_props.total_memory / (1024**3)

            # ROCm-specific compute capability (gfx version)
            try:
                gfx_version = device_props.gcnArchName
                self._compute_capability = gfx_version
            except AttributeError:
                self._compute_capability = "Unknown"

            logger.info(f"ROCm detected: {self._device_name}")
            logger.info(f"  GCN Arch: {self._compute_capability}")
            logger.info(f"  VRAM: {self._vram_gb:.2f} GB")
            logger.info(f"  Device Count: {self._device_count}")

            return True

        except ImportError:
            logger.debug("PyTorch (ROCm) not available")
            return False
        except Exception as e:
            logger.warning(f"ROCm detection failed: {e}")
            return False

    @property
    def device_type(self) -> DeviceType:
        """Get the detected device type."""
        return self._device_type

    @property
    def device_name(self) -> str:
        """Get the device name."""
        return self._device_name or "Unknown"

    @property
    def device_count(self) -> int:
        """Get the number of available devices."""
        return self._device_count

    @property
    def has_gpu(self) -> bool:
        """Check if GPU is available."""
        return self._device_type in (DeviceType.CUDA, DeviceType.ROCM)

    def get_device_string(self) -> str:
        """
        Get PyTorch device string.

        Returns:
            Device string for PyTorch (e.g., 'cuda', 'cpu')
        """
        if self._device_type == DeviceType.CPU:
            return "cpu"
        else:
            # Both CUDA and ROCm use 'cuda' in PyTorch API
            return "cuda"

    def get_compute_type(self, prefer_fp16: bool = True) -> str:
        """
        Get optimal compute type for the device.

        Args:
            prefer_fp16: Prefer FP16 if available (faster, less accurate)

        Returns:
            Compute type string (e.g., 'float16', 'float32', 'int8')
        """
        if not self.has_gpu:
            # CPU: use float32
            return "float32"

        if self._device_type == DeviceType.CUDA:
            # NVIDIA CUDA
            # FP16 supported on compute capability >= 5.3
            # BF16 supported on compute capability >= 8.0 (Ampere+)
            try:
                major, minor = map(int, self._compute_capability.split('.'))
                compute_cap = major * 10 + minor

                if compute_cap >= 80 and prefer_fp16:
                    # Ampere or newer: bfloat16 is ideal
                    logger.info("Using bfloat16 (Ampere+ GPU)")
                    return "bfloat16"
                elif compute_cap >= 70 and prefer_fp16:
                    # Volta or newer: float16 is good
                    logger.info("Using float16 (Volta+ GPU)")
                    return "float16"
                elif compute_cap >= 53 and prefer_fp16:
                    # Maxwell or newer: float16 supported
                    logger.info("Using float16 (Maxwell+ GPU)")
                    return "float16"
                else:
                    # Older GPUs: float32
                    logger.info("Using float32 (older GPU)")
                    return "float32"
            except (ValueError, AttributeError):
                # Fallback to float16 if supported, else float32
                return "float16" if prefer_fp16 else "float32"

        elif self._device_type == DeviceType.ROCM:
            # AMD ROCm
            # Most modern AMD GPUs support FP16
            # Check if it's a recent GPU (gfx9 or gfx10 series)
            if self._compute_capability and 'gfx' in self._compute_capability:
                try:
                    gfx_num = int(self._compute_capability.replace('gfx', '')[:2])
                    if gfx_num >= 90 and prefer_fp16:  # gfx90x (Vega 10, MI50) or newer
                        logger.info("Using float16 (modern AMD GPU)")
                        return "float16"
                except ValueError:
                    pass

            # Fallback to float32 for older or unknown AMD GPUs
            logger.info("Using float32 (AMD GPU)")
            return "float32"

        return "float32"

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get comprehensive device information.

        Returns:
            Dictionary with device details
        """
        return {
            "device_type": self._device_type.value if self._device_type else "unknown",
            "device_name": self.device_name,
            "device_count": self.device_count,
            "compute_capability": self._compute_capability,
            "vram_gb": self._vram_gb,
            "has_gpu": self.has_gpu,
            "device_string": self.get_device_string(),
            "optimal_compute_type": self.get_compute_type(),
        }

    def log_device_info(self) -> None:
        """Log device information for debugging."""
        info = self.get_device_info()
        logger.info("=== Device Information ===")
        for key, value in info.items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 30)


# Global singleton instance
_device_manager: Optional[DeviceManager] = None


def get_device_manager() -> DeviceManager:
    """
    Get or create singleton DeviceManager instance.

    Returns:
        DeviceManager instance
    """
    global _device_manager

    if _device_manager is None:
        _device_manager = DeviceManager()
        _device_manager.log_device_info()

    return _device_manager


def get_device() -> str:
    """
    Convenience function to get device string.

    Returns:
        Device string for PyTorch ('cuda' or 'cpu')
    """
    return get_device_manager().get_device_string()


def get_compute_type(prefer_fp16: bool = True) -> str:
    """
    Convenience function to get compute type.

    Args:
        prefer_fp16: Prefer FP16 if available

    Returns:
        Compute type string
    """
    return get_device_manager().get_compute_type(prefer_fp16=prefer_fp16)


def has_gpu() -> bool:
    """
    Convenience function to check GPU availability.

    Returns:
        True if GPU is available
    """
    return get_device_manager().has_gpu
