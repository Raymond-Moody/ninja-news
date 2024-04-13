import asyncio
from celery import shared_task
from .producer import push_videos
from .consumer import pull_messages

@shared_task
def producer():
    asyncio.run(push_videos())

@shared_task
def consumer():
    asyncio.run(pull_messages())
