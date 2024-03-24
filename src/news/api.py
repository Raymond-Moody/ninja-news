from ninja import NinjaAPI
from django.shortcuts import render

api = NinjaAPI()

@api.get("")
def home(request):
    return render(request, "news/home.html")
