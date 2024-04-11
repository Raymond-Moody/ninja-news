import os
import nats
import asyncio
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

api_key=os.getenv("YT_API_KEY")

channel_url="https://www.youtube.com/channel/UCYfdidRxbB8Qhf0Nx7ioOYw"

yt = build("youtube", "v3", developerKey=api_key)

request = yt.videoCategories().list(part="snippet", regionCode="US")
response = request.execute()

# Print categories with their IDs
for item in response["items"]:
    print(item["id"], ":", item["snippet"]["title"])

async def main():
    nc = await nats.connect("nats:4222")
    js = nc.jetstream()
    await js.add_stream(name="youtube-news", subjects=["news"])

    # Download the videos
