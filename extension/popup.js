const API_BASE_URL = 'http://localhost:5000/api';

let currentVideoId = null;
let isInitialized = false;

const elements = {
    status: document.getElementById('status'),
    videoInfo: document.getElementById('videoInfo'),
    chatContainer: document.getElementById('chatContainer'),
    questionInput: document.getElementById('questionInput'),
    sendBtn: document.getElementById('sendBtn')
};

// Update status message
function updateStatus(message, type = 'loading') {
    elements.status.textContent = message;
    elements.status.className = `status ${type}`;
}

// Add message to chat
function addMessage(text, isUser = false) {
    // Remove empty state if it exists
    const emptyState = elements.chatContainer.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
    messageDiv.textContent = text;
    elements.chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

// Get video ID from current tab
async function getVideoId() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url || !tab.url.includes('youtube.com/watch')) {
        return null;
    }
    
    const url = new URL(tab.url);
    return url.searchParams.get('v');
}

// Initialize video
async function initializeVideo(videoId) {
    try {
        updateStatus('Loading video transcript...', 'loading');
        
        const response = await fetch(`${API_BASE_URL}/initialize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ video_id: videoId })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to initialize video');
        }
        
        isInitialized = true;
        updateStatus('Ready to chat!', 'success');
        elements.videoInfo.textContent = `Video ID: ${videoId}`;
        elements.videoInfo.classList.add('active');
        elements.questionInput.disabled = false;
        elements.sendBtn.disabled = false;
        elements.questionInput.focus();
        
        return true;
    } catch (error) {
        updateStatus(`Error: ${error.message}`, 'error');
        return false;
    }
}

// Send question
async function sendQuestion(question) {
    if (!question.trim() || !currentVideoId) return;
    
    // Add user message
    addMessage(question, true);
    
    // Clear input
    elements.questionInput.value = '';
    elements.questionInput.disabled = true;
    elements.sendBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                video_id: currentVideoId,
                question: question
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to get response');
        }
        
        // Add bot response
        addMessage(data.response, false);
        
    } catch (error) {
        addMessage(`Error: ${error.message}`, false);
    } finally {
        elements.questionInput.disabled = false;
        elements.sendBtn.disabled = false;
        elements.questionInput.focus();
    }
}

// Event listeners
elements.sendBtn.addEventListener('click', () => {
    const question = elements.questionInput.value;
    sendQuestion(question);
});

elements.questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !elements.sendBtn.disabled) {
        const question = elements.questionInput.value;
        sendQuestion(question);
    }
});

// Initialize on popup open
(async function init() {
    try {
        // Check backend health
        updateStatus('Connecting to backend...', 'loading');
        
        const healthResponse = await fetch(`${API_BASE_URL}/health`);
        if (!healthResponse.ok) {
            throw new Error('Backend server is not running');
        }
        
        // Get video ID
        currentVideoId = await getVideoId();
        
        if (!currentVideoId) {
            updateStatus('Please open a YouTube video', 'error');
            return;
        }
        
        // Initialize video
        await initializeVideo(currentVideoId);
        
    } catch (error) {
        updateStatus(`Error: ${error.message}. Make sure backend is running on port 5000.`, 'error');
    }
})();