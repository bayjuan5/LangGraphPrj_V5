// frontend/static/js/app.js
/**
 * ROSIE Dashboard - Main Application Module
 * Version: 1.0.0
 */

// Global state (similar to views.py)
const AppState = {
    workflowNodes: [],
    workflowEdges: [],
    selectedNode: null,
    selectedEdge: null,
    isConnectingMode: false,
    connectingFromNode: null,
    connectingFromPort: null,
    nodeCounter: 1,
    edgeCounter: 1,
    operationHistory: {
        undoStack: [],
        redoStack: [],
        MAX_STEPS: 50
    },
    initialState: {
        "input_data": "Hello, World!",
        "counter": 0,
        "items": [],
        "config": {
            "debug": false,
            "max_iterations": 10
        }
    },
    socket: null
};

// Code templates (from views.py)
const codeTemplates = {
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

export default class App {
    constructor() {
        this.state = JSON.parse(JSON.stringify(AppState));
        this.modules = {};
        
        // Bind methods
        this.log = this.log.bind(this);
        this.updateStatus = this.updateStatus.bind(this);
        this.setupEventListeners = this.setupEventListeners.bind(this);
        this.loadNodes = this.loadNodes.bind(this);
        this.setupDragAndDrop = this.setupDragAndDrop.bind(this);
    }
    
    initialize() {
        console.log('Initializing ROSIE Dashboard App...');
        
        // Load saved nodes
        this.loadNodes();
        
        // Setup drag and drop
        this.setupDragAndDrop();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Update UI
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
        console.log(`Module registered: ${name}`);
    }
    
    // ============ NODE MANAGEMENT ============
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
                            <button class="btn btn-sm btn-secondary edit-node-btn" data-node-id="${node.id}" 
                                    style="padding: 2px 6px; font-size: 10px;">
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
                yourNodesDiv.innerHTML = '<div class="empty-state">No nodes yet. Click "New Node" to create one.</div>';
            }
            
            // Setup edit buttons
            document.querySelectorAll('.edit-node-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const nodeId = btn.getAttribute('data-node-id');
                    this.editCustomNode(nodeId);
                });
            });
            
        } catch (error) {
            console.error('Failed to load nodes:', error);
            this.log('Error loading nodes: ' + error.message);
        }
    }
    
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
                <button class="btn btn-sm btn-secondary edit-node-btn" data-node-id="${newNodeId}" 
                        style="padding: 2px 6px; font-size: 10px;">
                    <i class="fas fa-edit"></i>
                </button>
            </div>
        `;
        
        const yourNodesDiv = document.getElementById('your-nodes');
        const emptyMessage = yourNodesDiv.querySelector('.empty-state');
        
        if (emptyMessage) {
            yourNodesDiv.innerHTML = '';
        }
        
        yourNodesDiv.appendChild(nodeItem);
        
        const yourNodesCount = yourNodesDiv.querySelectorAll('.node-item').length;
        document.getElementById('your-nodes-count').textContent = yourNodesCount;
        
        // Setup edit button
        nodeItem.querySelector('.edit-node-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.editCustomNode(newNodeId);
        });
        
        this.saveCustomNodeToStorage(newNodeId, defaultName, true);
        this.log(`Created new node: ${defaultName} (ID: ${newNodeId})`);
    }
    
    editCustomNode(nodeId, event) {
        if (event) event.stopPropagation();
        
        if (this.modules.codeEditor) {
            this.modules.codeEditor.openEditor(nodeId);
        } else {
            console.warn('Code editor module not available');
        }
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
    
    // ============ CANVAS OPERATIONS ============
    addNodeToCanvas(nodeId, nodeType, clientX, clientY) {
        const canvas = document.getElementById('canvas');
        const rect = canvas.getBoundingClientRect();
        const x = clientX - rect.left - 60;
        const y = clientY - rect.top - 30;
        
        const existingNode = this.state.workflowNodes.find(n => n.id === nodeId);
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
        nodeElement.id = `canvas-${nodeId}-${this.state.nodeCounter++}`;
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

        // Make draggable
        this.makeDraggable(nodeElement, nodeId);
        
        nodeElement.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            this.editCustomNode(nodeId);
        });

        nodeElement.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectNode(nodeElement);
        });

        const inputPortEl = nodeElement.querySelector('.port.input');
        const outputPortEl = nodeElement.querySelector('.port.output');

        if (inputPortEl) {
            inputPortEl.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.modules.connectionManager) {
                    this.modules.connectionManager.handlePortClick(nodeId, 'input', inputPortEl);
                }
            });
        }

        if (outputPortEl) {
            outputPortEl.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.modules.connectionManager) {
                    this.modules.connectionManager.handlePortClick(nodeId, 'output', outputPortEl);
                }
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
        
        this.state.workflowNodes.push(nodeObj);
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
    
    makeDraggable(element, nodeId) {
        let isDragging = false;
        let startX, startY;
        
        element.addEventListener('mousedown', (e) => {
            if (e.target.closest('.port')) return;
            
            isDragging = true;
            startX = e.clientX - element.getBoundingClientRect().left;
            startY = e.clientY - element.getBoundingClientRect().top;
            element.style.cursor = 'grabbing';
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const canvas = document.getElementById('canvas');
            const canvasRect = canvas.getBoundingClientRect();
            
            let x = e.clientX - canvasRect.left - startX;
            let y = e.clientY - canvasRect.top - startY;
            
            // Boundary check
            x = Math.max(0, Math.min(x, canvasRect.width - 120));
            y = Math.max(0, Math.min(y, canvasRect.height - 80));
            
            element.style.left = `${x}px`;
            element.style.top = `${y}px`;
            
            // Update node position
            const node = this.state.workflowNodes.find(n => n.elementId === element.id);
            if (node) {
                node.x = x;
                node.y = y;
            }
            
            this.updateAllEdges();
        });
        
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                element.style.cursor = 'move';
                
                // Record move operation
                const node = this.state.workflowNodes.find(n => n.elementId === element.id);
                if (node && this.modules.undoRedoManager) {
                    // We would record the move here
                }
            }
        });
    }
    
    selectNode(nodeElement) {
        document.querySelectorAll('.canvas-node').forEach(node => {
            const nodeId = node.dataset.nodeId;
            const nodeObj = this.state.workflowNodes.find(n => n.elementId === node.id);
            if (nodeObj) {
                node.style.borderColor = nodeObj.color || this.getNodeColor(nodeId);
            } else {
                node.style.borderColor = this.getNodeColor(nodeId);
            }
            node.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        });
        
        nodeElement.style.borderColor = '#EF4444';
        nodeElement.style.boxShadow = '0 0 0 3px rgba(239,68,68,0.3)';
        
        this.state.selectedNode = nodeElement.id;
        document.getElementById('delete-node-btn').style.display = 'inline-flex';
        
        this.log(`Selected node: ${this.state.selectedNode}`);
    }
    
    getNodeColor(nodeId) {
        const node = this.state.workflowNodes.find(n => n.id === nodeId);
        if (node) return node.color || '#667eea';
        
        if (nodeId === 'start') return '#10B981';
        if (nodeId === 'end') return '#EF4444';
        return '#667eea';
    }
    
    // ============ DRAG AND DROP ============
    setupDragAndDrop() {
        const nodeItems = document.querySelectorAll('.node-item');
        const canvas = document.getElementById('canvas');
        
        nodeItems.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('nodeType', item.getAttribute('data-type') || 'custom');
                e.dataTransfer.setData('nodeId', item.getAttribute('data-id') || 'custom_' + Date.now());
                e.dataTransfer.setData('source', 'sidebar');
            });
        });
        
        canvas.addEventListener('dragover', (e) => {
            e.preventDefault();
            canvas.style.borderColor = '#667eea';
        });
        
        canvas.addEventListener('dragleave', () => {
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
        });
    }
    
    // ============ EDGE MANAGEMENT ============
    createEdge(sourceNodeId, targetNodeId) {
        console.log('Creating edge from', sourceNodeId, 'to', targetNodeId);
        const edgeId = `edge-${this.state.edgeCounter++}`;
        const edge = {
            id: edgeId,
            source: sourceNodeId,
            target: targetNodeId,
            sourcePort: 'output',
            targetPort: 'input'
        };

        this.state.workflowEdges.push(edge);
        this.drawEdge(edge);
        this.updateEdgeCountDisplay();
        this.log(`Created connection: ${sourceNodeId} ? ${targetNodeId}`);
        
        // Record operation
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
        const sourceNode = this.state.workflowNodes.find(n => n.id === edge.source);
        const targetNode = this.state.workflowNodes.find(n => n.id === edge.target);

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
        this.state.workflowEdges.forEach(edge => {
            if (edge.element && edge.path) {
                const sourceNode = this.state.workflowNodes.find(n => n.id === edge.source);
                const targetNode = this.state.workflowNodes.find(n => n.id === edge.target);
                
                if (!sourceNode || !targetNode) {
                    console.warn('Edge references missing node:', edge.source, 'or', edge.target);
                    return;
                }
                
                const sourceElement = document.getElementById(sourceNode.elementId);
                const targetElement = document.getElementById(targetNode.elementId);
                
                if (!sourceElement || !targetElement) {
                    console.warn('Node element not found:', sourceNode.elementId, 'or', targetNode.elementId);
                    return;
                }
                
                const canvasRect = document.getElementById('canvas').getBoundingClientRect();
                
                // Calculate source port position
                const sourceRect = sourceElement.getBoundingClientRect();
                const sourceX = sourceRect.left - canvasRect.left + sourceRect.width;
                const sourceY = sourceRect.top - canvasRect.top + sourceRect.height / 2;
                
                // Calculate target port position
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
            this.state.selectedEdge = edgeId;
            document.getElementById('delete-edge-btn').style.display = 'inline-flex';
            this.log(`Selected edge: ${edgeId}`);
        }
    }
    
    deleteSelectedEdge() {
        if (!this.state.selectedEdge) return;

        const edgeIndex = this.state.workflowEdges.findIndex(edge => edge.id === this.state.selectedEdge);
        if (edgeIndex !== -1) {
            const edge = this.state.workflowEdges[edgeIndex];
            
            // Record operation
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

            this.state.workflowEdges.splice(edgeIndex, 1);

            this.log(`Deleted edge: ${this.state.selectedEdge}`);
            this.updateEdgeCountDisplay();

            document.getElementById('delete-edge-btn').style.display = 'none';
            this.state.selectedEdge = null;
        }
    }
    
    deleteSelectedNode() {
        if (!this.state.selectedNode) return;

        const nodeIndex = this.state.workflowNodes.findIndex(
            n => n.elementId === this.state.selectedNode
        );

        if (nodeIndex === -1) return;

        const node = this.state.workflowNodes[nodeIndex];

        // Record operation
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

        const edgesToDelete = this.state.workflowEdges.filter(edge =>
            edge.source === node.id || edge.target === node.id
        );

        edgesToDelete.forEach(edge => {
            // Record edge deletions
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

        this.state.workflowEdges = this.state.workflowEdges.filter(edge =>
            edge.source !== node.id && edge.target !== node.id
        );

        this.state.workflowNodes.splice(nodeIndex, 1);

        this.updateNodeCountDisplay();
        this.updateEdgeCountDisplay();

        if (this.state.workflowNodes.length === 0) {
            document.getElementById('canvas-empty-state').style.display = 'flex';
        }

        this.log(`Deleted node: ${node.id}, removed ${edgesToDelete.length} edges`);

        document.getElementById('delete-node-btn').style.display = 'none';
        this.state.selectedNode = null;
    }
    
    // ============ UI UPDATES ============
    updateNodeCountDisplay() {
        const count = this.state.workflowNodes.length;
        const display = document.getElementById('node-count-display');
        if (display) {
            display.textContent = `${count} node${count !== 1 ? 's' : ''}`;
        }
    }
    
    updateEdgeCountDisplay() {
        const count = this.state.workflowEdges.length;
        const display = document.getElementById('edge-count-display');
        if (display) {
            display.textContent = `${count} connection${count !== 1 ? 's' : ''}`;
        }
    }
    
    updateUndoRedoButtons() {
        const undoBtn = document.getElementById('undo-btn');
        const redoBtn = document.getElementById('redo-btn');
        
        if (undoBtn && redoBtn && this.state.operationHistory) {
            undoBtn.disabled = this.state.operationHistory.undoStack.length === 0;
            redoBtn.disabled = this.state.operationHistory.redoStack.length === 0;
            
            undoBtn.title = `Undo (${this.state.operationHistory.undoStack.length} available)`;
            redoBtn.title = `Redo (${this.state.operationHistory.redoStack.length} available)`;
        }
    }
    
    updateStatus(status) {
        const statusDiv = document.getElementById('status');
        if (statusDiv) {
            statusDiv.textContent = status;
            statusDiv.className = 'status status-' + status.toLowerCase();
        }
    }
    
    // ============ EVENT LISTENERS ============
     // frontend/static/js/app.js ?? setupEventListeners ??
setupEventListeners() {
    // New node button
    const newNodeBtn = document.getElementById('new-node-btn');
    if (newNodeBtn) {
        newNodeBtn.addEventListener('click', () => this.createNewNode());
    }
    
    // Delete buttons
    const deleteEdgeBtn = document.getElementById('delete-edge-btn');
    if (deleteEdgeBtn) {
        deleteEdgeBtn.addEventListener('click', () => this.deleteSelectedEdge());
    }
    
    const deleteNodeBtn = document.getElementById('delete-node-btn');
    if (deleteNodeBtn) {
        deleteNodeBtn.addEventListener('click', () => this.deleteSelectedNode());
    }
    
    // Connection mode buttons
    const connectModeBtn = document.getElementById('connect-mode-btn');
    if (connectModeBtn) {
        connectModeBtn.addEventListener('click', () => {
            this.state.isConnectingMode = true;
            document.getElementById('mode-indicator').textContent = 'Connecting';
            document.getElementById('mode-indicator').classList.add('mode-connecting');
            this.log('Connection mode active. Click output port, then input port to connect nodes.');
        });
    }
    
    const cancelConnectBtn = document.getElementById('cancel-connect-btn');
    if (cancelConnectBtn) {
        cancelConnectBtn.addEventListener('click', () => {
            this.state.isConnectingMode = false;
            this.state.connectingFromNode = null;
            this.state.connectingFromPort = null;
            
            document.querySelectorAll('.port').forEach(port => {
                if (port.classList.contains('input')) {
                    port.style.backgroundColor = '#10B981';
                } else if (port.classList.contains('output')) {
                    port.style.backgroundColor = '#3B82F6';
                }
            });
            
            document.getElementById('mode-indicator').textContent = 'Normal';
            document.getElementById('mode-indicator').classList.remove('mode-connecting');
            this.log('Connection mode cancelled.');
        });
    }
    
    // Workflow actions
    const saveWorkflowBtn = document.getElementById('save-workflow-btn');
    if (saveWorkflowBtn) {
        saveWorkflowBtn.addEventListener('click', () => this.saveWorkflow());
    }
    
    const runWorkflowBtn = document.getElementById('run-workflow-btn');
    if (runWorkflowBtn) {
        runWorkflowBtn.addEventListener('click', () => this.runWorkflow());
    }
    
    const initialDataBtn = document.getElementById('initial-data-btn');
    if (initialDataBtn) {
        initialDataBtn.addEventListener('click', () => this.showInitialDataModal());
    }
    
    // New/Load workflow
    const newWorkflowBtn = document.getElementById('new-workflow-btn');
    if (newWorkflowBtn) {
        newWorkflowBtn.addEventListener('click', () => this.newWorkflow());
    }
    
    const loadWorkflowBtn = document.getElementById('load-workflow-btn');
    if (loadWorkflowBtn) {
        loadWorkflowBtn.addEventListener('click', () => this.loadWorkflow());
    }
    
    // Initial data modal listeners
    const saveInitialDataBtn = document.getElementById('save-initial-data-btn');
    if (saveInitialDataBtn) {
        saveInitialDataBtn.addEventListener('click', () => this.saveInitialData());
    }
    
    const closeInitialDataBtn = document.getElementById('close-initial-data-btn');
    if (closeInitialDataBtn) {
        closeInitialDataBtn.addEventListener('click', () => this.closeModal());
    }
    
    const cancelInitialDataBtn = document.getElementById('cancel-initial-data-btn');
    if (cancelInitialDataBtn) {
        cancelInitialDataBtn.addEventListener('click', () => this.closeModal());
    }
    
    // Canvas click to deselect
    const canvas = document.getElementById('canvas');
    if (canvas) {
        canvas.addEventListener('click', (e) => {
            if (e.target === canvas || e.target.id === 'edges-container' || e.target.tagName === 'svg') {
                document.querySelectorAll('.edge').forEach(edge => edge.classList.remove('selected'));
                document.getElementById('delete-edge-btn').style.display = 'none';
                this.state.selectedEdge = null;
                
                document.querySelectorAll('.canvas-node').forEach(node => {
                    const nodeId = node.dataset.nodeId;
                    const nodeObj = this.state.workflowNodes.find(n => n.elementId === node.id);
                    if (nodeObj) {
                        node.style.borderColor = nodeObj.color || this.getNodeColor(nodeId);
                    } else {
                        node.style.borderColor = this.getNodeColor(nodeId);
                    }
                    node.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                });
                document.getElementById('delete-node-btn').style.display = 'none';
                this.state.selectedNode = null;
            }
        });
    }
    
    // Initial data modal backdrop
    const initialDataModal = document.getElementById('initial-data-modal');
    if (initialDataModal) {
        initialDataModal.addEventListener('click', (e) => {
            if (e.target === initialDataModal) {
                this.closeModal();
            }
        });
    }
    
    // Code modal backdrop
    const codeModal = document.getElementById('code-modal');
    if (codeModal) {
        codeModal.addEventListener('click', (e) => {
            if (e.target === codeModal) {
                this.closeModal();
            }
        });
    }
    
    // Results modal backdrop
    const resultsModal = document.getElementById('results-modal');
    if (resultsModal) {
        resultsModal.addEventListener('click', (e) => {
            if (e.target === resultsModal) {
                document.getElementById('results-modal').classList.remove('active');
            }
        });
    }
    
    // Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (this.state.isConnectingMode) {
                this.state.isConnectingMode = false;
                this.state.connectingFromNode = null;
                this.state.connectingFromPort = null;
                document.getElementById('mode-indicator').textContent = 'Normal';
                document.getElementById('mode-indicator').classList.remove('mode-connecting');
            } else {
                this.closeModal();
            }
        }
    });
}
    
    // ============ WORKFLOW OPERATIONS ============
    saveWorkflow() {
        if (this.state.workflowNodes.length === 0) {
            alert('No workflow to save');
            return;
        }

        const workflowData = {
            nodes: this.state.workflowNodes,
            edges: this.state.workflowEdges,
            initialState: this.state.initialState,
            timestamp: new Date().toISOString()
        };

        this.log('Workflow saved locally');
        console.log('Workflow data:', workflowData);
        
        // Save to localStorage
        localStorage.setItem('rosie_workflow', JSON.stringify(workflowData));
    }
    
    async runWorkflow() {
        if (this.state.workflowNodes.length === 0) {
            alert('No workflow to run');
            return;
        }

        if (this.state.workflowEdges.length === 0) {
            if (!confirm('No connections between nodes. Run workflow anyway?')) return;
        }

        this.updateStatus('Running');
        this.log('Starting workflow execution...');

        try {
            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nodes: this.state.workflowNodes,
                    edges: this.state.workflowEdges,
                    initialState: this.state.initialState
                })
            });
            const data = await response.json();
            this.log(`Execution started with ID: ${data.execution_id}`);
        } catch (error) {
            console.error('Failed to run workflow:', error);
            this.updateStatus('Error');
            this.log('Error starting workflow: ' + error.message);
        }
    }
    
    newWorkflow() {
        if (confirm('Create new workflow? Current work will be lost.')) {
            // Clear canvas
            document.querySelectorAll('.canvas-node').forEach(node => node.remove());
            document.querySelectorAll('#edges-container g').forEach(edge => edge.remove());
            
            // Reset state
            this.state.workflowNodes = [];
            this.state.workflowEdges = [];
            this.state.selectedNode = null;
            this.state.selectedEdge = null;
            
            // Update UI
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
            
            // Clear current workflow
            this.newWorkflow();
            
            // Load nodes
            workflowData.nodes.forEach(nodeData => {
                this.addNodeToCanvas(nodeData.id, nodeData.type, 
                    nodeData.x + 60, nodeData.y + 30);
            });
            
            // Load edges
            workflowData.edges.forEach(edge => {
                this.createEdge(edge.source, edge.target);
            });
            
            // Load initial state
            if (workflowData.initialState) {
                this.state.initialState = workflowData.initialState;
            }
            
            document.getElementById('workflow-title').textContent = 
                `Loaded Workflow (${new Date(workflowData.timestamp).toLocaleString()})`;
            
            this.log(`Workflow loaded: ${workflowData.nodes.length} nodes, ${workflowData.edges.length} edges`);
        } catch (error) {
            console.error('Failed to load workflow:', error);
            alert('Error loading workflow');
        }
    }
    
    // ============ MODAL FUNCTIONS ============
    showInitialDataModal() {
        document.getElementById('initial-data-modal').classList.add('active');
        document.getElementById('initial-data-editor').value = 
            JSON.stringify(this.state.initialState, null, 2);
    }

    saveInitialData() {
        try {
            const dataText = document.getElementById('initial-data-editor').value;
            this.state.initialState = JSON.parse(dataText);
            this.closeModal();
            this.log('Initial state data saved');
        } catch (error) {
            alert('Invalid JSON format. Please check your data.');
        }
    }

    closeModal() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('active');
        });
    }
    
    // ============ LOGGING ============
    log(message) {
        const logPanel = document.getElementById('log-panel');
        const entry = document.createElement('div');
        const time = new Date().toLocaleTimeString();
        entry.textContent = `[${time}] ${message}`;
        logPanel.appendChild(entry);
        logPanel.scrollTop = logPanel.scrollHeight;
    }
    
    // ============ GETTERS ============
    getState() {
        return this.state;
    }
    
    getCodeTemplates() {
        return codeTemplates;
    }
}