// Socket.IO connection
const socket = io();

// DOM Elements
const startButton = document.getElementById('start-meeting');
const endButton = document.getElementById('end-meeting');
const transcriptContainer = document.getElementById('transcript-container');
const statusIndicator = document.getElementById('status-indicator');
const summaryContainer = document.getElementById('summary-container');

// State
let isRecording = false;

// Event Listeners
startButton.addEventListener('click', startMeeting);
endButton.addEventListener('click', endMeeting);

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    updateStatus('Connected to server', 'info');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateStatus('Disconnected from server', 'error');
});

socket.on('transcript_update', (data) => {
    console.log('Received transcript update:', data);
    addTranscriptEntry(data);
});

// Functions
function startMeeting() {
    if (isRecording) return;
    
    fetch('/start_meeting', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            isRecording = true;
            updateStatus('Recording in progress...', 'recording');
            startButton.disabled = true;
            endButton.disabled = false;
        } else {
            updateStatus(`Error: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        console.error('Error starting meeting:', error);
        updateStatus('Error starting meeting', 'error');
    });
}

function endMeeting() {
    if (!isRecording) return;
    
    fetch('/end_meeting', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            isRecording = false;
            updateStatus('Meeting ended', 'info');
            startButton.disabled = false;
            endButton.disabled = true;
            
            if (data.summary) {
                displaySummary(data.summary);
            }
        } else {
            updateStatus(`Error: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        console.error('Error ending meeting:', error);
        updateStatus('Error ending meeting', 'error');
    });
}

function addTranscriptEntry(data) {
    const entry = document.createElement('div');
    entry.className = 'transcript-entry';
    
    const timestamp = document.createElement('span');
    timestamp.className = 'timestamp';
    timestamp.textContent = `[${data.timestamp}] `;
    
    const speaker = document.createElement('span');
    speaker.className = 'speaker';
    speaker.textContent = `${data.speaker}: `;
    
    const text = document.createElement('span');
    text.className = 'text';
    text.textContent = data.text;
    
    entry.appendChild(timestamp);
    entry.appendChild(speaker);
    entry.appendChild(text);
    
    transcriptContainer.appendChild(entry);
    transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
}

function updateStatus(message, type) {
    statusIndicator.textContent = message;
    statusIndicator.className = `status ${type}`;
}

function displaySummary(summary) {
    summaryContainer.innerHTML = `
        <h3>Meeting Summary</h3>
        <div class="summary-content">${summary}</div>
    `;
    summaryContainer.style.display = 'block';
}

// Initialize UI state
endButton.disabled = true;
updateStatus('Ready to start meeting', 'info'); 