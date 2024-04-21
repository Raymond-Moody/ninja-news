import os
import nats
import asyncio
from protobuf import video_pb2
from datetime import timezone

from django.conf import settings

from news.models import Channel, Category, Video

async def pull_messages():
    nc = await nats.connect("nats:4222")
    js = nc.jetstream()
    try:
        sub = await js.pull_subscribe("news", "ninja-news")
    except:
        print("Failed to subscribe to jetstream")
        return -1

    try:
        msgs = await sub.fetch(50)
    except TimeoutError:
        print("Jetstream fetch timed out")
        return -1

    for msg in msgs:
        video_proto = video_pb2.Video()
        video_proto.ParseFromString(msg.data)

        # Skip if video already exists in the database
        if await Video.objects.filter(id=video_proto.id).aexists():
            print(f"Skipping video {video_proto.id} as it already exists")
            await msg.ack()
            continue

        # Create channel and category objects if they do not exist
        # Otherwise, get the existing object
        ch, created = await Channel.objects.aget_or_create(
            id=video_proto.channel.id,
            name=video_proto.channel.title
        )
        cat, created = await Category.objects.aget_or_create(name=video_proto.category)

        # Write transcript to file
        transcript_file_path = os.path.join(settings.BASE_DIR, f"transcripts/{video_proto.id}")
        with open(transcript_file_path, "w") as f:
            f.write(video_proto.transcript)

        # Create object in database
        video_db = await Video.objects.acreate(
            id=video_proto.id,
            url=f"https://www.youtube.com/watch?v={video_proto.id}",
            title=video_proto.title,
            transcript=transcript_file_path,
            channel=ch,
            publication_date=video_proto.publication_date.ToDatetime(tzinfo=timezone.utc),
            category=cat
        )

        await msg.ack()
    await nc.close()
    return 0

if __name__ == "__main__":
    asyncio.run(pull_messages())
