# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "mcp[cli]>=1.12.3",
#     "pydantic>=2.11.7",
#     "python-dotenv>=1.1.1",
#     "requests>=2.32.4",
#     "youtube-transcript-api>=1.2.2",
#     "yt-dlp>=2024.03.10",
# ]
# ///


from mcp.server.fastmcp import FastMCP
from src.service import YouTubeTranscriptService

mcp = FastMCP(
    name="YouTube",
    stateless_http=True,
)

_service = YouTubeTranscriptService(use_proxy=True)


@mcp.tool()
def get_transcript(
    video_url_or_id: str,
) -> str:
    """Get transcript as plain text."""
    try:
        return _service.get_transcript_text(video_url_or_id)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def search_youtube(query: str, max_results: int = 5) -> str:
    """Search for YouTube videos. Returns top results with titles and URLs."""
    try:
        return _service.search_videos(query, max_results)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def get_video_metadata(video_url: str) -> str:
    """Get metadata for a YouTube video including title, channel, and description."""
    try:
        return _service.get_metadata(video_url)
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
