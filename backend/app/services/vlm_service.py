"""
Vision Language Model (VLM) Service

Manages Qwen2.5-VL-7B-Instruct for visual analysis of images and video frames.
Handles lazy loading, GPU memory management, and provides specialized methods
for image captioning, object detection, meme classification, and more.

Features:
- Lazy loading with singleton pattern
- 4-bit quantization for efficient GPU memory usage
- Shared GPU memory with WhisperX and Pyannote models
- Multiple analysis modes: captioning, object detection, meme classification
- Support for PIL Images and file paths
- Automatic image resizing for large images
- Comprehensive error handling and logging
"""

import gc
import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
from PIL import Image
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from transformers import BitsAndBytesConfig

from app.services.device_manager import get_device_manager

logger = logging.getLogger(__name__)


class VLMManager:
    """
    Manager for Vision Language Model operations.

    Provides lazy-loaded access to Qwen2.5-VL-7B-Instruct model with 4-bit quantization
    for efficient GPU memory usage. Supports various image analysis tasks including
    captioning, object detection, meme classification, and video frame analysis.

    Usage:
        ```python
        # Get singleton instance
        vlm = get_vlm_manager()

        # Generate caption for search indexing
        caption = vlm.generate_caption("path/to/image.jpg")

        # Detect objects in image
        objects = vlm.extract_objects("path/to/image.png")

        # Check if image is a meme
        is_meme = vlm.classify_meme(image_path)

        # Custom analysis
        result = vlm.analyze_image(
            image_path,
            prompt="Describe the legal document shown in this image"
        )

        # Clean up GPU memory when done
        vlm.cleanup()
        ```

    Attributes:
        model_name: HuggingFace model identifier
        max_image_size: Maximum dimension (width/height) before resizing
        device: PyTorch device string ('cuda' or 'cpu')
    """

    # Default model configuration
    DEFAULT_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"
    MAX_IMAGE_SIZE = 1024  # Resize images larger than this

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        max_image_size: int = MAX_IMAGE_SIZE,
        load_on_init: bool = False
    ):
        """
        Initialize VLM Manager.

        Args:
            model_name: HuggingFace model identifier
            max_image_size: Maximum dimension before resizing (default: 1024)
            load_on_init: Load model immediately instead of lazy loading
        """
        self.model_name = model_name
        self.max_image_size = max_image_size

        # Model components (lazy loaded)
        self._model: Optional[Qwen2VLForConditionalGeneration] = None
        self._processor: Optional[AutoProcessor] = None

        # Device detection
        device_manager = get_device_manager()
        self.device = device_manager.get_device_string()
        self._has_gpu = device_manager.has_gpu

        logger.info(f"VLMManager initialized with device: {self.device}")
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Max image size: {self.max_image_size}px")

        if load_on_init:
            self.load_model()

    @property
    def is_loaded(self) -> bool:
        """Check if model is currently loaded in memory."""
        return self._model is not None and self._processor is not None

    def load_model(self) -> None:
        """
        Load Qwen2.5-VL model with 4-bit quantization.

        Loads the model with BitsAndBytes 4-bit quantization for efficient
        GPU memory usage. Falls back to CPU if CUDA is not available.

        Raises:
            RuntimeError: If model loading fails
        """
        if self.is_loaded:
            logger.debug("VLM model already loaded, skipping")
            return

        logger.info(f"Loading VLM model: {self.model_name}")

        try:
            # Configure 4-bit quantization for GPU efficiency
            quantization_config = None
            if self._has_gpu:
                logger.info("Configuring 4-bit quantization for GPU")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
            else:
                logger.warning("GPU not available, loading on CPU (slower)")

            # Load processor
            logger.info("Loading processor...")
            self._processor = AutoProcessor.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )

            # Load model with quantization
            logger.info("Loading model with quantization...")
            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_name,
                quantization_config=quantization_config if self._has_gpu else None,
                device_map="auto" if self._has_gpu else "cpu",
                trust_remote_code=True,
                torch_dtype=torch.float16 if self._has_gpu else torch.float32,
            )

            # Set model to evaluation mode
            self._model.eval()

            logger.info(f"VLM model loaded successfully on {self.device}")

            # Log memory usage if on GPU
            if self._has_gpu and torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024**3
                reserved = torch.cuda.memory_reserved() / 1024**3
                logger.info(f"GPU Memory - Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB")

        except Exception as e:
            logger.error(f"Failed to load VLM model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load VLM model: {e}")

    def _ensure_loaded(self) -> None:
        """Ensure model is loaded before use (lazy loading)."""
        if not self.is_loaded:
            self.load_model()

    def _load_image(self, image: Union[str, Path, Image.Image]) -> Image.Image:
        """
        Load and prepare image from various input types.

        Args:
            image: Path to image file or PIL Image object

        Returns:
            PIL Image object (RGB mode)

        Raises:
            ValueError: If image cannot be loaded
            FileNotFoundError: If image file doesn't exist
        """
        try:
            # Handle PIL Image
            if isinstance(image, Image.Image):
                pil_image = image
            # Handle path-like objects
            elif isinstance(image, (str, Path)):
                image_path = Path(image)
                if not image_path.exists():
                    raise FileNotFoundError(f"Image file not found: {image_path}")
                pil_image = Image.open(image_path)
            else:
                raise ValueError(f"Unsupported image type: {type(image)}")

            # Convert to RGB if necessary
            if pil_image.mode != "RGB":
                logger.debug(f"Converting image from {pil_image.mode} to RGB")
                pil_image = pil_image.convert("RGB")

            # Resize if too large
            width, height = pil_image.size
            max_dim = max(width, height)
            if max_dim > self.max_image_size:
                scale = self.max_image_size / max_dim
                new_width = int(width * scale)
                new_height = int(height * scale)
                logger.debug(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            return pil_image

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error loading image: {e}", exc_info=True)
            raise ValueError(f"Failed to load image: {e}")

    def analyze_image(
        self,
        image: Union[str, Path, Image.Image],
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7
    ) -> str:
        """
        Analyze image with custom prompt.

        Main analysis method that accepts any prompt for flexible image analysis.
        Other methods are specialized wrappers around this method.

        Args:
            image: Path to image or PIL Image object
            prompt: Text prompt describing what to analyze
            max_new_tokens: Maximum tokens to generate (default: 512)
            temperature: Sampling temperature (default: 0.7, lower = more deterministic)

        Returns:
            Generated text response

        Raises:
            ValueError: If image loading fails
            RuntimeError: If model inference fails

        Example:
            ```python
            result = vlm.analyze_image(
                "document.jpg",
                "What type of legal document is this?"
            )
            ```
        """
        self._ensure_loaded()

        try:
            # Load and prepare image
            pil_image = self._load_image(image)

            # Prepare conversation format (Qwen2.5-VL uses chat format)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]

            # Apply chat template
            text = self._processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            # Process inputs
            inputs = self._processor(
                text=[text],
                images=[pil_image],
                return_tensors="pt",
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate response
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    pad_token_id=self._processor.tokenizer.pad_token_id,
                    eos_token_id=self._processor.tokenizer.eos_token_id
                )

            # Decode response
            generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
            response = self._processor.decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )

            logger.debug(f"VLM analysis complete. Response length: {len(response)} chars")
            return response.strip()

        except Exception as e:
            logger.error(f"Error during image analysis: {e}", exc_info=True)
            raise RuntimeError(f"Image analysis failed: {e}")

    def generate_caption(
        self,
        image: Union[str, Path, Image.Image],
        max_length: int = 200
    ) -> str:
        """
        Generate descriptive caption for image search indexing.

        Creates a detailed, searchable description of the image content.
        Optimized for search and retrieval use cases.

        Args:
            image: Path to image or PIL Image object
            max_length: Maximum caption length in tokens

        Returns:
            Descriptive caption text

        Example:
            ```python
            caption = vlm.generate_caption("evidence_photo.jpg")
            # "A photograph of a black sedan with visible damage to the front bumper..."
            ```
        """
        prompt = (
            "Generate a detailed, descriptive caption for this image. "
            "Focus on key visual elements, objects, people, text, settings, and any notable details. "
            "Make the description clear and searchable."
        )

        return self.analyze_image(
            image,
            prompt,
            max_new_tokens=max_length,
            temperature=0.5  # Lower temperature for more focused captions
        )

    def extract_objects(
        self,
        image: Union[str, Path, Image.Image]
    ) -> List[str]:
        """
        Detect and list objects/entities visible in the image.

        Identifies key objects, people, text, and other entities present
        in the image. Returns a list of detected items.

        Args:
            image: Path to image or PIL Image object

        Returns:
            List of detected objects/entities

        Example:
            ```python
            objects = vlm.extract_objects("crime_scene.jpg")
            # ["car", "person", "road sign", "traffic light"]
            ```
        """
        prompt = (
            "List all visible objects, people, text, and entities in this image. "
            "Provide a comma-separated list of items. Be specific and comprehensive."
        )

        response = self.analyze_image(
            image,
            prompt,
            max_new_tokens=300,
            temperature=0.3  # Very low temperature for consistent object detection
        )

        # Parse comma-separated list
        objects = [obj.strip() for obj in response.split(",")]
        objects = [obj for obj in objects if obj]  # Remove empty strings

        return objects

    def classify_meme(
        self,
        image: Union[str, Path, Image.Image]
    ) -> Dict[str, Any]:
        """
        Detect if image is a meme and extract context.

        Classifies whether the image is a meme, and if so, attempts to
        identify the meme template and extract the text/message.

        Args:
            image: Path to image or PIL Image object

        Returns:
            Dictionary with classification results:
            - is_meme: bool
            - confidence: str (high/medium/low)
            - template: Optional[str] - Meme template name if recognized
            - text: Optional[str] - Text content of meme
            - description: str - Brief description

        Example:
            ```python
            result = vlm.classify_meme("funny_image.jpg")
            # {
            #   "is_meme": True,
            #   "confidence": "high",
            #   "template": "Distracted Boyfriend",
            #   "text": "...",
            #   "description": "..."
            # }
            ```
        """
        prompt = (
            "Analyze this image and determine if it's a meme. "
            "Respond in this format:\n"
            "IS_MEME: yes/no\n"
            "CONFIDENCE: high/medium/low\n"
            "TEMPLATE: [meme template name if recognized, or 'unknown']\n"
            "TEXT: [text content in the meme, if any]\n"
            "DESCRIPTION: [brief description of the meme or image]"
        )

        response = self.analyze_image(
            image,
            prompt,
            max_new_tokens=300,
            temperature=0.3
        )

        # Parse structured response
        lines = response.split("\n")
        result: Dict[str, Any] = {
            "is_meme": False,
            "confidence": "low",
            "template": None,
            "text": None,
            "description": ""
        }

        for line in lines:
            line = line.strip()
            if line.startswith("IS_MEME:"):
                is_meme_str = line.split(":", 1)[1].strip().lower()
                result["is_meme"] = is_meme_str == "yes"
            elif line.startswith("CONFIDENCE:"):
                result["confidence"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("TEMPLATE:"):
                template = line.split(":", 1)[1].strip()
                result["template"] = template if template.lower() != "unknown" else None
            elif line.startswith("TEXT:"):
                text = line.split(":", 1)[1].strip()
                result["text"] = text if text else None
            elif line.startswith("DESCRIPTION:"):
                result["description"] = line.split(":", 1)[1].strip()

        return result

    def analyze_video_frame(
        self,
        frame: Union[Image.Image, str, Path],
        context: Optional[str] = None
    ) -> str:
        """
        Analyze a video frame with optional context.

        Specialized method for analyzing individual frames extracted from videos.
        Can incorporate temporal context from previous frames.

        Args:
            frame: PIL Image of video frame or path to frame
            context: Optional context about previous frames or video content

        Returns:
            Description of frame content

        Example:
            ```python
            description = vlm.analyze_video_frame(
                frame_image,
                context="This is from a security camera recording at 2:30 PM"
            )
            ```
        """
        base_prompt = "Describe what's happening in this video frame. Focus on actions, people, objects, and any notable events."

        if context:
            prompt = f"{base_prompt}\n\nContext: {context}"
        else:
            prompt = base_prompt

        return self.analyze_image(
            frame,
            prompt,
            max_new_tokens=300,
            temperature=0.6
        )

    def extract_document_text(
        self,
        image: Union[str, Path, Image.Image]
    ) -> str:
        """
        Extract and transcribe text from document images.

        Specialized OCR-like functionality for extracting text content
        from images of documents, forms, receipts, etc.

        Args:
            image: Path to image or PIL Image object

        Returns:
            Extracted text content

        Example:
            ```python
            text = vlm.extract_document_text("scanned_contract.jpg")
            ```
        """
        prompt = (
            "Extract and transcribe ALL text visible in this image. "
            "Preserve the structure and formatting as much as possible. "
            "Include all text, even small print or watermarks."
        )

        return self.analyze_image(
            image,
            prompt,
            max_new_tokens=1024,  # Longer for document text
            temperature=0.1  # Very low for accurate transcription
        )

    def analyze_batch(
        self,
        images: List[Union[str, Path, Image.Image]],
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7
    ) -> List[str]:
        """
        Analyze multiple images with the same prompt.

        Processes a batch of images sequentially. Note: This doesn't use
        true batch inference - images are processed one at a time.

        Args:
            images: List of image paths or PIL Images
            prompt: Prompt to use for all images
            max_new_tokens: Maximum tokens per response
            temperature: Sampling temperature

        Returns:
            List of responses, one per image

        Example:
            ```python
            descriptions = vlm.analyze_batch(
                ["img1.jpg", "img2.jpg", "img3.jpg"],
                "Describe this image in detail"
            )
            ```
        """
        self._ensure_loaded()

        results = []
        for idx, image in enumerate(images):
            try:
                logger.debug(f"Processing image {idx + 1}/{len(images)}")
                result = self.analyze_image(
                    image,
                    prompt,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing image {idx + 1}: {e}")
                results.append(f"Error: {str(e)}")

        return results

    def cleanup(self) -> None:
        """
        Release GPU memory and cleanup model resources.

        Unloads the model from memory and runs garbage collection.
        Useful for freeing GPU memory when sharing with other models
        like WhisperX or Pyannote.

        Example:
            ```python
            vlm = get_vlm_manager()
            # ... use VLM for analysis ...
            vlm.cleanup()  # Free GPU memory for other models
            ```
        """
        if not self.is_loaded:
            logger.debug("VLM model not loaded, nothing to cleanup")
            return

        logger.info("Cleaning up VLM model and releasing GPU memory")

        # Delete model and processor
        del self._model
        del self._processor
        self._model = None
        self._processor = None

        # Force garbage collection
        gc.collect()

        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("CUDA cache cleared")

        logger.info("VLM cleanup complete")

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the VLM configuration.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "is_loaded": self.is_loaded,
            "device": self.device,
            "has_gpu": self._has_gpu,
            "max_image_size": self.max_image_size,
            "gpu_memory_allocated_gb": (
                torch.cuda.memory_allocated() / 1024**3
                if self._has_gpu and torch.cuda.is_available()
                else 0.0
            ),
            "gpu_memory_reserved_gb": (
                torch.cuda.memory_reserved() / 1024**3
                if self._has_gpu and torch.cuda.is_available()
                else 0.0
            ),
        }


# Global singleton instance
_vlm_manager: Optional[VLMManager] = None


def get_vlm_manager(
    model_name: str = VLMManager.DEFAULT_MODEL,
    max_image_size: int = VLMManager.MAX_IMAGE_SIZE
) -> VLMManager:
    """
    Get or create singleton VLMManager instance.

    Args:
        model_name: HuggingFace model identifier (default: Qwen2.5-VL-7B-Instruct)
        max_image_size: Maximum image dimension before resizing

    Returns:
        VLMManager singleton instance

    Example:
        ```python
        from app.services.vlm_service import get_vlm_manager

        vlm = get_vlm_manager()
        caption = vlm.generate_caption("image.jpg")
        ```
    """
    global _vlm_manager

    if _vlm_manager is None:
        _vlm_manager = VLMManager(
            model_name=model_name,
            max_image_size=max_image_size,
            load_on_init=False  # Lazy load by default
        )
        logger.info("Created VLMManager singleton")

    return _vlm_manager


def reset_vlm_manager() -> None:
    """
    Reset singleton instance (mainly for testing).

    Cleans up existing instance and resets to None.
    """
    global _vlm_manager

    if _vlm_manager is not None:
        _vlm_manager.cleanup()
        _vlm_manager = None
        logger.info("VLMManager singleton reset")
