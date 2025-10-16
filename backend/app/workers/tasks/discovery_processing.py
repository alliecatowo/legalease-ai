"""
Discovery Processing Tasks

Celery tasks for processing discovery items with visual analysis.
Handles photos, videos, and frame extraction with VLM integration.
"""
import os
import json
import logging
import tempfile
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from io import BytesIO
from PIL import Image
import base64

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.minio_client import minio_client
from app.models.discovery_item import DiscoveryItem
from app.models.visual_content import VisualContent
from app.models.video_summary import VideoSummary

logger = logging.getLogger(__name__)


class DiscoveryProcessingError(Exception):
    """Custom exception for discovery processing errors."""
    pass


class VLMService:
    """Handles Vision Language Model (VLM) operations using Ollama."""

    def __init__(self, model_name: str = "llava:latest", ollama_url: str = None):
        self.available_models = None
        """
        Initialize VLM service.

        Args:
            model_name: Name of the Ollama vision model to use
            ollama_url: Ollama API URL (defaults to environment variable or localhost)
        """
        self.model_name = model_name
        self.ollama_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        format_json: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze an image using VLM.

        Args:
            image_path: Path to the image file
            prompt: Analysis prompt for the VLM
            format_json: Whether to request JSON formatted response

        Returns:
            Dict containing the analysis results
        """
        try:
            import httpx

            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Prepare request
            request_data = {
                "model": self.model_name,
                "prompt": prompt,
                "images": [image_data],
                "stream": False,
            }

            if format_json:
                request_data["format"] = "json"

            # Call Ollama API
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.ollama_url}/api/generate",
                    json=request_data
                )

                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '')

                    if format_json:
                        try:
                            return json.loads(response_text)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON response, returning raw text")
                            return {'raw_response': response_text}
                    else:
                        return {'response': response_text}
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    raise Exception(f"VLM API error: {response.status_code}")

        except Exception as e:
            logger.error(f"VLM analysis failed: {e}", exc_info=True)
            raise Exception(f"VLM analysis failed: {str(e)}")

    def generate_caption(self, image_path: str) -> str:
        """
        Generate a descriptive caption for an image.

        Args:
            image_path: Path to the image file

        Returns:
            Generated caption text
        """
        prompt = """Provide a detailed, objective description of this image.
Include what you see, the setting, any people or objects, actions occurring, and any text visible.
Be comprehensive but concise. This is for legal discovery documentation."""

        result = self.analyze_image(image_path, prompt)
        return result.get('response', '')

    def detect_objects_and_scenes(self, image_path: str) -> Dict[str, Any]:
        """
        Detect objects, scenes, and activities in an image.

        Args:
            image_path: Path to the image file

        Returns:
            Dict with detected objects, scenes, and activities
        """
        prompt = """Analyze this image and identify:
1. Objects: List all significant objects visible
2. Scene: Describe the location/setting type
3. Activities: List any actions or activities occurring
4. People: Note if people are present and what they're doing
5. Text: Identify any visible text or signage

Return as JSON with keys: objects (array), scene (string), activities (array), people_present (boolean), people_description (string), visible_text (string)"""

        result = self.analyze_image(image_path, prompt, format_json=True)

        # Ensure expected structure
        return {
            'objects': result.get('objects', []),
            'scene': result.get('scene', ''),
            'activities': result.get('activities', []),
            'people_present': result.get('people_present', False),
            'people_description': result.get('people_description', ''),
            'visible_text': result.get('visible_text', '')
        }

    def classify_meme(self, image_path: str) -> Tuple[bool, float, str]:
        """
        Classify whether an image is a meme.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (is_meme, confidence, explanation)
        """
        prompt = """Determine if this image is a meme or meme-style content.
Consider: text overlays, recognizable meme formats, humorous intent, viral content patterns.

Return JSON with:
- is_meme (boolean): true if this is a meme
- confidence (float): 0.0 to 1.0 confidence score
- explanation (string): brief reasoning"""

        result = self.analyze_image(image_path, prompt, format_json=True)

        is_meme = result.get('is_meme', False)
        confidence = result.get('confidence', 0.0)
        explanation = result.get('explanation', '')

        return is_meme, confidence, explanation

    def detect_sensitive_content(self, image_path: str) -> Dict[str, Any]:
        """
        Detect potentially sensitive or explicit content.

        Args:
            image_path: Path to the image file

        Returns:
            Dict with sensitivity flags and descriptions
        """
        prompt = """Analyze this image for sensitive content including:
