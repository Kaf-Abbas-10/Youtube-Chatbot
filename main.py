import os

from langchain_huggingface import HuggingFaceEmbeddings
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Use environment variable instead of hardcoded key
api_key = os.getenv("GROQ_API_KEY")

video_id = "Gfr50f6ZBvo"
#video_id = "X0btK9X0Xnk"

# Transcript Fetching
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

#print(vectorstore.index_to_docstore_id)
print(vectorstore.get_by_ids(["8a99a01f-3d59-4540-806d-cec6a7a313d0"][0]))


# Retrieval
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})
retrieved_docs = retriever.invoke("What is deepmind")
print(retrieved_docs)
