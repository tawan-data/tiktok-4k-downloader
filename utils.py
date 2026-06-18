import os
import re
import time
import shutil
import subprocess
from datetime import datetime
from flask import current_app

def format_file_size(size_bytes):
    """Format file size to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def format_duration(seconds):
    """Format duration to MM:SS or HH:MM:SS"""
    if seconds < 3600:
        return f"{int(seconds // 60)}:{int(seconds % 60):02d}"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}"

def is_tiktok_url(url):
    """Check if URL is a TikTok URL"""
    patterns = [
        r'tiktok\.com/[@\w]+/video/\d+',
        r'tiktok\.com/[@\w]+\?lang=',
        r'vm\.tiktok\.com/[\w]+',
        r'tiktok\.com/[@\w]+',
    ]
    return any(re.search(p, url) for p in patterns)

def generate_unique_id():
    """Generate unique ID"""
    return f"{int(time.time())}_{os.urandom(4).hex()}"

def cleanup_directory(directory, max_age_hours=24):
    """Cleanup old files in directory"""
    if not os.path.exists(directory):
        return
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            if current_time - os.path.getmtime(filepath) > max_age_seconds:
                try:
                    os.remove(filepath)
                except Exception:
                    pass
