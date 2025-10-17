"""
Model Selection Service for Adaptive Transcription

Automatically selects optimal models and settings based on available VRAM.

Priority order for resource constraints:
1. Drop concurrency (go sequential)
2. Reduce model size (medium → small → base → tiny)
3. Last resort: disable diarization
"""
import logging
from typing import Dict, Tuple, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelSelector:
    """Intelligently select models and settings based on available hardware."""

    # Model VRAM requirements (in GB)
    WHISPER_MODEL_VRAM = {
        "tiny": 1.0,
        "base": 2.0,
        "small": 3.0,
        "medium": 5.0,
        "large": 10.0,
    }

    # Pyannote diarization requires ~3-4GB additional VRAM
    PYANNOTE_VRAM = 4.0

    @staticmethod
    def select_whisper_model(
        vram_gb: float, user_preference: str = "auto"
    ) -> str:
        """
        Auto-select WhisperX model based on VRAM.

        Args:
            vram_gb: Available VRAM in GB
            user_preference: User's model preference (auto, tiny, base, small, medium, large)

        Returns:
            Selected model name
        """
        if user_preference != "auto":
            logger.info(f"Using user-specified model: {user_preference}")
            return user_preference

        # Auto-select based on VRAM
        # Reserve 1GB buffer for other operations
        usable_vram = vram_gb - 1.0

        if usable_vram >= 10:
            model = "large"
        elif usable_vram >= 5:
            model = "medium"
        elif usable_vram >= 3:
            model = "small"
        elif usable_vram >= 2:
            model = "base"
        else:
            model = "tiny"

        logger.info(
            f"Auto-selected WhisperX model '{model}' for {vram_gb:.1f}GB VRAM "
            f"(requires ~{ModelSelector.WHISPER_MODEL_VRAM[model]}GB)"
        )
        return model

    @staticmethod
    def calculate_optimal_settings(
        vram_gb: float,
        user_model: str = "auto",
        enable_diarization: bool = True,
    ) -> Dict[str, any]:
        """
        Calculate optimal transcription settings based on VRAM.

        Priority order for resource constraints:
        1. Drop concurrency (go sequential with concurrency=1)
        2. Reduce model size (medium → small → base → tiny)
        3. Last resort: disable diarization

        Args:
            vram_gb: Available VRAM in GB
            user_model: User's model preference
            enable_diarization: Whether diarization is requested

        Returns:
            Dict with optimal settings: {
                "model": str,
                "batch_size": int,
                "enable_diarization": bool,
                "max_concurrency": int,
                "reason": str
            }
        """
        # Select model
        model = ModelSelector.select_whisper_model(vram_gb, user_model)
        model_vram = ModelSelector.WHISPER_MODEL_VRAM[model]

        # Calculate required VRAM for single task
        single_task_vram = model_vram
        if enable_diarization:
            single_task_vram += ModelSelector.PYANNOTE_VRAM

        # Determine optimal settings
        settings_dict = {
            "model": model,
            "batch_size": ModelSelector.calculate_batch_size(vram_gb, model),
            "enable_diarization": enable_diarization,
            "max_concurrency": 1,
            "reason": "",
        }

        # Check if we can run parallel tasks
        if single_task_vram * 2 <= vram_gb - 1:  # -1GB buffer
            settings_dict["max_concurrency"] = min(
                4, int(vram_gb / single_task_vram)
            )
            settings_dict[
                "reason"
            ] = f"Sufficient VRAM for {settings_dict['max_concurrency']} parallel tasks"

        # Check if single task with diarization fits
        elif single_task_vram <= vram_gb - 1:
            settings_dict["max_concurrency"] = 1
            settings_dict["reason"] = (
                f"Sequential processing required (VRAM: {vram_gb:.1f}GB, "
                f"required: {single_task_vram:.1f}GB per task)"
            )

        # Try reducing model size if can't fit with diarization
        elif enable_diarization:
            # Try smaller models
            for smaller_model in ["small", "base", "tiny"]:
                smaller_vram = ModelSelector.WHISPER_MODEL_VRAM[smaller_model]
                if smaller_vram + ModelSelector.PYANNOTE_VRAM <= vram_gb - 1:
                    settings_dict["model"] = smaller_model
                    settings_dict["batch_size"] = ModelSelector.calculate_batch_size(
                        vram_gb, smaller_model
                    )
                    settings_dict["max_concurrency"] = 1
                    settings_dict[
                        "reason"
                    ] = f"Reduced model to '{smaller_model}' to fit with diarization"
                    logger.warning(
                        f"Reduced model from '{model}' to '{smaller_model}' "
                        f"to fit diarization in {vram_gb:.1f}GB VRAM"
                    )
                    break
            else:
                # Last resort: disable diarization
                settings_dict["enable_diarization"] = False
                settings_dict["reason"] = (
                    f"Disabled diarization - insufficient VRAM ({vram_gb:.1f}GB) "
                    f"even with smallest model"
                )
                logger.warning(
                    f"Insufficient VRAM ({vram_gb:.1f}GB) for diarization. "
                    "Disabling speaker diarization as last resort."
                )
        else:
            # Without diarization, check if model fits
            if model_vram <= vram_gb - 1:
                settings_dict["max_concurrency"] = 1
                settings_dict["reason"] = (
                    f"Sequential processing without diarization "
                    f"(VRAM: {vram_gb:.1f}GB)"
                )
            else:
                # Try smaller model
                for smaller_model in ["small", "base", "tiny"]:
                    smaller_vram = ModelSelector.WHISPER_MODEL_VRAM[smaller_model]
                    if smaller_vram <= vram_gb - 1:
                        settings_dict["model"] = smaller_model
                        settings_dict["batch_size"] = (
                            ModelSelector.calculate_batch_size(vram_gb, smaller_model)
                        )
                        settings_dict["max_concurrency"] = 1
                        settings_dict[
                            "reason"
                        ] = f"Reduced model to '{smaller_model}' to fit in VRAM"
                        logger.warning(
                            f"Reduced model from '{model}' to '{smaller_model}' "
                            f"to fit in {vram_gb:.1f}GB VRAM"
                        )
                        break

        logger.info(
            f"Optimal settings: model={settings_dict['model']}, "
            f"batch_size={settings_dict['batch_size']}, "
            f"diarization={settings_dict['enable_diarization']}, "
            f"max_concurrency={settings_dict['max_concurrency']}"
        )
        logger.info(f"Reason: {settings_dict['reason']}")

        return settings_dict

    @staticmethod
    def calculate_batch_size(vram_gb: float, model_size: str) -> int:
        """
        Calculate optimal batch size for WhisperX based on VRAM and model.

        Args:
            vram_gb: Available VRAM in GB
            model_size: Model name (tiny, base, small, medium, large)

        Returns:
            Optimal batch size
        """
        # Base batch sizes per model
        base_batch_sizes = {
            "tiny": 32,
            "base": 24,
            "small": 16,
            "medium": 12,
            "large": 8,
        }

        base_batch = base_batch_sizes.get(model_size, 16)

        # Scale based on available VRAM
        if vram_gb < 4:
            return max(4, base_batch // 4)
        elif vram_gb < 6:
            return max(8, base_batch // 2)
        elif vram_gb < 10:
            return base_batch
        else:
            return min(32, base_batch * 2)

    @staticmethod
    def get_recommended_worker_count(
        vram_gb: float, model: str, enable_diarization: bool = True
    ) -> int:
        """
        Get recommended Celery worker concurrency for autoscaling.

        Args:
            vram_gb: Available VRAM in GB
            model: WhisperX model name
            enable_diarization: Whether diarization is enabled

        Returns:
            Recommended max worker count for autoscaling
        """
        settings = ModelSelector.calculate_optimal_settings(
            vram_gb, model, enable_diarization
        )
        return settings["max_concurrency"]
