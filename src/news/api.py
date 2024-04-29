import json
from ninja import NinjaAPI, Schema, Form
from .models import Video
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from news.tasks import generate_summaries, populate_pgvector
from langchain_postgres.vectorstores import PGVector
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate, MessagesPlaceholder, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain_core.messages import HumanMessage
from langchain.chains.combine_documents import create_stuff_documents_chain

api = NinjaAPI()

@api.get("")
def home(request):
    return render(request, "news/home.html")

@api.get("/latest")
def latest(request):
    """
    Render a Datatable (tabler.io) of all the videos
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

def generate_chat(message="", history=[]):
    """
    Request a response from OpenAI and stream it back
    """
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

    # Initialize AI Components
    llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-3.5-turbo-0125")

    prompt = """You are an assistant for question-answering tasks.\
    Use the following pieces of retrieved context to answer the question.\
    If you don't know the answer, just say that you don't know. \
    Give complete answers, but keep them concise. Try to include specific data from the context.\
    Also, print the entire context back out Verbatim.\
    
    {context} 
    """

    # Create chain for handling chat history
    contextualize_q_system_prompt = """Given a chat history and the latest user question \
    which might reference context in the chat history, formulate a standalone question \
    which can be understood without the chat history. Do NOT answer the question, \
    just reformulate it if needed and otherwise return it as is."""

    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
    
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])

    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    ai_msg = rag_chain.stream({
        "input" : message,
        "chat_history" : history
    })

    full_ai_msg = ""
    for chunk in ai_msg:
        if "context" in chunk:
            for doc in chunk["context"]:
                source = doc.metadata["source"].split("/")[-1] # Get video id from source file
                try:
                    source_vid = Video.objects.get(pk=source)
                except Video.DoesNotExist:
                    print("Referenced deleted video:", source)
                data = {
                    "quote": doc.page_content,
                    "video": source_vid.title,
                    "channel" : source_vid.channel.name
                }
                data = json.dumps(data)
                yield f'data: {data}\n\n'
        if "answer" in chunk:
            data = {"answer" : chunk["answer"]}
            data = json.dumps(data)
            yield f'data: {data}\n\n'
            full_ai_msg = full_ai_msg + chunk["answer"]
    history.append(full_ai_msg)

@api.get("/chat_backend")
def chat_response(request, message: str):
    """
    Return an http stream of the AI response to the given message
    """
    history = request.session.get("chat_history")
    if not history:
        history = []
    history.append(message)
    result_stream = generate_chat(message, history)
    request.session["chat_history"] = history
    response = StreamingHttpResponse(result_stream, content_type="text/event-stream")
    response['X-Accel-Buffering'] = 'no'
    response['Cache-Control'] = 'no-cache'
    return response

@api.get("/chat")
def chat_frontend(request):
    request.session["chat_history"] = ""
    return render(request, "news/chat.html")

@api.get("/pgvector")
def run_pgvector_task(request):
    populate_pgvector.apply_async()
    return render(request, "news/pgvector.html")
