import os
import re
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch
from anony import logger
from anony.helpers import Track, utils

API_URL = "https://shrutibots.site"
DOWNLOAD_DIR = "downloads"


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception:
            return None

        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool):
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception:
            pass

        return tracks

    async def download(self, video_id: str, video: bool = False):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        ext = "mp4" if video else "mp3"
        filename = f"{DOWNLOAD_DIR}/{video_id}.{ext}"

        if Path(filename).exists():
            return filename

        params = {
            "url": video_id,
            "type": "video" if video else "audio"
        }

        try:
            async with aiohttp.ClientSession() as session:

                async with session.get(
                    f"{API_URL}/download",
                    params=params
                ) as resp:

                    if resp.status != 200:
                        return None

                    data = await resp.json()
                    token = data.get("download_token")

                    if not token:
                        return None

                    stream_url = f"{API_URL}/stream/{video_id}?type={params['type']}&token={token}"

                    async with session.get(stream_url) as file_resp:

                        if file_resp.status != 200:
                            return None

                        with open(filename, "wb") as f:
                            async for chunk in file_resp.content.iter_chunked(16384):
                                f.write(chunk)

            return filename

        except Exception as ex:
            logger.warning("API download failed: %s", ex)
            return None