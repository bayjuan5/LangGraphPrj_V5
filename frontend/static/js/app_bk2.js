// frontend/static/js/app.js

class App {
    constructor() {
        this.currentWorkflow = null;
        this.workflowId = null;
        this.initialState = {};
        
        // Module references (will be set by index.html)
        this.websocketClient = null;
        this.nodeManager = null;
        this.connectionManager = null;
        this.codeEditor = null;
        this.undoRedoManager = null;
        
        this.init();
    }
    
    init() {
        console.log('Initializing App...');
        
        this.setupEventListeners();
        this.updateStatus('Ready');
        
        console.log('App initialized');
    }
    
    setupEventListeners() {
        // New Workflow
        const newWorkflowBtn = document.getElementById('new-workflow-btn');
        if (newWorkflowBtn) {
            newWorkflowBtn.addEventListener('click', () => this.newWorkflow());
        }
        
        // Load Workflow
        const loadWorkflowBtn = document.getElementById('load-workflow-btn');
        if (loadWorkflowBtn) {
            loadWorkflowBtn.addEventListener('click', () => this.loadWorkflowDialog());
        }
        
        // Save Workflow
        const saveWorkflowBtn = document.getElementById('save-workflow-btn');
        if (saveWorkflowBtn) {
            saveWorkflowBtn.addEventListener('click', () => this.saveWorkflow());
        }
        
        // Run Workflow
        const runWorkflowBtn = document.getElementById('run-workflow-btn');
        if (runWorkflowBtn) {
            runWorkflowBtn.addEventListener('click', () => this.runWorkflow());
        }
        
        // Set Initial Data
        const initialDataBtn = document.getElementById('initial-data-btn');
        if (initialDataBtn) {
            initialDataBtn.addEventListener('click', () => this.openInitialDataDialog());
        }
    }
    
    newWorkflow() {
        if (confirm('Create a new workflow? Any unsaved changes will be lost.')) {
            // Clear everything
            if (this.nodeManager) {
                this.nodeManager.clearAllNodes();
            }
            if (this.connectionManager) {
                this.connectionManager.clearAllEdges();
            }
            
            this.currentWorkflow = null;
            this.workflowId = null;
            this.initialState = {};
            
            document.getElementById('workflow-title').textContent = 'New Workflow';
            this.log('Created new workflow');
        }
    }
    
    async loadWorkflowDialog() {
        try {
            const response = await fetch('/api/workflows');
            const data = await response.json();
            
            if (!data.workflows || data.workflows.length === 0) {
                alert('No workflows found');
                return;
            }
            
            // Create dialog
            const dialog = this.createWorkflowListDialog(data.workflows);
            document.body.appendChild(dialog);
            
        } catch (error) {
            console.error('Error loading workflows:', error);
            alert('Failed to load workflows');
        }
    }
    
