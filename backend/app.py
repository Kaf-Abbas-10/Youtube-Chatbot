from flask import Flask, request, jsonify
from flask_cors import CORS
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

app = Flask(__name__)
CORS(app)

api_key = os.getenv("GROQ_API_KEY")

# Store video sessions in memory (in production, use Redis or database)
video_sessions = {}

def get_youtube_transcript(video_id):
    """Fetch transcript for a YouTube video"""
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.fetch(video_id, languages=['en'])
        transcript = " ".join(chunk.text for chunk in transcript_list)
        return transcript, None
    except TranscriptsDisabled:
        return None, "No captions available for this video"
    except Exception as e:
        return None, f"Error fetching transcript: {str(e)}"

def create_chain_for_video(video_id):
    """Create a RAG chain for a specific video"""
    if video_id in video_sessions:
        return video_sessions[video_id], None
    
    # Fetch transcript
    transcript, error = get_youtube_transcript(video_id)
    if error:
        return None, error
    
    # Document Splitting
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(transcript)
    
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
    
    llm = ChatGroq(api_key=api_key, model="llama-3.1-8b-instant")
    
    prompt = PromptTemplate(
        template="""
        You are a helpful assistant.
        Answer ONLY from the provided transcript context.
        If the context is insufficient, just say you don't know.
        
        Context: {context}
        Question: {question}
        """,
        input_variables=['context', 'question']
    )
    
    parser = StrOutputParser()
    
    main_chain = parallel_chain | prompt | llm | parser
    
    # Store in session
    video_sessions[video_id] = main_chain
    
    return main_chain, None

@app.route('/api/initialize', methods=['POST'])
def initialize_video():
    """Initialize a video for chatting"""
    data = request.json
    video_id = data.get('video_id')
    
    if not video_id:
        return jsonify({'error': 'video_id is required'}), 400
    
    chain, error = create_chain_for_video(video_id)
    
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'success': True,
        'message': 'Video initialized successfully',
        'video_id': video_id
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat with the video"""
    data = request.json
    video_id = data.get('video_id')
    question = data.get('question')
    
    if not video_id or not question:
        return jsonify({'error': 'video_id and question are required'}), 400
    
    # Get or create chain
    chain, error = create_chain_for_video(video_id)
    
    if error:
        return jsonify({'error': error}), 400
    
    try:
        response = chain.invoke(question)
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        return jsonify({'error': f'Error processing question: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)