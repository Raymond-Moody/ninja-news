from ninja import NinjaAPI
from .models import Video
from django.shortcuts import render

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
    return render(request, "news/home.html")

@api.get("/chat")
def chat(request):
    return render(request, "news/home.html")

