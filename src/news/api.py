from ninja import NinjaAPI, Schema
from .models import Video
from django.shortcuts import render
from django.conf import settings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio

api = NinjaAPI()

@api.get("")
def home(request):
    return render(request, "news/home.html")

@api.get("/latest")
def latest(request):
    """
    Render a Datatable (tablerio) of all the videos
    """
    queryset = Video.objects.all()
    context = {
        "video_list" : queryset
    }
    return render(request, "news/latest.html", context)

@api.get("/summarize")
async def summarize(request):
    """
    Checks for videos with blank summaries
    Creates a summary if necessary, and store embeddings of the transcripts for later use
    """

    # Create the langchain chain
    prompt = ChatPromptTemplate.from_template("""Summarize the following transcript. In your response, refer to the transcript as 'this video'.
    Transcript:
    {input}
    """)
    llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-3.5-turbo-0125")
    output_parser = StrOutputParser()

    chain = prompt | llm | output_parser

    summaries = {}
    async for video in Video.objects.all():
        if not video.summary: # Check for blank summary end generate one if necessary
            with open(video.transcript,"r") as f:
                transcript = f.read()
            response = await chain.ainvoke({"input" : transcript})
            video.summary = response
            await video.asave()
        summaries[video.id] = video.summary
    return summaries

class ChatSchema(Schema):
    message: str = ""

@api.post("/chat")
def chat(request, data: ChatSchema):
    return data.message

