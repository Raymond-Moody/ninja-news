from ninja import NinjaAPI, Schema
from .models import Video
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
from news.tasks import generate_summaries

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
def summarize(request):
    summaries = generate_summaries.delay()
    return summaries.get()
    

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

