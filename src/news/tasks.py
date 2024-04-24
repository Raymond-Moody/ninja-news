import os
import asyncio
from celery import shared_task
from .producer import push_videos
from .consumer import pull_messages
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_postgres.vectorstores import PGVector
from langchain_community.document_loaders import DirectoryLoader, TextLoader
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

@shared_task
def populate_pgvector():
    """
    Populate the vector database with the transcripts
    This task should only be run once
    """
    vectorstore = PGVector(
        embeddings=OpenAIEmbeddings(model="text-embedding-3-large", api_key=settings.OPENAI_API_KEY),
        collection_name="news",
        connection="postgresql+psycopg://langchain:langchain@pgvector:5432/langchain",
        use_jsonb=True,
    ) 

    # Just in case this task was run before, drop tables to prevent inserting videos twice
    #vectorstore.drop_tables()

    # Create document loader for transcript directory
    transcript_path = os.path.join(settings.BASE_DIR, "transcripts/")
    loader = DirectoryLoader(transcript_path, loader_cls=TextLoader)
    docs = loader.load()

    vectorstore.add_documents(docs)

    #Test the vectors
    print(vectorstore.similarity_search("Ukraine"))
