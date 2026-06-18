import re
import time
import uuid
import requests
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class TikTokAPI:
    """Base class for TikTok API"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_video_info(self, url: str) -> Tuple[Optional[Dict], Optional[str]]:
        raise NotImplementedError


class TikWMAPI(TikTokAPI):
    """TikWM API - Main"""
    
    def get_video_info(self, url: str) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            api_url = "https://www.tikwm.com/api/"
            payload = {"url": url, "hd": 1}
            
            response = self.session.post(api_url, data=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                return None, data.get("msg", "Unknown error")
            
            video_data = data["data"]
            
            video_url = video_data.get("hdplay") or video_data.get("play")
            
            if not video_url:
                return None, "No video URL found"
            
            return {
                'title': video_data.get("title", "TikTok Video"),
                'video_url': video_url,
                'music_url': video_data.get("music"),
                'thumbnail': video_data.get("cover"),
                'author': video_data.get("author", {}).get("unique_id", "Unknown"),
                'duration': video_data.get("duration", 0),
                'quality': "1080p" if video_data.get("hdplay") else "720p",
                'id': video_data.get("id", str(uuid.uuid4())[:8])
            }, None
            
        except Exception as e:
            logger.error(f"TikWM error: {e}")
            return None, str(e)


class SSSTikAPI(TikTokAPI):
    """SSSTik.io API - Backup"""
    
    def get_video_info(self, url: str) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            self.session.get('https://ssstik.io/en', timeout=10)
            
            response = self.session.post(
                'https://ssstik.io/abc',
                data={'id': url, 'locale': 'en', 'tt': '1'},
                timeout=30
            )
            response.raise_for_status()
            
            html = response.text
            
            video_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>Download</a>', html)
            if not video_match:
                video_match = re.search(r'https://[^\s"]+\.mp4[^\s"]*', html)
            
            if not video_match:
                return None, "No video URL found"
            
            video_url = video_match.group(1)
            
            title_match = re.search(r'<p[^>]*>([^<]+)</p>', html)
            title = title_match.group(1).strip() if title_match else "TikTok Video"
            
            return {
                'title': title,
                'video_url': video_url,
                'music_url': None,
                'thumbnail': None,
                'author': "Unknown",
                'duration': 0,
                'quality': "1080p",
                'id': str(uuid.uuid4())[:8]
            }, None
            
        except Exception as e:
            logger.error(f"SSSTik error: {e}")
            return None, str(e)


class TikMateAPI(TikTokAPI):
    """TikMate.cc API - Backup 2"""
    
    def get_video_info(self, url: str) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            session.get('https://tikmate.cc/', timeout=10)
            
            response = session.post(
                'https://tikmate.cc/download',
                data={'url': url},
                timeout=30
            )
            response.raise_for_status()
            
            html = response.text
            
            video_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*download[^"]*"', html)
            if not video_match:
                video_match = re.search(r'https://[^\s"]+\.mp4[^\s"]*', html)
            
            if not video_match:
                return None, "No video URL found"
            
            video_url = video_match.group(1)
            
            title_match = re.search(r'<title>([^<]+)</title>', html)
            title = title_match.group(1).replace(' - TikMate', '').strip() if title_match else "TikTok Video"
            
            return {
                'title': title,
                'video_url': video_url,
                'music_url': None,
                'thumbnail': None,
                'author': "Unknown",
                'duration': 0,
                'quality': "720p",
                'id': str(uuid.uuid4())[:8]
            }, None
            
        except Exception as e:
            logger.error(f"TikMate error: {e}")
            return None, str(e)


def get_available_apis() -> list:
    """Get list of available APIs"""
    return [
        {'id': 'tikwm', 'name': 'TikWM (แนะนำ)', 'supports_hd': True},
        {'id': 'ssstik', 'name': 'SSSTik.io', 'supports_hd': True},
        {'id': 'tikmate', 'name': 'TikMate.cc', 'supports_hd': False},
    ]


def download_tiktok(url: str, api_id: str = 'tikwm') -> Tuple[Optional[Dict], Optional[str]]:
    """Download TikTok video with selected API"""
    apis = {
        'tikwm': TikWMAPI(),
        'ssstik': SSSTikAPI(),
        'tikmate': TikMateAPI(),
    }
    
    api = apis.get(api_id)
    if not api:
        return None, f"API '{api_id}' not found"
    
    logger.info(f"Using API: {api_id}")
    return api.get_video_info(url)
