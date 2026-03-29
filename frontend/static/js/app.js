// frontend/static/js/app.js
/**
 * ROSIE Dashboard - Main Application Module
 * Version: 2.0.0 (Modular)
 */
console.log("✅ app.js loaded");
export default class App {
    constructor() {
        // Core state - ?? getter ?????
        this._workflowNodes = [];
        this._workflowEdges = [];
        this._selectedNode = null;
        this._selectedEdge = null;
        this._isConnectingMode = false;
        this._connectingFromNode = null;
        this._connectingFromPort = null;
        this._nodeCounter = 1;
        this._edgeCounter = 1;
        this._socket = null;
        
        // Data storage
        this.initialState = {
            "input_data": "Hello, World!",
            "counter": 0,
            "items": [],
            "config": {
                "debug": false,
                "max_iterations": 10
            }
        };
        
        // Undo/Redo history
        this._operationHistory = {
            undoStack: [],
            redoStack: [],
            MAX_STEPS: 50
        };
        
        // Modules
        this.modules = {};
        
        // Code templates
        this.codeTemplates = {
            simple_transform: `def process(state, params=None):
    """
    Simple data transformation node.
    Access input from state, process, and return modified state.
    """
    # Get input data from state
    input_data = state.get('input_data', '')

    # Perform transformation
    if isinstance(input_data, str):
        processed = input_data.upper()  # Example: convert to uppercase
    else:
        processed = str(input_data)

    # Update state with output
    state['output_data'] = processed
    state['processed_at'] = new Date().isoformat()

    # Log for debugging
    print(f"Processed data: {processed}")

    return state`,

            text_processor: `def process(state, params=None):
    """
    Text processing node with parameters.
    params should contain: {'operation': 'reverse|split|count'}
    """
    # Get input text
    text = state.get('text', state.get('input_data', ''))

    # Get parameters
    operation = 'reverse'
    if params:
        operation = params.get('operation', 'reverse')

    # Perform operation
    if operation == 'reverse':
        result = text[::-1]
    elif operation == 'split':
        result = text.split()
    elif operation == 'count':
        result = len(text)
    elif operation == 'uppercase':
        result = text.upper()
    elif operation == 'lowercase':
        result = text.lower()
    else:
        result = f"Unknown operation: {operation}"

    # Update state
    state['processed_text'] = result
    state['operation'] = operation

    return state`,

            math_operation: `def process(state, params=None):
    """
    Mathematical operation node.
    Expects: state['numbers'] = [1, 2, 3, ...]
    """
    # Get numbers from state
    numbers = state.get('numbers', [])

    # Get operation from params or default
    operation = 'sum'
    if params:
        operation = params.get('operation', 'sum')

    # Perform calculation
    result = None
    if operation == 'sum':
        result = sum(numbers)
    elif operation == 'average':
        result = sum(numbers) / len(numbers) if numbers else 0
    elif operation == 'max':
        result = max(numbers) if numbers else 0
    elif operation == 'min':
        result = min(numbers) if numbers else 0
    elif operation == 'product':
        import math
        result = math.prod(numbers) if numbers else 0

    # Update state
    state['calculation_result'] = result
    state['calculation_type'] = operation

    return state`,

            list_processor: `def process(state, params=None):
    """
    List processing node with filtering/mapping.
    """
    # Get list from state
    items = state.get('items', [])

    # Get parameters
    filter_condition = None
    map_function = None

    if params:
        filter_condition = params.get('filter')
        map_function = params.get('map')

    # Process list
    processed = items

    # Apply filter if specified
    if filter_condition:
        # Example filter: lambda x: x > 0
        try:
            # Note: In real implementation, you'd need safer eval
            # For demo, we use simple condition
            processed = [item for item in processed if item > 0]
        except:
            pass

    # Apply map if specified
    if map_function == 'double':
        processed = [item * 2 for item in processed]
    elif map_function == 'square':
        processed = [item ** 2 for item in processed]
    elif map_function == 'stringify':
        processed = [str(item) for item in processed]

    # Update state
    state['processed_items'] = processed
    state['original_count'] = len(items)
    state['processed_count'] = len(processed)

    return state`,

            http_request: `def process(state, params=None):
    """
    HTTP request node (simplified).
    In production, you'd use requests library.
    """
    import json
    import urllib.request

    # Get URL from params or state
    url = ''
    if params:
        url = params.get('url', '')
    if not url:
        url = state.get('api_url', 'https://jsonplaceholder.typicode.com/todos/1')

    # Make request (simplified for demo)
    try:
        # In real implementation:
        # import requests
        # response = requests.get(url, timeout=10)
        # data = response.json()

        # For demo, return mock data
        data = {
            "userId": 1,
            "id": 1,
            "title": "delectus aut autem",
            "completed": False,
            "url": url,
            "status": "success"
        }

        # Update state
        state['api_response'] = data
        state['request_url'] = url
        state['request_success'] = True

    except Exception as e:
        state['api_error'] = str(e)
        state['request_success'] = False

    return state`
        };
    }

    // ============ GETTERS/SETTERS ============
    get workflowNodes() { return this._workflowNodes; }
    set workflowNodes(nodes) { this._workflowNodes = nodes; }
    
    get workflowEdges() { return this._workflowEdges; }
    set workflowEdges(edges) { this._workflowEdges = edges; }
    
    get selectedNode() { return this._selectedNode; }
    set selectedNode(node) { this._selectedNode = node; }
    
    get selectedEdge() { return this._selectedEdge; }
    set selectedEdge(edge) { this._selectedEdge = edge; }
    
    get isConnectingMode() { return this._isConnectingMode; }
    set isConnectingMode(mode) { this._isConnectingMode = mode; }
    
    get connectingFromNode() { return this._connectingFromNode; }
    set connectingFromNode(node) { this._connectingFromNode = node; }
    
    get connectingFromPort() { return this._connectingFromPort; }
    set connectingFromPort(port) { this._connectingFromPort = port; }
    
    get nodeCounter() { return this._nodeCounter; }
    set nodeCounter(counter) { this._nodeCounter = counter; }
    
    get edgeCounter() { return this._edgeCounter; }
    set edgeCounter(counter) { this._edgeCounter = counter; }
    
