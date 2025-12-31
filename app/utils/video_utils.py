"""
Utility functions for video processing
"""
import ffmpeg
from pathlib import Path
import os
import shutil

# Set ffmpeg executable path for Windows
if os.name == 'nt':  # Windows
    # Try to find ffmpeg in PATH
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        os.environ['FFMPEG_BINARY'] = ffmpeg_path
        os.environ['FFPROBE_BINARY'] = ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')


def get_video_duration(video_path: str) -> int:
    """
    Extract video duration in seconds using ffmpeg
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Duration in seconds (rounded to nearest integer)
    """
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        return int(round(duration))
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return 0


def get_video_info(video_path: str) -> dict:
    """
    Extract comprehensive video information using ffmpeg
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Dictionary with video info (duration, width, height, etc.)
    """
    try:
        probe = ffmpeg.probe(video_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        
        return {
            'duration': int(round(float(probe['format']['duration']))),
            'width': int(video_info['width']),
            'height': int(video_info['height']),
            'codec': video_info['codec_name'],
            'fps': eval(video_info.get('r_frame_rate', '0/1'))
        }
    except Exception as e:
        print(f"Error getting video info: {e}")
        return {
            'duration': 0,
            'width': 0,
            'height': 0,
            'codec': 'unknown',
            'fps': 0
        }