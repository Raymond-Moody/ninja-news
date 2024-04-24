import asyncio
from celery import shared_task
from .producer import push_videos
from .consumer import pull_messages
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from django.conf import settings
from news.models import Video

@shared_task
def producer():
    asyncio.run(push_videos())

@shared_task
def consumer():
    asyncio.run(pull_messages())

@shared_task
def generate_summaries():
    """
    Checks for videos with blank summaries and creates a summary if necessary
    Returns a dictionary of summaries in the format {video_id : summary}
    """

    async def get_summary(video):
        # Create the langchain chain
        prompt = ChatPromptTemplate.from_template("""Summarize the following transcript. In your response, refer to the transcript as 'this video'.
        Transcript:
        {input}
        """)
        llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-3.5-turbo-0125")
        output_parser = StrOutputParser()

        chain = prompt | llm | output_parser

        with open(video.transcript,"r") as f:
            transcript = f.read()
        response = await chain.ainvoke({"input" : transcript})
        video.summary = response
        await video.asave()

    summaries = {}
    for video in Video.objects.all():
        if not video.summary: # Check for blank summary end generate one if necessary
            asyncio.run(get_summary(video))
        summaries[video.id] = video.summary
    return summaries