    get socket() { return this._socket; }
    set socket(socket) { this._socket = socket; }
    
    get operationHistory() { return this._operationHistory; }
    set operationHistory(history) { this._operationHistory = history; }

    // ============ INITIALIZATION ============
    initialize() {
        console.log('Initializing ROSIE Dashboard...');
        this.loadNodes();
        this.connectWebSocket();
        this.setupDragAndDrop();
        this.setupEventListeners();
        this.updateNodeCountDisplay();
        this.updateEdgeCountDisplay();
        this.updateUndoRedoButtons();
        this.log('System ready. Drag nodes from sidebar to start building.');
        this.log('Double-click any node to edit its Python code.');
        this.log('Click "Connect Nodes" to create connections between nodes.');
        this.log('Click "Set Initial Data" to define initial state for execution.');
    }

    registerModule(name, module) {
        this.modules[name] = module;
    }

    // ============ EVENT LISTENERS ============
    setupEventListeners() {
        // Canvas click to deselect
        const canvas = document.getElementById('canvas');
        if (canvas) {
            canvas.addEventListener('click', (e) => {
                if (e.target === canvas || e.target.id === 'edges-container' || e.target.tagName === 'svg') {
                    this.deselectAll();
                }
            });
        }
        
        // Modal backdrop clicks
        const codeModal = document.getElementById('code-modal');
        if (codeModal) {
            codeModal.addEventListener('click', (e) => {
                if (e.target === codeModal) {
                    this.closeModal();
                }
            });
        }
        
        const initialDataModal = document.getElementById('initial-data-modal');
        if (initialDataModal) {
            initialDataModal.addEventListener('click', (e) => {
                if (e.target === initialDataModal) {
                    this.closeModal();
                }
            });
        }
        
        const resultsModal = document.getElementById('results-modal');
        if (resultsModal) {
            resultsModal.addEventListener('click', (e) => {
                if (e.target === resultsModal) {
                    document.getElementById('results-modal').classList.remove('active');
                }
            });
        }
        
        // Escape key handler
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.isConnectingMode && this.modules.connectionManager) {
                    this.modules.connectionManager.resetConnectingMode();
                } else {
                    this.closeModal();
                    document.getElementById('initial-data-modal').classList.remove('active');
                    document.getElementById('results-modal').classList.remove('active');
                }
            }
        });
    }

    deselectAll() {
        document.querySelectorAll('.edge').forEach(edge => edge.classList.remove('selected'));
        document.getElementById('delete-edge-btn').style.display = 'none';
        this.selectedEdge = null;
        
        document.querySelectorAll('.canvas-node').forEach(node => {
            const nodeId = node.dataset.nodeId;
            const nodeObj = this.workflowNodes.find(n => n.elementId === node.id);
            if (nodeObj) {
                node.style.borderColor = nodeObj.color || this.getNodeColor(nodeId);
            } else {
                node.style.borderColor = this.getNodeColor(nodeId);
            }
            node.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        });
        document.getElementById('delete-node-btn').style.display = 'none';
        this.selectedNode = null;
    }

    // ============ NODE MANAGEMENT ============
    createNewNode() {
        const newNodeId = `node_${Date.now()}`;
        const defaultName = `Node ${Date.now().toString().slice(-4)}`;
        
        // Create the node item in the sidebar
        const nodeItem = document.createElement('div');
        nodeItem.className = 'node-item';
        nodeItem.setAttribute('data-type', 'custom');
        nodeItem.setAttribute('data-id', newNodeId);
        nodeItem.draggable = true;
        nodeItem.innerHTML = `
            <i class="fas fa-plus" style="color: #F59E0B;"></i>
            <span>${defaultName}</span>
            <div style="margin-left: auto;">
                <button class="btn btn-sm btn-secondary" onclick="window.rosieApp.editCustomNode('${newNodeId}', event)" style="padding: 2px 6px; font-size: 10px;">
                    <i class="fas fa-edit"></i>
                </button>
            </div>
        `;
        
        const yourNodesDiv = document.getElementById('your-nodes');
        const emptyMessage = yourNodesDiv.querySelector('div[style*="text-align: center"]');
        
        if (emptyMessage) {
            yourNodesDiv.innerHTML = '';
        }
        
        yourNodesDiv.appendChild(nodeItem);
        
        const yourNodesCount = yourNodesDiv.querySelectorAll('.node-item').length;
        document.getElementById('your-nodes-count').textContent = yourNodesCount;
        
        this.setupDragAndDropForNode(nodeItem);
        this.saveCustomNodeToStorage(newNodeId, defaultName, true);
        this.log(`Created new node: ${defaultName} (ID: ${newNodeId})`);
    }

    setupDragAndDropForNode(nodeElement) {
        nodeElement.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('nodeType', this.dataset.type || 'custom');
            e.dataTransfer.setData('nodeId', this.dataset.id);
            e.dataTransfer.setData('source', 'sidebar');
        });
    }

    editCustomNode(nodeId, event) {
        if (event) event.stopPropagation();
        
        const customNodes = JSON.parse(localStorage.getItem('customNodes') || '[]');
        const node = customNodes.find(n => n.id === nodeId);
        
        document.getElementById('modal-title').textContent = `Edit Node: ${node ? node.name : nodeId}`;
        
        if (node && node.code) {
            document.getElementById('code-editor').value = node.code;
        } else {
            document.getElementById('code-editor').value = `def process(state, params=None):
    """
    Custom node function.
    Modify this function to implement your logic.
    """
    # Get data from state
    input_data = state.get('input_data', '')
    
    # Your logic here
    processed_data = f"Processed: {input_data}"
    
    # Update state
    state['output_data'] = processed_data
    
    return state`;
        }
        
        if (node) {
            document.getElementById('node-display-name').value = node.name || '';
            document.getElementById('node-type-select').value = node.type || 'custom';
            document.getElementById('node-icon-select').value = node.icon || 'plus';
            document.getElementById('node-color-select').value = node.color || '#F59E0B';
            document.getElementById('node-id-display').value = nodeId;
        }
        
        document.getElementById('code-modal').classList.add('active');
        this.selectedNode = nodeId;
        this.switchTab('code');
        
        setTimeout(() => {
            document.getElementById('code-editor').focus();
        }, 100);
    }

    saveCustomNodeToStorage(nodeId, nodeName, isNew = false) {
        const existingNodes = JSON.parse(localStorage.getItem('customNodes') || '[]');
        const nodeIndex = existingNodes.findIndex(n => n.id === nodeId);
        
        if (nodeIndex === -1 || isNew) {
            const newNode = {
                id: nodeId,
                name: nodeName || `Node ${nodeId.slice(-4)}`,
                type: 'custom',
                icon: 'plus',
                color: '#F59E0B',
                code: `def process(state, params=None):
    # Custom node function
    # Your logic here
    return state`,
                created: new Date().toISOString(),
                lastModified: new Date().toISOString()
            };
            
            if (nodeIndex !== -1 && !isNew) {
                newNode.name = existingNodes[nodeIndex].name || nodeName;
                newNode.icon = existingNodes[nodeIndex].icon || 'plus';
                newNode.color = existingNodes[nodeIndex].color || '#F59E0B';
                newNode.code = existingNodes[nodeIndex].code || newNode.code;
                newNode.created = existingNodes[nodeIndex].created || new Date().toISOString();
                existingNodes[nodeIndex] = newNode;
            } else {
                existingNodes.push(newNode);
            }
        }
        
        localStorage.setItem('customNodes', JSON.stringify(existingNodes));
    }

    loadNodes() {
        try {
            const customNodes = JSON.parse(localStorage.getItem('customNodes') || '[]');
            const yourNodesDiv = document.getElementById('your-nodes');
            yourNodesDiv.innerHTML = '';
            
            customNodes.forEach(node => {
                if (node.type === 'custom') {
                    const div = document.createElement('div');
                    div.className = 'node-item';
                    div.setAttribute('data-type', node.type);
                    div.setAttribute('data-id', node.id);
                    div.draggable = true;
                    
                    const displayName = node.name || node.id;
                    const displayIcon = node.icon || 'plus';
                    const displayColor = node.color || '#F59E0B';
                    
                    div.innerHTML = `
                        <i class="fas fa-${displayIcon}" style="color: ${displayColor};"></i>
                        <span>${displayName}</span>
                        <div style="margin-left: auto;">
                            <button class="btn btn-sm btn-secondary" onclick="window.rosieApp.editCustomNode('${node.id}', event)" style="padding: 2px 6px; font-size: 10px;">
                                <i class="fas fa-edit"></i>
                            </button>
                        </div>
                    `;
                    yourNodesDiv.appendChild(div);
                }
            });
            
            const yourNodesCount = yourNodesDiv.querySelectorAll('.node-item').length;
            document.getElementById('your-nodes-count').textContent = yourNodesCount;
            
            if (yourNodesCount === 0) {
                yourNodesDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #666; font-size: 14px;">No nodes yet. Click "New Node" to create one.</div>';
            }
            
            this.setupDragAndDrop();
            
        } catch (error) {
            console.error('Failed to load nodes:', error);
            this.log('Error loading nodes: ' + error.message);
        }
    }

    // ============ DRAG AND DROP ============
    setupDragAndDrop() {
        const nodeItems = document.querySelectorAll('.node-item');
        const canvas = document.getElementById('canvas');
        
        nodeItems.forEach(item => {
            item.addEventListener('dragstart', function(e) {
                e.dataTransfer.setData('nodeType', this.dataset.type || 'custom');
                e.dataTransfer.setData('nodeId', this.dataset.id || 'custom_' + Date.now());
                e.dataTransfer.setData('source', 'sidebar');
            });
        });
        
        canvas.addEventListener('dragover', function(e) {
            e.preventDefault();
            canvas.style.borderColor = '#667eea';
        });
        
        canvas.addEventListener('dragleave', function() {
            canvas.style.borderColor = '#ccc';
        });
        
        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            canvas.style.borderColor = '#ccc';
            
            const source = e.dataTransfer.getData('source');
            const nodeType = e.dataTransfer.getData('nodeType');
            const nodeId = e.dataTransfer.getData('nodeId');
            
            if (source === 'sidebar' && nodeId) {
                this.addNodeToCanvas(nodeId, nodeType, e.clientX, e.clientY);
            }
        }.bind(this));
    }

    // ============ CANVAS OPERATIONS ============
    addNodeToCanvas(nodeId, nodeType, clientX, clientY) {
        const canvas = document.getElementById('canvas');
        const rect = canvas.getBoundingClientRect();
        const x = clientX - rect.left - 60;
        const y = clientY - rect.top - 30;
        
        // Check if node already exists on canvas
        const existingNode = this.workflowNodes.find(n => n.id === nodeId);
        if (existingNode) {
            const nodeElement = document.getElementById(existingNode.elementId);
            if (nodeElement) {
                nodeElement.style.left = x + 'px';
                nodeElement.style.top = y + 'px';
                existingNode.x = x;
                existingNode.y = y;
                this.updateAllEdges();
                this.log(`Moved existing node: ${existingNode.name || nodeId} to (${x}, ${y})`);
            }
            return existingNode;
        }
        
        const nodeElement = document.createElement('div');
        nodeElement.className = `canvas-node ${nodeType}`;
        nodeElement.id = `canvas-${nodeId}-${this.nodeCounter++}`;
        nodeElement.dataset.nodeId = nodeId;
        nodeElement.style.left = x + 'px';
        nodeElement.style.top = y + 'px';
        
        let nodeName, nodeIcon, nodeColor;
        
        if (nodeId === 'start') {
            nodeName = 'Start';
            nodeIcon = 'play';
            nodeColor = '#10B981';
        } else if (nodeId === 'end') {
            nodeName = 'End';
            nodeIcon = 'stop';
            nodeColor = '#EF4444';
        } else if (nodeId === 'custom') {
            nodeName = 'Custom Node';
            nodeIcon = 'plus';
            nodeColor = '#F59E0B';
        } else {
            const customNodes = JSON.parse(localStorage.getItem('customNodes') || '[]');
            const nodeInfo = customNodes.find(n => n.id === nodeId);
            
            if (nodeInfo) {
                nodeName = nodeInfo.name || `Node ${nodeId.slice(-4)}`;
                nodeIcon = nodeInfo.icon || 'plus';
                nodeColor = nodeInfo.color || '#F59E0B';
            } else {
                nodeName = `Node ${nodeId.slice(-4)}`;
                nodeIcon = 'plus';
                nodeColor = '#F59E0B';
                this.saveCustomNodeToStorage(nodeId, nodeName, true);
            }
        }

        let inputPort = '', outputPort = '';
        if (nodeId === 'start') {
            outputPort = '<div class="port output" data-port-type="output"><div class="port-tooltip">Output</div></div>';
            inputPort = '<div class="port" style="visibility: hidden;"></div>';
        } else if (nodeId === 'end') {
            inputPort = '<div class="port input" data-port-type="input"><div class="port-tooltip">Input</div></div>';
            outputPort = '<div class="port" style="visibility: hidden;"></div>';
        } else {
            inputPort = '<div class="port input" data-port-type="input"><div class="port-tooltip">Input</div></div>';
            outputPort = '<div class="port output" data-port-type="output"><div class="port-tooltip">Output</div></div>';
        }

        nodeElement.innerHTML = `
            <div style="position: relative; height: 100%;">
                <div><i class="fas fa-${nodeIcon}" style="color: ${nodeColor}; font-size: 24px;"></i></div>
                <div style="margin-top: 8px; font-size: 12px; font-weight: 600; color: #333;">${nodeName}</div>
                <div style="font-size: 9px; color: #999; margin-top: 2px; opacity: 0.7;">ID: ${nodeId}</div>
                <div class="node-ports">
                    ${inputPort}
                    <div style="font-size: 8px; color: #999; margin-top: 3px;">${nodeType}</div>
                    ${outputPort}
                </div>
            </div>
        `;

        // Make node draggable with real-time edge updates
        this.makeDraggable(nodeElement, nodeId);
        
        // Double-click to edit
        nodeElement.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            this.editNodeCode(nodeId);
        });

        // Click to select
        nodeElement.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectNode(nodeElement);
        });

        // Setup port click handlers
        const inputPortEl = nodeElement.querySelector('.port.input');
        const outputPortEl = nodeElement.querySelector('.port.output');

        if (inputPortEl) {
            inputPortEl.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handlePortClick(nodeId, 'input', inputPortEl);
            });
        }

        if (outputPortEl) {
            outputPortEl.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handlePortClick(nodeId, 'output', outputPortEl);
            });
        }

        canvas.appendChild(nodeElement);
        document.getElementById('canvas-empty-state').style.display = 'none';

        const nodeObj = {
            id: nodeId,
            type: nodeType,
            x: x,
            y: y,
            name: nodeName,
            icon: nodeIcon,
            color: nodeColor,
            elementId: nodeElement.id
        };
        
        this.workflowNodes.push(nodeObj);
        this.updateNodeCountDisplay();
        this.log(`Added node to canvas: ${nodeName} (ID: ${nodeId})`);
        
        // Record operation for undo/redo
        if (this.modules.undoRedoManager) {
            this.modules.undoRedoManager.recordOperation({
                type: 'add_node',
                data: JSON.parse(JSON.stringify(nodeObj)),
                timestamp: new Date().toISOString()
            });
        }

        return nodeObj;
    }

    makeDraggable(nodeElement, nodeId) {
        let isDragging = false;
        
        nodeElement.draggable = true;
        
        nodeElement.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('nodeId', nodeId);
            e.dataTransfer.setData('canvasNodeId', this.id);
            e.dataTransfer.setData('source', 'canvas');
            e.dataTransfer.effectAllowed = 'move';
            isDragging = true;
        });
        
        // Real-time edge updates during drag
        nodeElement.addEventListener('drag', function(e) {
            if (!isDragging || e.clientX === 0 && e.clientY === 0) return;
            
            const canvas = document.getElementById('canvas');
            const canvasRect = canvas.getBoundingClientRect();
            const newX = e.clientX - canvasRect.left - 60;
            const newY = e.clientY - canvasRect.top - 30;
            
            this.style.left = newX + 'px';
            this.style.top = newY + 'px';
            this.updateAllEdges();
        }.bind(this));
        
        nodeElement.addEventListener('dragend', (e) => {
            isDragging = false;
            
            const canvas = document.getElementById('canvas');
            const canvasRect = canvas.getBoundingClientRect();
            const newX = e.clientX - canvasRect.left - 60;
            const newY = e.clientY - canvasRect.top - 30;
            
            if (newX >= 0 && newY >= 0 && 
                newX <= canvasRect.width - 120 && 
                newY <= canvasRect.height - 80) {
                nodeElement.style.left = newX + 'px';
                nodeElement.style.top = newY + 'px';
                
                const nodeObj = this.workflowNodes.find(n => n.elementId === nodeElement.id);
                if (nodeObj) {
                    const oldX = nodeObj.x;
                    const oldY = nodeObj.y;
                    
                    nodeObj.x = newX;
                    nodeObj.y = newY;
                    
                    if (this.modules.undoRedoManager) {
                        this.modules.undoRedoManager.recordOperation({
                            type: 'move_node',
                            data: {
                                nodeId: nodeObj.id,
                                oldX: oldX,
                                oldY: oldY,
                                newX: newX,
                                newY: newY,
                                elementId: nodeObj.elementId,
                                name: nodeObj.name,
                                icon: nodeObj.icon,
                                color: nodeObj.color,
                                type: nodeObj.type
                            },
                            timestamp: new Date().toISOString()
                        });
                    }
                }
                
                this.updateAllEdges();
            }
        }.bind(this));
    }

    selectNode(nodeElement) {
        document.querySelectorAll('.canvas-node').forEach(node => {
            const nodeId = node.dataset.nodeId;
            const nodeObj = this.workflowNodes.find(n => n.elementId === node.id);
            if (nodeObj) {
                node.style.borderColor = nodeObj.color || this.getNodeColor(nodeId);
            } else {
                node.style.borderColor = this.getNodeColor(nodeId);
            }
            node.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        });
        
        nodeElement.style.borderColor = '#EF4444';
        nodeElement.style.boxShadow = '0 0 0 3px rgba(239,68,68,0.3)';
        
        this.selectedNode = nodeElement.id;
        document.getElementById('delete-node-btn').style.display = 'inline-flex';
        this.log(`Selected node: ${this.selectedNode}`);
    }

    deleteSelectedNode() {
        if (!this.selectedNode) return;

        const nodeIndex = this.workflowNodes.findIndex(n => n.elementId === this.selectedNode);
        if (nodeIndex === -1) return;

        const node = this.workflowNodes[nodeIndex];

        if (this.modules.undoRedoManager) {
            this.modules.undoRedoManager.recordOperation({
                type: 'delete_node',
                data: JSON.parse(JSON.stringify(node)),
                timestamp: new Date().toISOString()
            });
        }

        const nodeElement = document.getElementById(node.elementId);
        if (nodeElement && nodeElement.parentNode) {
            nodeElement.parentNode.removeChild(nodeElement);
        }

        const edgesToDelete = this.workflowEdges.filter(edge =>
            edge.source === node.id || edge.target === node.id
        );

        edgesToDelete.forEach(edge => {
            if (this.modules.undoRedoManager) {
                this.modules.undoRedoManager.recordOperation({
                    type: 'delete_edge',
                    data: JSON.parse(JSON.stringify(edge)),
                    timestamp: new Date().toISOString()
                });
            }

            const edgeElement = document.getElementById(edge.id);
            if (edgeElement && edgeElement.parentNode) {
                edgeElement.parentNode.removeChild(edgeElement);
            }
        });

        this.workflowEdges = this.workflowEdges.filter(edge =>
            edge.source !== node.id && edge.target !== node.id
        );

        this.workflowNodes.splice(nodeIndex, 1);

        this.updateNodeCountDisplay();
        this.updateEdgeCountDisplay();

        if (this.workflowNodes.length === 0) {
            document.getElementById('canvas-empty-state').style.display = 'flex';
        }

        this.log(`Deleted node: ${node.id}, removed ${edgesToDelete.length} edges`);

        document.getElementById('delete-node-btn').style.display = 'none';
        this.selectedNode = null;
    }

    getNodeColor(nodeId) {
        const node = this.workflowNodes.find(n => n.id === nodeId);
        if (node) return node.color || '#667eea';
        
        if (nodeId === 'start') return '#10B981';
        if (nodeId === 'end') return '#EF4444';
        return '#667eea';
    }

    // ============ CONNECTION MANAGEMENT ============
    handlePortClick(nodeId, portType, portElement) {
        if (this.modules.connectionManager) {
            this.modules.connectionManager.handlePortClick(nodeId, portType, portElement);
        }
    }

    resetConnectingMode() {
        if (this.modules.connectionManager) {
            this.modules.connectionManager.resetConnectingMode();
        } else {
            this.isConnectingMode = false;
            this.connectingFromNode = null;
            this.connectingFromPort = null;

            document.querySelectorAll('.port').forEach(port => {
                if (port.classList.contains('input')) {
                    port.style.backgroundColor = '#10B981';
                } else if (port.classList.contains('output')) {
                    port.style.backgroundColor = '#3B82F6';
                }
            });

            document.getElementById('mode-indicator').textContent = 'Normal';
            document.getElementById('mode-indicator').classList.remove('mode-connecting');
        }
    }

    // ============ EDGE MANAGEMENT ============
    createEdge(sourceNodeId, targetNodeId) {
        console.log('Creating edge from', sourceNodeId, 'to', targetNodeId);
        const edgeId = `edge-${this.edgeCounter++}`;
        const edge = {
            id: edgeId,
            source: sourceNodeId,
            target: targetNodeId,
            sourcePort: 'output',
            targetPort: 'input'
        };

        this.workflowEdges.push(edge);
        this.drawEdge(edge);
        this.updateEdgeCountDisplay();
        this.log(`Created connection: ${sourceNodeId} ? ${targetNodeId}`);
        
        if (this.modules.undoRedoManager) {
            this.modules.undoRedoManager.recordOperation({
                type: 'add_edge',
                data: JSON.parse(JSON.stringify(edge)),
                timestamp: new Date().toISOString()
            });
        }
        
        return edge;
    }

    drawEdge(edge) {
        const sourceNode = this.workflowNodes.find(n => n.id === edge.source);
        const targetNode = this.workflowNodes.find(n => n.id === edge.target);

        if (!sourceNode || !targetNode) {
            console.error('Node not found:', edge.source, 'or', edge.target);
            return;
        }

        const sourceElement = document.getElementById(sourceNode.elementId);
        const targetElement = document.getElementById(targetNode.elementId);

        if (!sourceElement || !targetElement) {
            console.error('Element not found:', sourceNode.elementId, 'or', targetNode.elementId);
            return;
        }

        const sourceRect = sourceElement.getBoundingClientRect();
        const targetRect = targetElement.getBoundingClientRect();
        const canvasRect = document.getElementById('canvas').getBoundingClientRect();

        const sourceX = sourceRect.left - canvasRect.left + sourceRect.width;
        const sourceY = sourceRect.top - canvasRect.top + sourceRect.height / 2;
        const targetX = targetRect.left - canvasRect.left;
        const targetY = targetRect.top - canvasRect.top + targetRect.height / 2;

        const svgNS = "http://www.w3.org/2000/svg";
        const edgeGroup = document.createElementNS(svgNS, "g");
        edgeGroup.id = edge.id;
        edgeGroup.classList.add('edge');

        const path = document.createElementNS(svgNS, "path");
        path.classList.add('edge-line');

        const marker = document.createElementNS(svgNS, "marker");
        marker.id = `arrow-${edge.id}`;
        marker.setAttribute("markerWidth", "10");
        marker.setAttribute("markerHeight", "10");
        marker.setAttribute("refX", "9");
        marker.setAttribute("refY", "3");
        marker.setAttribute("orient", "auto");
        marker.setAttribute("markerUnits", "strokeWidth");

        const arrow = document.createElementNS(svgNS, "path");
        arrow.setAttribute("d", "M0,0 L0,6 L9,3 z");
        arrow.classList.add('edge-arrow');
        marker.appendChild(arrow);

        let defs = document.querySelector('#edges-container defs');
        if (!defs) {
            defs = document.createElementNS(svgNS, "defs");
            document.getElementById('edges-container').appendChild(defs);
        }
        defs.appendChild(marker);

        path.setAttribute("marker-end", `url(#arrow-${edge.id})`);

        const controlX1 = sourceX + 50;
        const controlY1 = sourceY;
        const controlX2 = targetX - 50;
        const controlY2 = targetY;

        const pathData = `M ${sourceX} ${sourceY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${targetX} ${targetY}`;
        path.setAttribute("d", pathData);

        edgeGroup.appendChild(path);
        document.getElementById('edges-container').appendChild(edgeGroup);

        edgeGroup.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectEdge(edge.id);
        });

        edge.element = edgeGroup;
        edge.path = path;
        edge.sourceElement = sourceElement;
        edge.targetElement = targetElement;
    }

    updateAllEdges() {
        this.workflowEdges.forEach(edge => {
            if (edge.element && edge.path) {
                const sourceNode = this.workflowNodes.find(n => n.id === edge.source);
                const targetNode = this.workflowNodes.find(n => n.id === edge.target);
                
                if (!sourceNode || !targetNode) return;
                
                const sourceElement = document.getElementById(sourceNode.elementId);
                const targetElement = document.getElementById(targetNode.elementId);
                
                if (!sourceElement || !targetElement) return;
                
                const canvasRect = document.getElementById('canvas').getBoundingClientRect();
                const sourceRect = sourceElement.getBoundingClientRect();
                const sourceX = sourceRect.left - canvasRect.left + sourceRect.width;
                const sourceY = sourceRect.top - canvasRect.top + sourceRect.height / 2;
                
                const targetRect = targetElement.getBoundingClientRect();
                const targetX = targetRect.left - canvasRect.left;
                const targetY = targetRect.top - canvasRect.top + targetRect.height / 2;
                
                const controlX1 = sourceX + 50;
                const controlY1 = sourceY;
                const controlX2 = targetX - 50;
                const controlY2 = targetY;
                
                const pathData = `M ${sourceX} ${sourceY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${targetX} ${targetY}`;
                edge.path.setAttribute("d", pathData);
            }
        });
    }

    selectEdge(edgeId) {
        document.querySelectorAll('.edge').forEach(edge => edge.classList.remove('selected'));
        const edgeElement = document.getElementById(edgeId);
        if (edgeElement) {
            edgeElement.classList.add('selected');
            this.selectedEdge = edgeId;
            document.getElementById('delete-edge-btn').style.display = 'inline-flex';
            this.log(`Selected edge: ${edgeId}`);
        }
    }

    deleteSelectedEdge() {
        if (!this.selectedEdge) return;

        const edgeIndex = this.workflowEdges.findIndex(edge => edge.id === this.selectedEdge);
        if (edgeIndex !== -1) {
            const edge = this.workflowEdges[edgeIndex];
            
            if (this.modules.undoRedoManager) {
                this.modules.undoRedoManager.recordOperation({
                    type: 'delete_edge',
                    data: JSON.parse(JSON.stringify(edge)),
                    timestamp: new Date().toISOString()
                });
            }

            if (edge.element && edge.element.parentNode) {
                edge.element.parentNode.removeChild(edge.element);
            }

            this.workflowEdges.splice(edgeIndex, 1);
            this.log(`Deleted edge: ${this.selectedEdge}`);
            this.updateEdgeCountDisplay();
            document.getElementById('delete-edge-btn').style.display = 'none';
            this.selectedEdge = null;
        }
    }

    // ============ CODE EDITOR ============
    editNodeCode(nodeId) {
        const customNodes = JSON.parse(localStorage.getItem('customNodes') || '[]');
        const node = customNodes.find(n => n.id === nodeId);
        
        if (node) {
            document.getElementById('modal-title').textContent = `Edit Node: ${node.name || nodeId}`;
            document.getElementById('code-editor').value = node.code || '';
            document.getElementById('node-display-name').value = node.name || '';
            document.getElementById('node-type-select').value = node.type || 'custom';
            document.getElementById('node-icon-select').value = node.icon || 'plus';
            document.getElementById('node-color-select').value = node.color || '#F59E0B';
            document.getElementById('node-id-display').value = nodeId;
        } else {
            let displayName = nodeId.charAt(0).toUpperCase() + nodeId.slice(1);
            if (nodeId === 'custom') displayName = 'Custom Node';
            
            document.getElementById('modal-title').textContent = `Edit Node: ${displayName}`;
            document.getElementById('code-editor').value = `def process(state, params=None):
    """
    ${displayName} node function.
    """
    return state`;
            
            document.getElementById('node-display-name').value = displayName;
            document.getElementById('node-type-select').value = nodeId;
            document.getElementById('node-icon-select').value = nodeId === 'start' ? 'play' : nodeId === 'end' ? 'stop' : 'plus';
            document.getElementById('node-color-select').value = nodeId === 'start' ? '#10B981' : nodeId === 'end' ? '#EF4444' : '#F59E0B';
            document.getElementById('node-id-display').value = nodeId;
        }
        
        document.getElementById('code-modal').classList.add('active');
        this.selectedNode = nodeId;
        this.switchTab('code');
        setTimeout(() => document.getElementById('code-editor').focus(), 100);
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        // Find the tab with the correct onclick attribute
        const tabs = document.querySelectorAll('.tab');
        tabs.forEach(tab => {
            if (tab.getAttribute('onclick') && tab.getAttribute('onclick').includes(tabName)) {
                tab.classList.add('active');
            }
        });
        
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }

    loadTemplate() {
        const templateName = document.getElementById('template-selector').value;
        if (templateName && this.codeTemplates[templateName]) {
            document.getElementById('template-preview').textContent = this.codeTemplates[templateName];
        }
    }

    applyParams() {
        const inputKey = document.getElementById('input-key').value;
        const outputKey = document.getElementById('output-key').value;
        const timeout = document.getElementById('timeout').value;

        if (inputKey || outputKey) {
            let code = document.getElementById('code-editor').value;
            if (!code.includes('def process')) {
                code = `def process(state, params=None):
    # Node: ${this.selectedNode}
    # Input key: ${inputKey}
    # Output key: ${outputKey}
    # Timeout: ${timeout}s
    
    return state`;
            }
            document.getElementById('code-editor').value = code;
            this.log(`Applied parameters to ${this.selectedNode}`);
        }
    }

    applyNodeProperties() {
        const nodeName = document.getElementById('node-display-name').value;
        const nodeType = document.getElementById('node-type-select').value;
        const nodeIcon = document.getElementById('node-icon-select').value;
        const nodeColor = document.getElementById('node-color-select').value;
        
        if (!this.selectedNode) return;
        
        const customNodes = JSON.parse(localStorage.getItem('customNodes') || '[]');
        const nodeIndex = customNodes.findIndex(n => n.id === this.selectedNode);
        
        if (nodeIndex !== -1) {
            customNodes[nodeIndex].name = nodeName || `Node ${this.selectedNode.slice(-4)}`;
            customNodes[nodeIndex].type = nodeType;
            customNodes[nodeIndex].icon = nodeIcon;
            customNodes[nodeIndex].color = nodeColor;
            customNodes[nodeIndex].lastModified = new Date().toISOString();
            localStorage.setItem('customNodes', JSON.stringify(customNodes));
        } else if (this.selectedNode.startsWith('node_')) {
            customNodes.push({
                id: this.selectedNode,
                name: nodeName || `Node ${this.selectedNode.slice(-4)}`,
                type: nodeType,
                icon: nodeIcon,
                color: nodeColor,
                code: document.getElementById('code-editor').value || '',
                created: new Date().toISOString(),
                lastModified: new Date().toISOString()
            });
            localStorage.setItem('customNodes', JSON.stringify(customNodes));
        }
        
        const canvasNode = this.workflowNodes.find(n => n.id === this.selectedNode);
        if (canvasNode) {
            canvasNode.name = nodeName || `Node ${this.selectedNode.slice(-4)}`;
            canvasNode.type = nodeType;
            canvasNode.icon = nodeIcon;
            canvasNode.color = nodeColor;
            this.updateCanvasNodeDisplay(canvasNode);
        }
        
        this.loadNodes();
        this.log(`Updated properties for node: ${nodeName || this.selectedNode}`);
    }

    updateCanvasNodeDisplay(canvasNode) {
        const nodeElement = document.getElementById(canvasNode.elementId);
        if (!nodeElement) return;
        
        const iconElement = nodeElement.querySelector('i');
        if (iconElement) {
            iconElement.className = `fas fa-${canvasNode.icon}`;
            iconElement.style.color = canvasNode.color;
        }
        
        const nameElement = nodeElement.querySelector('div[style*="margin-top: 8px"]');
        if (nameElement) {
            nameElement.textContent = canvasNode.name || canvasNode.id;
        }
        
        nodeElement.className = `canvas-node ${canvasNode.type}`;
    }

    saveNodeCode() {
        if (!this.selectedNode) return;
        const code = document.getElementById('code-editor').value;

        if (!code.trim()) {
            alert('Please write some code before saving!');
            return;
        }

        if (!code.includes('def process(')) {
            if (!confirm('Code does not contain a "process" function. Save anyway?')) {
                return;
            }
        }

        const customNodes = JSON.parse(localStorage.getItem('customNodes') || '[]');
        const nodeIndex = customNodes.findIndex(n => n.id === this.selectedNode);
        
        const nodeName = document.getElementById('node-display-name').value;
        const nodeType = document.getElementById('node-type-select').value;
        const nodeIcon = document.getElementById('node-icon-select').value;
        const nodeColor = document.getElementById('node-color-select').value;
        
        if (nodeIndex !== -1) {
            customNodes[nodeIndex].code = code;
            if (nodeName) customNodes[nodeIndex].name = nodeName;
            if (nodeType) customNodes[nodeIndex].type = nodeType;
            if (nodeIcon) customNodes[nodeIndex].icon = nodeIcon;
            if (nodeColor) customNodes[nodeIndex].color = nodeColor;
            customNodes[nodeIndex].lastModified = new Date().toISOString();
            localStorage.setItem('customNodes', JSON.stringify(customNodes));
        } else if (this.selectedNode.startsWith('node_')) {
            customNodes.push({
                id: this.selectedNode,
                name: nodeName || `Node ${this.selectedNode.slice(-4)}`,
                type: nodeType || 'custom',
                icon: nodeIcon || 'plus',
                color: nodeColor || '#F59E0B',
                code: code,
                created: new Date().toISOString(),
                lastModified: new Date().toISOString()
            });
            localStorage.setItem('customNodes', JSON.stringify(customNodes));
        }
        
        const canvasNode = this.workflowNodes.find(n => n.id === this.selectedNode);
        if (canvasNode) {
            canvasNode.name = nodeName || `Node ${this.selectedNode.slice(-4)}`;
            canvasNode.type = nodeType || 'custom';
            canvasNode.icon = nodeIcon || 'plus';
            canvasNode.color = nodeColor || '#F59E0B';
            this.updateCanvasNodeDisplay(canvasNode);
        }
        
        this.closeModal();
        this.log(`Code saved for ${nodeName || this.selectedNode}`);
        this.loadNodes();
    }

    // ============ MODAL FUNCTIONS ============
    closeModal() {
        document.getElementById('code-modal').classList.remove('active');
        document.getElementById('initial-data-modal').classList.remove('active');
        this.selectedNode = null;
    }

    showInitialDataModal() {
        document.getElementById('initial-data-modal').classList.add('active');
        document.getElementById('initial-data-editor').value = JSON.stringify(this.initialState, null, 2);
    }

    saveInitialData() {
        try {
            const dataText = document.getElementById('initial-data-editor').value;
            this.initialState = JSON.parse(dataText);
            this.closeModal();
            this.log('Initial state data saved');
        } catch (error) {
            alert('Invalid JSON format. Please check your data.');
        }
    }

    showResultsModal(results) {
        const container = document.getElementById('results-container');
        if (results.success) {
            const resultsHTML = Object.entries(results.final_state || {}).map(([key, value]) => {
                return `<div class="result-item"><strong>${key}:</strong> ${typeof value === 'object' ? JSON.stringify(value, null, 2) : value}</div>`;
            }).join('');

            container.innerHTML = `
                <h4>Execution Successful!</h4>
                <p>Nodes executed: ${results.nodes_executed || 0}</p>
                <p>Execution time: ${results.execution_time || 'N/A'}</p>
                <div class="result-panel">${resultsHTML}</div>
            `;
        } else {
            container.innerHTML = `
                <h4>Execution Failed!</h4>
                <p style="color: #EF4444;">${results.error || 'Unknown error'}</p>
                <pre style="background: #fee2e2; padding: 10px; border-radius: 4px;">${results.traceback || ''}</pre>
            `;
        }
        document.getElementById('results-modal').classList.add('active');
    }

    // ============ WORKFLOW OPERATIONS ============
    saveWorkflow() {
        if (this.workflowNodes.length === 0) {
            alert('No workflow to save');
            return;
        }

        const workflowData = {
            nodes: this.workflowNodes,
            edges: this.workflowEdges,
            initialState: this.initialState,
            timestamp: new Date().toISOString()
        };

        localStorage.setItem('rosie_workflow', JSON.stringify(workflowData));
        this.log('Workflow saved locally');
        console.log('Workflow data:', workflowData);
    }

    async runWorkflow() {
        if (this.workflowNodes.length === 0) {
            alert('No workflow to run');
            return;
        }

        if (this.workflowEdges.length === 0) {
            if (!confirm('No connections between nodes. Run workflow anyway?')) return;
        }

        this.updateStatus('Running');
        this.log('Starting workflow execution...');

        try {
            // Generate a workflow ID for this execution
            const workflowId = `workflow_${Date.now()}`;

            const response = await fetch(`/api/workflows/${workflowId}/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nodes: this.workflowNodes,
                    edges: this.workflowEdges,
                    initialState: this.initialState
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.log(`Execution started with ID: ${data.execution_id}`);

            // Emit to WebSocket for real-time updates
            if (this.socket) {
                this.socket.emit('execution_started', {
                    execution_id: data.execution_id,
                    workflow_id: workflowId,
                    timestamp: new Date().toISOString()
                });
            }
        } catch (error) {
            console.error('Failed to run workflow:', error);
            this.updateStatus('Error');
            this.log('Error starting workflow: ' + error.message);
        }
    }

    newWorkflow() {
        if (confirm('Create new workflow? Current work will be lost.')) {
            document.querySelectorAll('.canvas-node').forEach(node => node.remove());
            document.querySelectorAll('#edges-container g').forEach(edge => edge.remove());
            
            this.workflowNodes = [];
            this.workflowEdges = [];
            this.selectedNode = null;
            this.selectedEdge = null;
            
            this.updateNodeCountDisplay();
            this.updateEdgeCountDisplay();
            document.getElementById('canvas-empty-state').style.display = 'flex';
            document.getElementById('workflow-title').textContent = 'New Workflow';
            this.log('Created new workflow');
        }
    }

    loadWorkflow() {
        try {
            const saved = localStorage.getItem('rosie_workflow');
            if (!saved) {
                alert('No saved workflow found');
                return;
            }
            
            const workflowData = JSON.parse(saved);
            this.newWorkflow();
            
            workflowData.nodes.forEach(nodeData => {
                this.addNodeToCanvas(nodeData.id, nodeData.type, nodeData.x + 60, nodeData.y + 30);
            });
            
            workflowData.edges.forEach(edge => {
                this.createEdge(edge.source, edge.target);
            });
            
            if (workflowData.initialState) {
                this.initialState = workflowData.initialState;
            }
            
            document.getElementById('workflow-title').textContent = 
                `Loaded Workflow (${new Date(workflowData.timestamp).toLocaleString()})`;
            
            this.log(`Workflow loaded: ${workflowData.nodes.length} nodes, ${workflowData.edges.length} edges`);
        } catch (error) {
            console.error('Failed to load workflow:', error);
            alert('Error loading workflow');
        }
    }

    // ============ WEBSOCKET ============
    connectWebSocket() {
        this.socket = io();
        this.socket.on('connect', () => this.log('Connected to test_ROSIE server'));
        this.socket.on('connected', (data) => this.log(data.message || 'Connected to server'));
        this.socket.on('execution_start', (data) => {
            this.log(`Execution ${data.execution_id} started`);
            this.updateStatus('Running');
        });
        this.socket.on('node_progress', (data) => {
            const progress = data.progress ? ` (${Math.round(data.progress)}%)` : '';
            this.log(`${data.message}${progress}`);
        });
        this.socket.on('execution_complete', (data) => {
            this.log(`Execution completed: ${data.message}`);
            this.updateStatus('Ready');
            this.showResultsModal(data.results);
        });
        this.socket.on('execution_error', (data) => {
            this.log(`Error: ${data.error}`);
            this.updateStatus('Error');
        });
    }

    // ============ UI UPDATES ============
    updateNodeCountDisplay() {
        const count = this.workflowNodes.length;
        document.getElementById('node-count-display').textContent = `${count} node${count !== 1 ? 's' : ''}`;
    }

    updateEdgeCountDisplay() {
        const count = this.workflowEdges.length;
        document.getElementById('edge-count-display').textContent = `${count} connection${count !== 1 ? 's' : ''}`;
    }

    updateUndoRedoButtons() {
        const undoBtn = document.getElementById('undo-btn');
        const redoBtn = document.getElementById('redo-btn');
        if (undoBtn && redoBtn) {
            const canUndo = this.operationHistory.undoStack.length > 0;
            const canRedo = this.operationHistory.redoStack.length > 0;
            undoBtn.disabled = !canUndo;
            redoBtn.disabled = !canRedo;
            undoBtn.title = `Undo (${this.operationHistory.undoStack.length} available)`;
            redoBtn.title = `Redo (${this.operationHistory.redoStack.length} available)`;
        }
    }

    updateStatus(status) {
        const statusDiv = document.getElementById('status');
        if (statusDiv) {
            statusDiv.textContent = status;
            statusDiv.className = 'status status-' + status.toLowerCase();
        }
    }

    log(message) {
        const logPanel = document.getElementById('log-panel');
        const entry = document.createElement('div');
        const time = new Date().toLocaleTimeString();
        entry.textContent = `[${time}] ${message}`;
        logPanel.appendChild(entry);
        logPanel.scrollTop = logPanel.scrollHeight;
    }
}