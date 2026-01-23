"""LLM client for processing audio and video with AI models."""

import base64
import logging
import asyncio
from typing import List, Optional, Dict
from pathlib import Path

from openai import AsyncOpenAI

import sys
sys.path.append('/app/shared')

from shared import config, get_db_session, MediaLibrary

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM API for transcription."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.AI_API_KEY,
            base_url=config.AI_BASE_URL,
            timeout=config.AI_TIMEOUT,
            max_retries=config.AI_MAX_RETRIES,
        )
        self.model = config.AI_MODEL
        self.target_language = config.TARGET_SUBTITLE_LANGUAGE

    async def transcribe_segment(
        self,
        task: Dict,
        audio_path: str,
        screenshot_paths: List[str],
        previous_overlap_text: str = ""
    ) -> Optional[str]:
        """
        Transcribe an audio segment with visual context.

        Args:
            task: Task dictionary with media metadata.
            audio_path: Path to audio segment file.
            screenshot_paths: List of screenshot file paths.
            previous_overlap_text: Previous segment's overlap text for context.

        Returns:
            Transcript text with timestamps, or None if failed.
        """
        try:
            # Load prompt template
            prompt = await self._build_prompt(task, previous_overlap_text)

            # Prepare message content
            message_content = []

            # Add text prompt
            message_content.append({
                "type": "text",
                "text": prompt
            })

            # Add audio
            with open(audio_path, 'rb') as f:
                audio_data = base64.b64encode(f.read()).decode('utf-8')

            message_content.append({
                "type": "input_audio",
                "input_audio": {
                    "data": audio_data,
                    "format": "wav"
                }
            })

            # Add screenshots
            for screenshot_path in screenshot_paths:
                with open(screenshot_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}"
                    }
                })

            # Call LLM API with retries
            for attempt in range(config.AI_MAX_RETRIES):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": message_content
                            }
                        ],
                        temperature=0.3,
                    )

                    transcript = response.choices[0].message.content

                    if transcript:
                        return transcript.strip()
                    else:
                        logger.warning(f"Empty transcript received (attempt {attempt + 1})")

                except Exception as e:
                    logger.warning(f"LLM API call failed (attempt {attempt + 1}/{config.AI_MAX_RETRIES}): {e}")

                    if attempt < config.AI_MAX_RETRIES - 1:
                        # Exponential backoff
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All retry attempts exhausted")
                        raise

            return None

        except Exception as e:
            logger.error(f"Error in LLM transcription: {e}", exc_info=True)
            return None

    async def _build_prompt(self, task: Dict, previous_overlap_text: str) -> str:
        """
        Build prompt from template and task metadata.

        Args:
            task: Task dictionary with media metadata.
            previous_overlap_text: Previous overlap text for context.

        Returns:
            Formatted prompt string.
        """
        # Load prompt template
        prompt_template_path = Path(__file__).parent.parent / "prompts" / "transcription.txt"

        with open(prompt_template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        # Get media metadata from database
        try:
            with get_db_session() as session:
                media = session.query(MediaLibrary).filter(
                    MediaLibrary.media_id == task['media_id']
                ).first()

                if not media:
                    logger.warning(f"Media {task['media_id']} not found, using minimal metadata")
                    metadata = {
                        'title': task.get('media_title', 'Unknown'),
                        'year': '',
                        'overview': '',
                        'cast': '',
                        'season': '',
                        'episode': '',
                        'episode_overview': '',
                    }
                else:
                    # Parse cast JSON
                    import json
                    try:
                        cast_list = json.loads(media.cast) if media.cast else []
                        cast_str = ', '.join(cast_list[:5])  # Top 5 actors
                    except:
                        cast_str = ''

                    metadata = {
                        'title': media.title or '',
                        'year': str(media.year) if media.year else '',
                        'overview': media.overview or '',
                        'cast': cast_str,
                        'season': str(media.season) if media.season else '',
                        'episode': str(media.episode) if media.episode else '',
                        'episode_overview': media.episode_overview or '',
                    }

        except Exception as e:
            logger.error(f"Error fetching media metadata: {e}", exc_info=True)
            metadata = {
                'title': task.get('media_title', 'Unknown'),
                'year': '',
                'overview': '',
                'cast': '',
                'season': '',
                'episode': '',
                'episode_overview': '',
            }

        # Format prompt
        prompt = template.format(
            title=metadata['title'],
            year=metadata['year'],
            overview=metadata['overview'],
            cast=metadata['cast'],
            season=metadata['season'],
            episode=metadata['episode'],
            episode_overview=metadata['episode_overview'],
            target_language=self._get_language_name(self.target_language),
            previous_overlap_text=previous_overlap_text if previous_overlap_text else "None (this is the first segment)",
        )

        return prompt

    def _get_language_name(self, language_code: str) -> str:
        """Convert language code to full name."""
        language_map = {
            'en': 'English',
            'zh': 'Chinese',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'ja': 'Japanese',
            'ko': 'Korean',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'it': 'Italian',
        }

        return language_map.get(language_code, language_code.upper())
