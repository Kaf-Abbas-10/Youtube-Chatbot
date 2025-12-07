import os

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
chunks = splitter.create_documents([transcript])
print(len(chunks))

