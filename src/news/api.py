from ninja import NinjaAPI, Schema
from .models import Video
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
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
    Checks for videos with blank summaries and creates a summary if necessary
    Returns a dictionary of summaries in the format {video_id : summary}
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

@api.get("/summary_html/{video_id}")
def summary_html(request, video_id: str):
    """
    Returns the transcript and summary for a given video as html for the /latest template to render
    """
    response = HttpResponse()
    try:
        video = Video.objects.get(pk=video_id)
        with open(video.transcript, "r") as f:
            transcript = f.read()
        transcript = transcript.replace("\n"," ")
        response.write('<div class="row row-deck">')
        response.write(
            f"""
            <div class="col-md-6">
                <div class="card">
                    <div class="card-status-top bg-blue"></div>
                    <div class="card-body">
                        <h3 class="card-title">Transcript</h3>
                        <p class="text-secondary">{transcript}</p>
                    </div>
                </div>
            </div>
            """
        )
        response.write(
            f"""
            <div class="col-md-6">
                <div class="card">
                    <div class="card-status-top bg-green"></div>
                    <div class="card-body">
                        <h3 class="card-title">Summary</h3>
                        <p class="text-secondary">{video.summary}</p>
                    </div>
                </div>
            </div>
            """
        )
        response.write("</div>")
    except ObjectDoesNotExist:
        response.write(f"Video with id {video_id} does not exist")

    print(response)
    return response

@api.get("/title/{video_id}")
def title(request, video_id: str):
    """
    Returns the title of the given video. Used to update the summary modal's title
    """
    try:
        video = Video.objects.get(pk=video_id)
        return HttpResponse(video.title)
    except ObjectDoesNotExist:
        return HttpResponse(f"Video with id {video_id} does not exist")

class ChatSchema(Schema):
    message: str = ""

@api.post("/chat")
def chat(request, data: ChatSchema):
    return data.message