    createWorkflowListDialog(workflows) {
        const dialog = document.createElement('div');
        dialog.className = 'modal';
        dialog.style.display = 'flex';
        
        let workflowListHTML = '';
        workflows.forEach(wf => {
            workflowListHTML += `
                <div class="workflow-item" data-id="${wf.id}">
                    <h4>${wf.name}</h4>
                    <p>${wf.description || 'No description'}</p>
                    <small>Updated: ${new Date(wf.updated_at).toLocaleString()}</small>
                    <button class="btn btn-sm btn-primary load-wf-btn" data-id="${wf.id}">Load</button>
                </div>
            `;
        });
        
        dialog.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Load Workflow</h3>
                    <button class="btn btn-secondary close-dialog-btn">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="workflow-list">
                        ${workflowListHTML}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary close-dialog-btn">Cancel</button>
                </div>
            </div>
        `;
        
        // Event listeners
        dialog.querySelectorAll('.close-dialog-btn').forEach(btn => {
            btn.addEventListener('click', () => dialog.remove());
        });
        
        dialog.querySelectorAll('.load-wf-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const workflowId = e.target.getAttribute('data-id');
                await this.loadWorkflow(workflowId);
                dialog.remove();
            });
        });
        
        return dialog;
    }
    
    async loadWorkflow(workflowId) {
        try {
            const response = await fetch(`/api/workflows/${workflowId}`);
            const workflow = await response.json();
            
            // Clear current workflow
            if (this.nodeManager) {
                this.nodeManager.clearAllNodes();
            }
            if (this.connectionManager) {
                this.connectionManager.clearAllEdges();
            }
            
            // Load nodes
            if (workflow.nodes && this.nodeManager) {
                workflow.nodes.forEach(node => {
                    this.nodeManager.addNodeToCanvas(node);
                });
            }
            
            // Load edges
            if (workflow.edges && this.connectionManager) {
                workflow.edges.forEach(edge => {
                    this.connectionManager.createEdge(edge.source, edge.target, edge.id);
                });
            }
            
            // Update UI
            this.currentWorkflow = workflow;
            this.workflowId = workflowId;
            document.getElementById('workflow-title').textContent = workflow.name;
            
            this.log(`Loaded workflow: ${workflow.name}`);
            
        } catch (error) {
            console.error('Error loading workflow:', error);
            alert('Failed to load workflow');
        }
    }
    
    async saveWorkflow() {
        const workflowName = prompt('Enter workflow name:', 
            this.currentWorkflow ? this.currentWorkflow.name : 'New Workflow');
        
        if (!workflowName) return;
        
        const workflowData = {
            name: workflowName,
            description: prompt('Enter description (optional):') || '',
            nodes: this.nodeManager ? this.nodeManager.getAllNodes() : [],
            edges: this.connectionManager ? this.connectionManager.getAllEdges() : [],
            is_public: true
        };
        
        try {
            let response;
            if (this.workflowId) {
                // Update existing
                response = await fetch(`/api/workflows/${this.workflowId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(workflowData)
                });
            } else {
                // Create new
                response = await fetch('/api/workflows', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(workflowData)
                });
            }
            
            const result = await response.json();
            
            if (response.ok) {
                this.currentWorkflow = result.workflow;
                this.workflowId = result.workflow.id;
                document.getElementById('workflow-title').textContent = workflowName;
                
                this.log(`Saved workflow: ${workflowName}`);
                alert('Workflow saved successfully!');
            } else {
                throw new Error(result.error || 'Failed to save');
            }
            
        } catch (error) {
            console.error('Error saving workflow:', error);
            alert('Failed to save workflow: ' + error.message);
        }
    }
    
    async runWorkflow() {
        if (!this.workflowId) {
            alert('Please save the workflow first');
            return;
        }
        
        try {
            this.updateStatus('Running...');
            
            const response = await fetch(`/api/workflows/${this.workflowId}/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: this.initialState })
            });
            
            const result = await response.json();
            
            this.log(`Started execution: ${result.execution_id}`);
            
            // Results will come via WebSocket
            
        } catch (error) {
            console.error('Error running workflow:', error);
            alert('Failed to run workflow');
            this.updateStatus('Error');
        }
    }
    
    openInitialDataDialog() {
        const modal = document.getElementById('initial-data-modal');
        const editor = document.getElementById('initial-data-editor');
        
        if (modal && editor) {
            editor.value = JSON.stringify(this.initialState, null, 2);
            modal.style.display = 'flex';
            
            // Setup close buttons
            const closeButtons = modal.querySelectorAll('#close-initial-data-btn, #cancel-initial-data-btn');
            closeButtons.forEach(btn => {
                btn.onclick = () => modal.style.display = 'none';
            });
            
            // Save button
            const saveBtn = document.getElementById('save-initial-data-btn');
            if (saveBtn) {
                saveBtn.onclick = () => {
                    try {
                        this.initialState = JSON.parse(editor.value);
                        this.log('Initial state data saved');
                        modal.style.display = 'none';
                    } catch (error) {
                        alert('Invalid JSON format');
                    }
                };
            }
        }
    }
    
    showResults(results) {
        const modal = document.getElementById('results-modal');
        const container = document.getElementById('results-container');
        
        if (modal && container) {
            container.innerHTML = `
                <div class="results-content">
                    <h4>Execution Completed</h4>
                    <div class="result-item">
                        <strong>Status:</strong> ${results.status}
                    </div>
                    <div class="result-item">
                        <strong>Workflow:</strong> ${results.result.workflow_name || 'N/A'}
                    </div>
                    <div class="result-item">
                        <strong>Nodes Executed:</strong> ${results.result.nodes_executed || 0}
                    </div>
                    <div class="result-item">
                        <strong>Execution Time:</strong> ${results.result.execution_time || 'N/A'}
                    </div>
                    <div class="result-item">
                        <strong>Output:</strong>
                        <pre>${JSON.stringify(results.result.output, null, 2)}</pre>
                    </div>
                </div>
            `;
            
            modal.style.display = 'flex';
            
            // Setup close buttons
            const closeButtons = modal.querySelectorAll('#close-results-btn, #close-results-modal-btn');
            closeButtons.forEach(btn => {
                btn.onclick = () => modal.style.display = 'none';
            });
        }
        
        this.updateStatus('Completed');
    }
    
    updateStatus(status) {
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = 'status';
            
            if (status === 'Ready') {
                statusElement.classList.add('status-ready');
            } else if (status === 'Running...') {
                statusElement.classList.add('status-running');
            } else if (status === 'Completed') {
                statusElement.classList.add('status-success');
            } else if (status === 'Error') {
                statusElement.classList.add('status-error');
            }
        }
    }
    
    log(message) {
        const logPanel = document.getElementById('log-panel');
        if (logPanel) {
            const logEntry = document.createElement('div');
            logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logPanel.appendChild(logEntry);
            logPanel.scrollTop = logPanel.scrollHeight;
        }
        console.log(message);
    }
}

export default App;