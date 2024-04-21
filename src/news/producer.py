import os
import nats
import asyncio
from protobuf import video_pb2
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled
from pytube import YouTube
from pytube.exceptions import AgeRestrictedError
from django.conf import settings


async def push_videos():
    api_key=settings.YOUTUBE_API_KEY
    yt_api = build("youtube", "v3", developerKey=api_key)
    request = yt_api.videoCategories().list(part="snippet", regionCode="US")
    response = request.execute()
    video_file_path = os.path.join(settings.BASE_DIR, "video_files/")
    categories = {}
    # Turn categories into a dictionary
    for item in response["items"]:
        categories[item["id"]] = item["snippet"]["title"]

    nc = await nats.connect("nats:4222")
    js = nc.jetstream()
    await js.add_stream(name="youtube-news", subjects=["news"])

    # Store videos from links in text file
    with open("yt-links", "r") as videos:
        for video in videos:
            if video[0] == '#':
                # ignore comment lines in link file
                continue
            else:
                v_id = video.rstrip()
                # Create a protobuf object
                video_proto = video_pb2.Video()
                video_proto.id = v_id

                # Get pytube object of video
                v_url = f"https://www.youtube.com/watch?v={v_id}"
                yt = YouTube(v_url)

                # Assign fields from pytube object
                video_proto.title = yt.title
                video_proto.channel.id = yt.channel_id

                video_proto.publication_date.FromDatetime(yt.publish_date)

                # Use YouTube API to get channel title and video category
                response = yt_api.videos().list(part="snippet", id=v_id).execute()
                video_proto.channel.title = response["items"][0]["snippet"]["channelTitle"]
                cat_id = response["items"][0]["snippet"]["categoryId"]
                video_proto.category = categories[cat_id]

                # Process transcript
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(v_id)
                except TranscriptsDisabled:
                    print(f"{v_id} has transcripts disabled")
                    continue

                transcript_text = ""
                for line in transcript:
                    transcript_text += line["text"].strip()
                    transcript_text += " "
                if transcript_text.strip() == "":
                    print(f"Failed to get transcript for {v_id}")
                    continue
                video_proto.transcript = transcript_text

                # Send message over nats
                payload = video_proto.SerializeToString()
                await js.publish("news", payload)

                # Download video
                if not os.path.isfile(f"{video_file_path}/{v_id}"):
                    try:
                        stream = yt.streams.first()
                    except AgeRestrictedError:
                        print(f"{video_proto.id} was age restricted, could not download")
                        continue

                    if stream is None:
                        print(f"Failed to get stream for {v_id}")
                        continue
                    else:
                        stream.download(output_path=video_file_path, filename=v_id)

        await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
