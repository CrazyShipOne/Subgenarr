"""Media processing module for audio/video extraction and subtitle generation."""

import asyncio
import logging
import os
import shutil
import string
import random
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import subprocess
import json
import re

import sys
sys.path.append('/app/shared')

from shared import config
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class MediaProcessor:
    """Handles media processing including audio/video extraction and subtitle generation."""

    def __init__(self):
        self.temp_dir = config.TEMP_DIR
        self.segment_duration = config.AUDIO_SEGMENT_DURATION
        self.overlap_duration = config.AUDIO_OVERLAP_DURATION
        self.screenshots_per_segment = config.SCREENSHOTS_PER_SEGMENT
        self.target_language = config.TARGET_SUBTITLE_LANGUAGE
        self.cleanup_enabled = config.TEMP_CLEANUP_ENABLED
        self.llm_client = LLMClient()

    # ISO 639-1 (2-letter) to ISO 639-2 (3-letter) mapping for common languages.
    # ffprobe typically returns 3-letter codes in stream language tags.
    _LANG_CODE_MAP: Dict[str, list] = {
        'en': ['eng'],
        'zh': ['chi', 'zho'],
        'ja': ['jpn'],
        'ko': ['kor'],
        'fr': ['fra', 'fre'],
        'de': ['deu', 'ger'],
        'es': ['spa'],
        'it': ['ita'],
        'pt': ['por'],
        'ru': ['rus'],
        'ar': ['ara'],
        'hi': ['hin'],
        'th': ['tha'],
        'vi': ['vie'],
        'id': ['ind'],
        'ms': ['msa', 'may'],
        'nl': ['nld', 'dut'],
        'pl': ['pol'],
        'cs': ['ces', 'cze'],
        'tr': ['tur'],
        'sv': ['swe'],
        'da': ['dan'],
        'fi': ['fin'],
        'uk': ['ukr'],
    }

    async def check_embedded_subtitle_language(self, video_path: str, target_language: str) -> bool:
        """
        Check whether the video has an embedded subtitle stream matching target_language.

        Uses ffprobe to read subtitle stream language tags and normalises both
        ISO 639-1 (2-letter) and ISO 639-2 (3-letter) codes before comparing.

        Returns True if a matching subtitle stream is found.
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 's',
                '-show_entries', 'stream_tags=language',
                '-of', 'json',
                video_path,
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error(f"ffprobe subtitle check error: {stderr.decode()}")
                return False

            data = json.loads(stdout.decode())
            streams = data.get('streams', [])

            if not streams:
                return False

            # Build the set of acceptable codes for the target language
            lang = target_language.lower()
            accepted = {lang}
            accepted.update(self._LANG_CODE_MAP.get(lang, []))

            for stream in streams:
                stream_lang = stream.get('tags', {}).get('language', '').lower()
                if stream_lang in accepted:
                    logger.info(
                        f"Embedded subtitle stream matched: "
                        f"stream_lang='{stream_lang}' target='{target_language}'"
                    )
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking embedded subtitles: {e}", exc_info=True)
            return False

    async def process_media(self, task: Dict) -> Optional[str]:
        """
        Process media file to generate subtitles.

        Args:
            task: Task dictionary with video path and metadata.

        Returns:
            Path to generated subtitle file, or None if failed.
        """
        task_id = task['task_id']
        video_path = task['video_file_path']
        directory_path = task['directory_path']

        workspace = None

        try:
            # Step 1: Setup workspace
            logger.info(f"Task {task_id}: Setting up workspace")
            workspace = self._setup_workspace(task_id)

            # Step 2: Get video duration
            duration = await self._get_video_duration(video_path)
            if not duration:
                logger.error(f"Task {task_id}: Failed to get video duration")
                return None

            logger.info(f"Task {task_id}: Video duration: {duration}s")

            # Step 3: Extract audio segments
            logger.info(f"Task {task_id}: Extracting audio segments")
            segments = await self._extract_audio_segments(video_path, workspace, duration)

            if not segments:
                logger.error(f"Task {task_id}: Failed to extract audio segments")
                return None

            logger.info(f"Task {task_id}: Extracted {len(segments)} audio segments")

            # Step 4: Extract screenshots for each segment
            logger.info(f"Task {task_id}: Extracting screenshots")
            for segment in segments:
                success = await self._extract_screenshots(
                    video_path,
                    workspace,
                    segment['index'],
                    segment['start_time'],
                    segment['end_time']
                )
                if not success:
                    logger.error(f"Task {task_id}: Failed to extract screenshots for segment {segment['index']}")
                    return None

            logger.info(f"Task {task_id}: Screenshots extracted successfully")

            # Step 5: Process with LLM
            logger.info(f"Task {task_id}: Starting LLM processing")
            transcript_lines = await self._process_with_llm(task, workspace, segments)

            if not transcript_lines:
                logger.error(f"Task {task_id}: Failed to generate transcript")
                return None

            logger.info(f"Task {task_id}: Generated {len(transcript_lines)} transcript lines")

            # Step 6: Generate SRT file
            logger.info(f"Task {task_id}: Generating SRT file")
            subtitle_path = await self._generate_srt(
                video_path,
                directory_path,
                transcript_lines
            )

            if not subtitle_path:
                logger.error(f"Task {task_id}: Failed to generate SRT file")
                return None

            logger.info(f"Task {task_id}: SRT file generated: {subtitle_path}")

            # Step 7: Cleanup
            if self.cleanup_enabled:
                logger.info(f"Task {task_id}: Cleaning up workspace")
                self._cleanup_workspace(workspace)

            return subtitle_path

        except Exception as e:
            logger.error(f"Task {task_id}: Error processing media: {e}", exc_info=True)
            if workspace and self.cleanup_enabled:
                self._cleanup_workspace(workspace)
            return None

    def _setup_workspace(self, task_id: int) -> str:
        """
        Create temporary workspace directory.

        Returns:
            Path to workspace directory.
        """
        # Generate random suffix
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        workspace = os.path.join(self.temp_dir, f"{task_id}_{random_suffix}")

        # Create directories
        os.makedirs(workspace, exist_ok=True)
        os.makedirs(os.path.join(workspace, "audio"), exist_ok=True)
        os.makedirs(os.path.join(workspace, "screenshots"), exist_ok=True)

        logger.info(f"Created workspace: {workspace}")
        return workspace

    async def _get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration in seconds using ffprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                video_path
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error(f"ffprobe error: {stderr.decode()}")
                return None

            data = json.loads(stdout.decode())
            duration = float(data['format']['duration'])
            return duration

        except Exception as e:
            logger.error(f"Error getting video duration: {e}", exc_info=True)
            return None

    async def _extract_audio_segments(
        self,
        video_path: str,
        workspace: str,
        duration: float
    ) -> List[Dict]:
        """
        Extract audio segments with overlap.

        Returns:
            List of segment dictionaries with start_time, end_time, index, audio_path.
        """
        segments = []
        segment_index = 0
        current_start = 0.0

        while current_start < duration:
            # Calculate segment times
            if segment_index == 0:
                start_time = 0.0
            else:
                start_time = max(0, current_start - self.overlap_duration)

            end_time = min(duration, current_start + self.segment_duration)

            # Create segment directory
            segment_dir = os.path.join(workspace, "audio", str(segment_index))
            os.makedirs(segment_dir, exist_ok=True)

            audio_path = os.path.join(segment_dir, "audio.wav")

            # Extract audio segment
            success = await self._extract_audio_segment(
                video_path,
                audio_path,
                start_time,
                end_time - start_time
            )

            if not success:
                logger.error(f"Failed to extract audio segment {segment_index}")
                return []

            segments.append({
                'index': segment_index,
                'start_time': start_time,
                'end_time': end_time,
                'audio_path': audio_path,
            })

            # Move to next segment
            current_start += self.segment_duration
            segment_index += 1

            # Break if we've reached the end
            if end_time >= duration:
                break

        return segments

    async def _extract_audio_segment(
        self,
        video_path: str,
        output_path: str,
        start_time: float,
        duration: float
    ) -> bool:
        """Extract audio segment using ffmpeg."""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-vn',  # No video
                '-acodec', 'pcm_s16le',
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite output
                output_path
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error(f"ffmpeg audio extraction error: {stderr.decode()}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error extracting audio segment: {e}", exc_info=True)
            return False

    async def _extract_screenshots(
        self,
        video_path: str,
        workspace: str,
        segment_index: int,
        start_time: float,
        end_time: float
    ) -> bool:
        """Extract screenshots for a segment."""
        try:
            segment_dir = os.path.join(workspace, "screenshots", str(segment_index))
            os.makedirs(segment_dir, exist_ok=True)

            segment_duration = end_time - start_time
            interval = segment_duration / self.screenshots_per_segment

            for i in range(self.screenshots_per_segment):
                timestamp = start_time + (i * interval) + (interval / 2)  # Middle of interval
                output_path = os.path.join(segment_dir, f"{i}.jpg")

                cmd = [
                    'ffmpeg',
                    '-ss', str(timestamp),
                    '-i', video_path,
                    '-vframes', '1',
                    '-q:v', '2',  # High quality
                    '-y',
                    output_path
                ]

                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await result.communicate()

                if result.returncode != 0:
                    logger.error(f"ffmpeg screenshot error: {stderr.decode()}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error extracting screenshots: {e}", exc_info=True)
            return False

    async def _process_with_llm(
        self,
        task: Dict,
        workspace: str,
        segments: List[Dict]
    ) -> List[Dict]:
        """
        Process segments with LLM to generate transcript.

        Returns:
            List of transcript lines with start_time, end_time, text.
        """
        all_transcript_lines = []
        previous_overlap_text = ""

        for segment in segments:
            segment_index = segment['index']
            logger.info(f"Task {task['task_id']}: Processing segment {segment_index}/{len(segments)-1}")

            # Load audio and screenshots
            audio_path = segment['audio_path']
            screenshot_dir = os.path.join(workspace, "screenshots", str(segment_index))
            screenshot_paths = sorted([
                os.path.join(screenshot_dir, f)
                for f in os.listdir(screenshot_dir)
                if f.endswith('.jpg')
            ])

            # Call LLM
            transcript_text = await self.llm_client.transcribe_segment(
                task=task,
                audio_path=audio_path,
                screenshot_paths=screenshot_paths,
                previous_overlap_text=previous_overlap_text
            )

            if not transcript_text:
                logger.error(f"Task {task['task_id']}: Failed to get transcript for segment {segment_index}")
                return []

            # Parse transcript lines
            lines = self._parse_transcript(transcript_text, segment['start_time'])

            if not lines:
                logger.warning(f"Task {task['task_id']}: No transcript lines parsed for segment {segment_index}")
                continue

            # Handle overlap
            is_last_segment = segment_index == len(segments) - 1

            if not is_last_segment:
                # Extract overlap text
                overlap_start = segment['end_time'] - self.overlap_duration
                overlap_lines = []
                non_overlap_lines = []

                for line in lines:
                    if line['start_time'] >= overlap_start:
                        overlap_lines.append(line)
                    else:
                        non_overlap_lines.append(line)

                # Format overlap text for next iteration
                previous_overlap_text = '\n'.join([
                    f"[{self._format_timestamp(l['start_time'])} - {self._format_timestamp(l['end_time'])}] {l['text']}"
                    for l in overlap_lines
                ])

                # Add non-overlap lines to result
                all_transcript_lines.extend(non_overlap_lines)
            else:
                # Last segment, add all lines
                all_transcript_lines.extend(lines)

        return all_transcript_lines

    def _parse_transcript(self, transcript_text: str, segment_start_time: float) -> List[Dict]:
        """
        Parse transcript text into structured lines.

        Expected format: [HH:MM:SS - HH:MM:SS] text
        """
        lines = []

        # Match lines with timestamp pattern
        pattern = r'\[(\d{2}:\d{2}:\d{2}(?:\.\d{3})?)\s*-\s*(\d{2}:\d{2}:\d{2}(?:\.\d{3})?)\]\s*(.+)'

        for line in transcript_text.strip().split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                start_ts, end_ts, text = match.groups()

                # Convert timestamps to seconds
                start_seconds = self._timestamp_to_seconds(start_ts)
                end_seconds = self._timestamp_to_seconds(end_ts)

                # Adjust for segment start time
                absolute_start = segment_start_time + start_seconds
                absolute_end = segment_start_time + end_seconds

                lines.append({
                    'start_time': absolute_start,
                    'end_time': absolute_end,
                    'text': text.strip()
                })

        return lines

    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert HH:MM:SS or HH:MM:SS.mmm to seconds."""
        parts = timestamp.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])

        # Handle seconds with optional milliseconds
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0

        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
        return total_seconds

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS.mmm timestamp."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    async def _generate_srt(
        self,
        video_path: str,
        directory_path: str,
        transcript_lines: List[Dict]
    ) -> Optional[str]:
        """Generate SRT subtitle file."""
        try:
            # Generate output filename
            video_filename = Path(video_path).stem
            subtitle_filename = self._generate_subtitle_filename(
                directory_path,
                video_filename,
                self.target_language
            )

            subtitle_path = os.path.join(directory_path, subtitle_filename)

            # Write SRT file
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                for idx, line in enumerate(transcript_lines, start=1):
                    # Subtitle index
                    f.write(f"{idx}\n")

                    # Timestamps
                    start_ts = self._format_srt_timestamp(line['start_time'])
                    end_ts = self._format_srt_timestamp(line['end_time'])
                    f.write(f"{start_ts} --> {end_ts}\n")

                    # Text
                    f.write(f"{line['text']}\n")

                    # Blank line separator
                    f.write("\n")

            logger.info(f"Generated SRT file: {subtitle_path}")
            return subtitle_path

        except Exception as e:
            logger.error(f"Error generating SRT file: {e}", exc_info=True)
            return None

    def _generate_subtitle_filename(
        self,
        directory_path: str,
        video_filename: str,
        language: str
    ) -> str:
        """Generate unique subtitle filename."""
        # Try without index first: {video}.{lang}.srt
        filename = f"{video_filename}.{language}.srt"
        if not os.path.exists(os.path.join(directory_path, filename)):
            return filename

        # Conflict found, increment from 1: {video}.{lang}.1.srt
        index = 1
        while True:
            filename = f"{video_filename}.{language}.{index}.srt"
            if not os.path.exists(os.path.join(directory_path, filename)):
                return filename
            index += 1

    def _format_srt_timestamp(self, seconds: float) -> str:
        """Format seconds to SRT timestamp format: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _cleanup_workspace(self, workspace: str):
        """Remove workspace directory."""
        try:
            if os.path.exists(workspace):
                shutil.rmtree(workspace)
                logger.info(f"Cleaned up workspace: {workspace}")
        except Exception as e:
            logger.error(f"Error cleaning up workspace: {e}", exc_info=True)
