from ninja import NinjaAPI, Schema, Form
from .models import Video
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
from news.tasks import generate_summaries
from langchain_postgres.vectorstores import PGVector
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

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

class ChatIn(Schema):
    message: str
    #history: str

def generate_chat(message="", history=""):
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Access vector store and create a retriever
    store = PGVector(
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=settings.OPENAI_API_KEY),
        connection = "postgresql+psycopg://langchain:langchain@pgvector:5432/langchain",
        collection_name = "news",
        use_jsonb = True
    )
    retriever = store.as_retriever(search_type="similarity", search_kwargs={"k":6})

    # Create RAG chain
    llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-3.5-turbo-0125")
    prompt = PromptTemplate.from_template("""
    You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Give complete answers, but keep them concise. Try to include specific data from the context.

    Question: {question} 

    Context: {context} 

    Answer:
    """)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    results = ""
    for chunk in rag_chain.stream(message):
        results = results + chunk
    return results

@api.post("/chat_backend")
def render_chat_response(request, data: Form[ChatIn]):
    history = request.session.get("chat_history")
    if history is None:
        request.session["chat_history"] = ""
        history = ""
    request.session["chat_history"] = history + data.message
    #results = generate_chat(data.message)
    response = HttpResponse()
    response.write(f"""
    <div class="row align-items-end justify-content-end">
        <div class="col col-lg-6">
            <div class="chat-bubble chat-bubble-me">
                <div class="chat-bubble-title">
                    <div class="row">
                        <div class="col chat-bubble-author">User</div>
                    </div>
                </div>
                <div class="chat-bubble-body"><p>{data.message}</p></div>
            </div>
        </div>
    </div>
    """)

    response.write(f"""
    <div class="row align-items-end">
        <div class="col col-lg-6">
            <div class="chat-bubble">
                <div class="chat-bubble-title">
                    <div class="row">
                        <div class="col chat-bubble-author">Assistant</div>
                    </div>
                </div>
                <div class="chat-bubble-body"><p>'''{history}'''</p></div>
            </div>
        </div>
    </div>
    """)
    return response

@api.get("/chat")
def chat_frontend(request):
    return render(request, "news/chat.html")