- Explicit/adult content
- Violence or weapons
- Drug-related content
- Illegal activities
- Personal information visible

Return JSON with:
- has_sensitive_content (boolean)
- flags (array of strings): types of sensitive content detected
- severity (string): "none", "low", "medium", "high"
- description (string): brief explanation"""

        result = self.analyze_image(image_path, prompt, format_json=True)

        return {
            'has_sensitive_content': result.get('has_sensitive_content', False),
            'flags': result.get('flags', []),
            'severity': result.get('severity', 'none'),
            'description': result.get('description', '')
        }

    def cleanup(self):
        """Cleanup resources (placeholder for future implementations)."""
        pass


class VideoProcessor:
    """Handles video processing operations."""

    @staticmethod
    def get_video_metadata(video_path: str) -> Dict[str, Any]:
        """
        Extract video metadata using FFprobe.

        Args:
            video_path: Path to video file

        Returns:
            Dict containing video metadata
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode == 0:
                metadata = json.loads(result.stdout.decode('utf-8'))

                # Extract relevant information
                video_stream = next(
                    (s for s in metadata.get('streams', []) if s.get('codec_type') == 'video'),
                    None
                )

                if video_stream:
                    return {
                        'duration': float(metadata.get('format', {}).get('duration', 0)),
                        'width': video_stream.get('width', 0),
                        'height': video_stream.get('height', 0),
                        'fps': eval(video_stream.get('r_frame_rate', '0/1')),  # e.g., "30/1" -> 30.0
                        'codec': video_stream.get('codec_name', ''),
                        'bitrate': int(metadata.get('format', {}).get('bit_rate', 0))
                    }

            return {}

        except Exception as e:
            logger.warning(f"Failed to extract video metadata: {e}")
            return {}

    @staticmethod
    def extract_frame(
        video_path: str,
        timestamp: float,
        output_path: str
    ) -> bool:
        """
        Extract a single frame from video at specified timestamp.

        Args:
            video_path: Path to video file
            timestamp: Time in seconds to extract frame
            output_path: Path to save extracted frame

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',  # High quality
                '-y',  # Overwrite
                output_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception as e:
            logger.error(f"Failed to extract frame at {timestamp}s: {e}")
            return False


@celery_app.task(name="process_discovery_photo", bind=True)
def process_discovery_photo(self, discovery_item_id: int) -> Dict[str, Any]:
    """
    Process a photo discovery item with VLM analysis.

    Pipeline:
    1. Download image from MinIO
    2. Generate VLM caption
    3. Detect objects, scenes, activities
    4. Classify if meme
    5. Detect sensitive content
    6. Create VisualContent record
    7. Update DiscoveryItem.processed = True

    Args:
        discovery_item_id: ID of the discovery item to process

    Returns:
        Dict containing processing status and results
    """
    db = SessionLocal()
    vlm = None
    temp_dir = None

    try:
        # Update task state
        self.update_state(
            state='STARTED',
            meta={'status': 'Initializing photo processing', 'progress': 0}
        )

        # Step 1: Get discovery item from database
        logger.info(f"Starting photo processing for discovery item {discovery_item_id}")
        item = db.query(DiscoveryItem).filter(DiscoveryItem.id == discovery_item_id).first()

        if not item:
            raise Exception(f"Discovery item {discovery_item_id} not found")

        # Step 2: Download image from MinIO
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Downloading image from storage', 'progress': 10}
        )

        logger.info(f"Downloading image from MinIO: {item.file_path}")
        image_data = minio_client.download_file(item.file_path)

        if not image_data:
            raise Exception("Failed to download image from MinIO")

        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='discovery_photo_')
        image_path = os.path.join(temp_dir, 'image.jpg')

        # Save image
        with open(image_path, 'wb') as f:
            f.write(image_data)

        # Step 3: Initialize VLM service
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Initializing vision model', 'progress': 20}
        )

        vlm = VLMService()

        # Step 4: Generate caption
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Generating image caption', 'progress': 30}
        )

        logger.info("Generating VLM caption")
        caption = vlm.generate_caption(image_path)

        # Step 5: Detect objects and scenes
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Detecting objects and scenes', 'progress': 50}
        )

        logger.info("Detecting objects and scenes")
        detection_results = vlm.detect_objects_and_scenes(image_path)

        # Step 6: Classify if meme
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Classifying content type', 'progress': 70}
        )

        logger.info("Classifying meme status")
        is_meme, meme_confidence, meme_explanation = vlm.classify_meme(image_path)

        # Step 7: Detect sensitive content
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Scanning for sensitive content', 'progress': 80}
        )

        logger.info("Detecting sensitive content")
        sensitive_flags = vlm.detect_sensitive_content(image_path)
        sensitive_results = vlm.detect_sensitive_content(image_path)

        # Step 8: Create VisualContent record
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Saving analysis results', 'progress': 90}
        )

        logger.info("Creating VisualContent record")
        visual_content = VisualContent(
            discovery_item_id=discovery_item_id,
            frame_number=None,  # NULL for photos
            timestamp_in_video=None,  # NULL for photos
            vlm_caption=caption,
            detected_objects=detection_results.get('objects', []),
            detected_scenes=[detection_results.get('scene', '')] if detection_results.get('scene') else [],
            detected_activities=detection_results.get('activities', []),
            sensitive_flags=sensitive_results,
            is_meme=is_meme
        )

        db.add(visual_content)

        # Step 9: Update DiscoveryItem.processed = True
        item.processed = True
        item.item_metadata = item.item_metadata or {}
        item.item_metadata['visual_analysis'] = {
            'processed_at': datetime.utcnow().isoformat(),
            'meme_classification': {
                'is_meme': is_meme,
                'confidence': meme_confidence,
                'explanation': meme_explanation
            },
            'has_sensitive_content': sensitive_results.get('has_sensitive_content', False),
            'sensitivity_severity': sensitive_results.get('severity', 'none')
        }

        db.commit()

        logger.info(f"Photo processing completed successfully for discovery item {discovery_item_id}")

        return {
            'status': 'completed',
            'discovery_item_id': discovery_item_id,
            'visual_content_id': visual_content.id,
            'caption': caption,
            'is_meme': is_meme,
            'has_sensitive_content': sensitive_results.get('has_sensitive_content', False),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Photo processing failed for discovery item {discovery_item_id}: {str(e)}", exc_info=True)

        # Update item to mark processing attempt
        try:
            item = db.query(DiscoveryItem).filter(DiscoveryItem.id == discovery_item_id).first()
            if item:
                item.item_metadata = item.item_metadata or {}
                item.item_metadata['processing_error'] = {
                    'error': str(e),
                    'failed_at': datetime.utcnow().isoformat()
                }
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update item metadata: {str(db_error)}")

        self.update_state(
            state='FAILURE',
            meta={'status': f'Processing failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'discovery_item_id': discovery_item_id,
            'task_id': self.request.id
        }

    finally:
        # Cleanup
        if vlm:
            vlm.cleanup()
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")
        db.close()


@celery_app.task(name="process_discovery_video", bind=True)
def process_discovery_video(self, discovery_item_id: int) -> Dict[str, Any]:
    """
    Process a video discovery item with comprehensive analysis.

    Pipeline:
    1. Download video from MinIO
    2. Extract video metadata (duration, fps, resolution)
    3. Trigger frame extraction task
    4. Wait for frame analysis completion
    5. Generate comprehensive video summary from frame analyses
    6. Create VideoSummary record
    7. Update DiscoveryItem.processed = True

    Args:
        discovery_item_id: ID of the discovery item to process

    Returns:
        Dict containing processing status and results
    """
    db = SessionLocal()
    temp_dir = None

    try:
        # Update task state
        self.update_state(
            state='STARTED',
            meta={'status': 'Initializing video processing', 'progress': 0}
        )

        # Step 1: Get discovery item from database
        logger.info(f"Starting video processing for discovery item {discovery_item_id}")
        item = db.query(DiscoveryItem).filter(DiscoveryItem.id == discovery_item_id).first()

        if not item:
            raise Exception(f"Discovery item {discovery_item_id} not found")

        # Step 2: Download video from MinIO
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Downloading video from storage', 'progress': 10}
        )

        logger.info(f"Downloading video from MinIO: {item.file_path}")
        video_data = minio_client.download_file(item.file_path)

        if not video_data:
            raise Exception("Failed to download video from MinIO")

        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='discovery_video_')
        video_path = os.path.join(temp_dir, 'video.mp4')

        # Save video
        with open(video_path, 'wb') as f:
            f.write(video_data)

        # Step 3: Extract video metadata
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Extracting video metadata', 'progress': 20}
        )

        logger.info("Extracting video metadata")
        processor = VideoProcessor()
        metadata = processor.get_video_metadata(video_path)

        duration = metadata.get('duration', 0)
        fps = metadata.get('fps', 30)

        logger.info(f"Video metadata: duration={duration}s, fps={fps}, resolution={metadata.get('width')}x{metadata.get('height')}")

        # Step 4: Trigger frame extraction
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Extracting video frames', 'progress': 30}
        )

        logger.info("Triggering frame extraction task")
        frame_task = extract_video_frames.delay(discovery_item_id)

        # Wait for frame extraction to complete
        frame_result = frame_task.get(timeout=600)  # 10 minute timeout

        if frame_result['status'] != 'completed':
            raise Exception("Frame extraction failed")

        # Step 5: Get all frame analyses
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Generating video summary', 'progress': 80}
        )

        logger.info("Retrieving frame analyses for summary generation")
        frame_analyses = db.query(VisualContent).filter(
            VisualContent.discovery_item_id == discovery_item_id
        ).order_by(VisualContent.timestamp_in_video).all()

        # Generate comprehensive summary
        comprehensive_summary = _generate_video_summary(frame_analyses, metadata)
        key_moments = _extract_key_moments(frame_analyses)
        visual_summary = _generate_visual_summary(frame_analyses)

        # Step 6: Create VideoSummary record
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Saving video summary', 'progress': 90}
        )

        logger.info("Creating VideoSummary record")
        video_summary = VideoSummary(
            discovery_item_id=discovery_item_id,
            comprehensive_summary=comprehensive_summary,
            key_moments=key_moments,
            visual_summary=visual_summary,
            audio_summary=None,  # TODO: Implement audio analysis
            importance_score=_calculate_importance_score(frame_analyses),
            flagged_content=_extract_flagged_content(frame_analyses)
        )

        db.add(video_summary)

        # Step 7: Update DiscoveryItem.processed = True
        item.processed = True
        item.item_metadata = item.item_metadata or {}
        item.item_metadata['video_analysis'] = {
            'processed_at': datetime.utcnow().isoformat(),
            'duration': duration,
            'fps': fps,
            'resolution': f"{metadata.get('width')}x{metadata.get('height')}",
            'frames_analyzed': len(frame_analyses),
            'importance_score': video_summary.importance_score
        }

        db.commit()

        logger.info(f"Video processing completed successfully for discovery item {discovery_item_id}")

        return {
            'status': 'completed',
            'discovery_item_id': discovery_item_id,
            'video_summary_id': video_summary.id,
            'frames_analyzed': len(frame_analyses),
            'duration': duration,
            'importance_score': video_summary.importance_score,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Video processing failed for discovery item {discovery_item_id}: {str(e)}", exc_info=True)

        # Update item to mark processing attempt
        try:
            item = db.query(DiscoveryItem).filter(DiscoveryItem.id == discovery_item_id).first()
            if item:
                item.item_metadata = item.item_metadata or {}
                item.item_metadata['processing_error'] = {
                    'error': str(e),
                    'failed_at': datetime.utcnow().isoformat()
                }
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update item metadata: {str(db_error)}")

        self.update_state(
            state='FAILURE',
            meta={'status': f'Processing failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'discovery_item_id': discovery_item_id,
            'task_id': self.request.id
        }

    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")
        db.close()


@celery_app.task(name="extract_video_frames", bind=True)
def extract_video_frames(self, discovery_item_id: int) -> Dict[str, Any]:
    """
    Extract frames from video at regular intervals and analyze each frame.

    Pipeline:
    1. Download video from MinIO
    2. Extract frames at intervals (e.g., every 5 seconds)
    3. Save frames temporarily
    4. Trigger analyze_video_frame for each frame
    5. Report progress

    Args:
        discovery_item_id: ID of the discovery item to process

    Returns:
        Dict containing extraction status and frame count
    """
    db = SessionLocal()
    temp_dir = None

    try:
        # Update task state
        self.update_state(
            state='STARTED',
            meta={'status': 'Initializing frame extraction', 'progress': 0}
        )

        # Step 1: Get discovery item
        logger.info(f"Starting frame extraction for discovery item {discovery_item_id}")
        item = db.query(DiscoveryItem).filter(DiscoveryItem.id == discovery_item_id).first()

        if not item:
            raise Exception(f"Discovery item {discovery_item_id} not found")

        # Step 2: Download video
        logger.info(f"Downloading video from MinIO: {item.file_path}")
        video_data = minio_client.download_file(item.file_path)

        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='video_frames_')
        video_path = os.path.join(temp_dir, 'video.mp4')

        with open(video_path, 'wb') as f:
            f.write(video_data)

        # Step 3: Get video metadata
        processor = VideoProcessor()
        metadata = processor.get_video_metadata(video_path)
        duration = metadata.get('duration', 0)

        # Step 4: Extract frames at intervals
        frame_interval = 5.0  # Extract frame every 5 seconds
        timestamps = []
        current_time = 0.0

        while current_time < duration:
            timestamps.append(current_time)
            current_time += frame_interval

        logger.info(f"Extracting {len(timestamps)} frames from {duration}s video")

        # Extract and analyze frames
        frame_tasks = []
        for idx, timestamp in enumerate(timestamps):
            # Update progress
            progress = int(10 + (idx / len(timestamps)) * 80)
            self.update_state(
                state='PROCESSING',
                meta={
                    'status': f'Extracting frame {idx + 1}/{len(timestamps)}',
                    'progress': progress
                }
            )

            # Extract frame
            frame_path = os.path.join(temp_dir, f'frame_{idx:04d}.jpg')
            success = processor.extract_frame(video_path, timestamp, frame_path)

            if success:
                # Read frame data
                with open(frame_path, 'rb') as f:
                    frame_data = f.read()

                # Trigger analysis task
                task = analyze_video_frame.delay(
                    discovery_item_id,
                    idx,
                    timestamp,
                    frame_data
                )
                frame_tasks.append(task)
                logger.info(f"Queued analysis for frame {idx} at {timestamp}s")

        # Wait for all frame analyses to complete
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Waiting for frame analyses', 'progress': 90}
        )

        for task in frame_tasks:
            task.get(timeout=120)  # 2 minute timeout per frame

        logger.info(f"Frame extraction completed: {len(frame_tasks)} frames processed")

        return {
            'status': 'completed',
            'discovery_item_id': discovery_item_id,
            'frames_extracted': len(frame_tasks),
            'duration': duration,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Frame extraction failed: {str(e)}", exc_info=True)

        self.update_state(
            state='FAILURE',
            meta={'status': f'Frame extraction failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'discovery_item_id': discovery_item_id,
            'task_id': self.request.id
        }

    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")
        db.close()


@celery_app.task(name="analyze_video_frame", bind=True)
def analyze_video_frame(
    self,
    discovery_item_id: int,
    frame_number: int,
    timestamp: float,
    frame_data: bytes
) -> Dict[str, Any]:
    """
    Analyze a single video frame with VLM.

    Pipeline:
    1. Save frame data to temporary file
    2. Analyze with VLM
    3. Create VisualContent record for the frame
    4. Return analysis results

    Args:
        discovery_item_id: ID of the discovery item
        frame_number: Frame sequence number
        timestamp: Timestamp in video (seconds)
        frame_data: Raw frame image data

    Returns:
        Dict containing analysis results
    """
    db = SessionLocal()
    vlm = None
    temp_dir = None

    try:
        # Update task state
        self.update_state(
            state='STARTED',
            meta={'status': f'Analyzing frame {frame_number}', 'progress': 0}
        )

        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='frame_analysis_')
        frame_path = os.path.join(temp_dir, f'frame_{frame_number}.jpg')

        # Save frame
        with open(frame_path, 'wb') as f:
            f.write(frame_data)

        # Initialize VLM
        vlm = VLMService()

        # Analyze frame
        self.update_state(
            state='PROCESSING',
            meta={'status': f'Analyzing frame {frame_number}', 'progress': 50}
        )

        caption = vlm.generate_caption(frame_path)
        detection_results = vlm.detect_objects_and_scenes(frame_path)
        sensitive_results = vlm.detect_sensitive_content(frame_path)

        # Create VisualContent record
        visual_content = VisualContent(
            discovery_item_id=discovery_item_id,
            frame_number=frame_number,
            timestamp_in_video=timestamp,
            vlm_caption=caption,
            detected_objects=detection_results.get('objects', []),
            detected_scenes=[detection_results.get('scene', '')] if detection_results.get('scene') else [],
            detected_activities=detection_results.get('activities', []),
            sensitive_flags=sensitive_results,
            is_meme=False  # Video frames typically not memes
        )

        db.add(visual_content)
        db.commit()

        logger.info(f"Frame {frame_number} analysis completed")

        return {
            'status': 'completed',
            'frame_number': frame_number,
            'timestamp': timestamp,
            'visual_content_id': visual_content.id,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Frame analysis failed: {str(e)}", exc_info=True)

        self.update_state(
            state='FAILURE',
            meta={'status': f'Frame analysis failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'frame_number': frame_number,
            'task_id': self.request.id
        }

    finally:
        # Cleanup
        if vlm:
            vlm.cleanup()
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")
        db.close()


# Helper functions for video summary generation

def _generate_video_summary(frame_analyses: List[VisualContent], metadata: Dict[str, Any]) -> str:
    """
    Generate comprehensive video summary from frame analyses.

    Args:
        frame_analyses: List of VisualContent records for video frames
        metadata: Video metadata dict

    Returns:
        Comprehensive summary text
    """
    if not frame_analyses:
        return "No frame analyses available for summary."

    # Collect all captions
    captions = [f"[{fa.timestamp_in_video:.1f}s] {fa.vlm_caption}"
                for fa in frame_analyses if fa.vlm_caption]

    # Build summary
    summary_parts = [
        f"Video Analysis Summary (Duration: {metadata.get('duration', 0):.1f}s)",
        f"Resolution: {metadata.get('width')}x{metadata.get('height')}",
        f"Frames Analyzed: {len(frame_analyses)}",
        "",
        "Timeline:",
        *captions[:10]  # Include first 10 frames
    ]

    if len(captions) > 10:
        summary_parts.append(f"... and {len(captions) - 10} more frames")

    return "\n".join(summary_parts)


def _extract_key_moments(frame_analyses: List[VisualContent]) -> List[Dict[str, Any]]:
    """
    Extract key moments from frame analyses.

    Args:
        frame_analyses: List of VisualContent records

    Returns:
        List of key moment dicts with timestamp and description
    """
    key_moments = []

    for fa in frame_analyses:
        # Identify key moments based on content
        has_activity = fa.detected_activities and len(fa.detected_activities) > 0
        has_sensitive = fa.sensitive_flags and fa.sensitive_flags.get('has_sensitive_content', False)

        if has_activity or has_sensitive:
            key_moments.append({
                'timestamp': fa.timestamp_in_video,
                'description': fa.vlm_caption,
                'activities': fa.detected_activities,
                'flagged': has_sensitive
            })

    return key_moments


def _generate_visual_summary(frame_analyses: List[VisualContent]) -> str:
    """
    Generate visual summary from frame analyses.

    Args:
        frame_analyses: List of VisualContent records

    Returns:
        Visual summary text
    """
    # Collect all objects and scenes
    all_objects = []
    all_scenes = []

    for fa in frame_analyses:
        if fa.detected_objects:
            all_objects.extend(fa.detected_objects)
        if fa.detected_scenes:
            all_scenes.extend(fa.detected_scenes)

    # Get unique items
    unique_objects = list(set(all_objects))
    unique_scenes = list(set(all_scenes))

    summary_parts = [
        f"Visual Elements Detected:",
        f"Objects: {', '.join(unique_objects[:10]) if unique_objects else 'None'}",
        f"Scenes: {', '.join(unique_scenes[:5]) if unique_scenes else 'None'}"
    ]

    return "\n".join(summary_parts)


def _calculate_importance_score(frame_analyses: List[VisualContent]) -> float:
    """
    Calculate overall importance score for video.

    Args:
        frame_analyses: List of VisualContent records

    Returns:
        Importance score between 0.0 and 1.0
    """
    if not frame_analyses:
        return 0.0

    # Factors that increase importance:
    # - Sensitive content detected
    # - Activities detected
    # - Number of objects/scenes

    score = 0.5  # Base score

    for fa in frame_analyses:
        # Sensitive content increases importance
        if fa.sensitive_flags and fa.sensitive_flags.get('has_sensitive_content'):
            score += 0.1

        # Activities increase importance
        if fa.detected_activities and len(fa.detected_activities) > 0:
            score += 0.05

    # Normalize to 0.0-1.0 range
    return min(1.0, max(0.0, score / len(frame_analyses)))


def _extract_flagged_content(frame_analyses: List[VisualContent]) -> List[Dict[str, Any]]:
    """
    Extract flagged content from frame analyses.

    Args:
        frame_analyses: List of VisualContent records

    Returns:
        List of flagged content with timestamps and reasons
    """
    flagged = []

    for fa in frame_analyses:
        if fa.sensitive_flags and fa.sensitive_flags.get('has_sensitive_content'):
            flagged.append({
                'timestamp': fa.timestamp_in_video,
                'frame_number': fa.frame_number,
                'flags': fa.sensitive_flags.get('flags', []),
                'severity': fa.sensitive_flags.get('severity', 'unknown'),
                'description': fa.sensitive_flags.get('description', '')
            })

    return flagged
