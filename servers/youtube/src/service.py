import os
import json
import yt_dlp

from requests import Session
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import (
    TextFormatter,
)
from youtube_transcript_api.proxies import WebshareProxyConfig

from .utils import extract_video_id


class YouTubeTranscriptService:
    """Service class wrapping youtube-transcript-api with proxy support."""

    def __init__(self, use_proxy: bool = True):
        self.api = self._create_api(use_proxy)

    def _create_api(self, use_proxy: bool) -> YouTubeTranscriptApi:
        """Create API instance with optional proxy support."""
        if not use_proxy:
            return YouTubeTranscriptApi()

        proxy_username = os.getenv("WEBSHARE_USERNAME")
        proxy_password = os.getenv("WEBSHARE_PASSWORD")

        if proxy_username and proxy_password:
            proxy_config = WebshareProxyConfig(
                proxy_username=proxy_username,
                proxy_password=proxy_password,
            )
            http_client = Session()
            http_client.proxies = proxy_config.to_requests_dict()
            return YouTubeTranscriptApi(http_client=http_client)

        return YouTubeTranscriptApi()

    def fetch(
        self,
        video_url_or_id: str,
    ):
        """Fetch transcript."""
        video_id = extract_video_id(video_url_or_id)
        return self.api.fetch(video_id)

    def get_transcript_text(
        self,
        video_url_or_id: str,
    ) -> str:
        """Get transcript as plain text."""
        transcript = self.fetch(video_url_or_id)
        formatter = TextFormatter()
        return formatter.format_transcript(transcript)

    def search_videos(self, query: str, max_results: int = 5) -> str:
        """Search YouTube and return results as formatted text."""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch{max_results}:{query}"
            info = ydl.extract_info(search_query, download=False)
            
            if 'entries' not in info or not info['entries']:
                return "No results found."
                
            results = []
            for i, entry in enumerate(info['entries']):
                title = entry.get('title', 'Unknown Title')
                url = entry.get('url', '')
                duration = entry.get('duration', 0)
                channel = entry.get('uploader', 'Unknown Channel')
                results.append(f"{i+1}. {title} | Channel: {channel} | Duration: {duration}s | URL: {url}")
                
            return "\n".join(results)

    def get_metadata(self, video_url: str) -> str:
        """Get video metadata like title and description."""
        ydl_opts = {
            'quiet': True,
            'simulate': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
            except Exception as e:
                return f"Could not fetch metadata: {str(e)}"
            
            title = info.get('title', 'Unknown')
            uploader = info.get('uploader', 'Unknown')
            views = info.get('view_count', 0)
            desc = info.get('description', '')
            
            output = f"Title: {title}\nChannel: {uploader}\nViews: {views}\n\nDescription:\n{desc}"
            return output
