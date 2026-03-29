// frontend/static/js/websocket-client.js
/**
 * WebSocket Client Module
 * Handles real-time communication with server
 */

export default class WebSocketClient {
    constructor(app) {
        this.app = app;
        this.socket = null;
        this.connected = false;
        this.connect();
    }
    
    connect() {
        console.log('Connecting to WebSocket...');
        
        // Get socket path from config or use default
        const socketPath = window.LangGraphConfig?.socketIoPath || '/socket.io';
        this.socket = io(socketPath);
        
        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.connected = true;
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            this.connected = false;
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('connected', (data) => {
            console.log('Server connection established:', data);
            this.app.log(`Connected to server: ${data.message}`);
        });
        
        this.socket.on('error', (error) => {
            console.error('WebSocket error:', error);
            this.app.log(`WebSocket error: ${error}`);
        });
        
        // Workflow execution events
        this.socket.on('execution_started', (data) => {
            console.log('Execution started:', data);
            this.app.log(`Execution ${data.execution_id} started`);
            this.app.updateStatus('Running');
        });
        
        this.socket.on('execution_progress', (data) => {
            console.log('Execution progress:', data);
            const progress = data.progress ? ` (${Math.round(data.progress)}%)` : '';
            this.app.log(`${data.message}${progress}`);
        });
        
        this.socket.on('execution_completed', (data) => {
            console.log('Execution completed:', data);
            this.app.log(`Execution completed: ${data.message}`);
            this.app.updateStatus('Ready');
            this.showResultsModal(data.result || data.results);
        });
        
        this.socket.on('execution_error', (data) => {
            console.error('Execution error:', data);
            this.app.log(`Error: ${data.error}`);
            this.app.updateStatus('Error');
        });
    }
    
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
            if (connected) {
                statusEl.innerHTML = '<i class="fas fa-circle" style="color: #10b981;"></i> Connected';
            } else {
                statusEl.innerHTML = '<i class="fas fa-circle" style="color: #ef4444;"></i> Disconnected';
            }
        }
    }
    
    emit(event, data) {
        if (this.connected && this.socket) {
            this.socket.emit(event, data);
        } else {
            console.warn('Cannot emit event, socket not connected');
        }
    }
    
    on(event, callback) {
        if (this.socket) {
            this.socket.on(event, callback);
        }
    }
    
    showResultsModal(results) {
        const container = document.getElementById('results-container');
        container.innerHTML = '';

        if (results.success) {
            const resultsHTML = Object.entries(results.final_state || {}).map(([key, value]) => {
                return `
                    <div class="result-item">
                        <strong>${key}:</strong> ${typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
                    </div>
                `;
            }).join('');

            container.innerHTML = `
                <h4>Execution Successful!</h4>
                <p>Nodes executed: ${results.nodes_executed || 0}</p>
                <p>Execution time: ${results.execution_time || 'N/A'}</p>
                <div class="result-panel">
                    ${resultsHTML}
                </div>
            `;
        } else {
            container.innerHTML = `
                <h4>Execution Failed!</h4>
                <p style="color: #EF4444;">${results.error || 'Unknown error'}</p>
                <pre style="background: #fee2e2; padding: 10px; border-radius: 4px;">${results.traceback || ''}</pre>
            `;
        }

        document.getElementById('results-modal').classList.add('active');
        
        // Setup results modal event listeners
        this.setupResultsModalListeners();
    }
    
    setupResultsModalListeners() {
        const closeResultsBtn = document.getElementById('close-results-btn');
        if (closeResultsBtn) {
            closeResultsBtn.addEventListener('click', () => {
                document.getElementById('results-modal').classList.remove('active');
            });
        }
        
        const closeResultsModalBtn = document.getElementById('close-results-modal-btn');
        if (closeResultsModalBtn) {
            closeResultsModalBtn.addEventListener('click', () => {
                document.getElementById('results-modal').classList.remove('active');
            });
        }
        
        const exportResultsBtn = document.getElementById('export-results-btn');
        if (exportResultsBtn) {
            exportResultsBtn.addEventListener('click', () => {
                alert('Export feature coming soon!');
            });
        }
        
        // Modal backdrop click
        const resultsModal = document.getElementById('results-modal');
        if (resultsModal) {
            resultsModal.addEventListener('click', (e) => {
                if (e.target === resultsModal) {
                    document.getElementById('results-modal').classList.remove('active');
                }
            });
        }
    }
}