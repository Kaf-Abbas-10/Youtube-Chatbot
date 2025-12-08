import os
from langchain_huggingface import HuggingFaceEmbeddings
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Use environment variable instead of hardcoded key
api_key = os.getenv("GROQ_API_KEY")

video_id = "Gfr50f6ZBvo"
try:
    api = YouTubeTranscriptApi()
    transcript_list = api.fetch(video_id, languages=['en'])
    
    transcript = " ".join(chunk.text for chunk in transcript_list)
    #print(transcript)

except TranscriptsDisabled:
    print("No captions available for this video")
except Exception as e:
    print(f"Error fetching transcript: {e}")
    print(f"Error type: {type(e)}")
    
    if 'transcript_list' in locals() and len(transcript_list) > 0:
        print("\nAvailable attributes on transcript snippet:")
        print(dir(transcript_list[0]))

# Document Splitting
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_text(transcript)
print(len(chunks))

# Embeddings And Storing
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
vectorstore = FAISS.from_texts(chunks, embeddings)

retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})

def format_docs(retrieved_docs):
    context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)
    return context_text

parallel_chain = RunnableParallel({
    'context': retriever | RunnableLambda(format_docs),
    'question': RunnablePassthrough()
})

llm = ChatGroq(api_key=api_key,
               model="llama-3.1-8b-instant"
               )

prompt = PromptTemplate(
    template="""
		You are a helpful assistant.
        Answer ONLY from the provided transcript context.
        If the context is insufficient, just say you don't know.
        
        Context: {context}
        Question: {question}
	""",
    input_variables = ['context', 'question']
)

parser = StrOutputParser()

main_chain = parallel_chain | prompt | llm | parser

print(main_chain.invoke("Can you summarize the video"))