// frontend/static/js/undo-redo-manager.js
/**
 * Undo/Redo Manager Module
 * Handles undo/redo functionality
 */

export default class UndoRedoManager {
    constructor(app) {
        this.app = app;
        console.log('UndoRedoManager initialized');
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        const undoBtn = document.getElementById('undo-btn');
        if (undoBtn) {
            undoBtn.addEventListener('click', () => this.undoAction());
        }
        
        const redoBtn = document.getElementById('redo-btn');
        if (redoBtn) {
            redoBtn.addEventListener('click', () => this.redoAction());
        }
    }
    
    recordOperation(operation) {
        console.log('Recording operation:', operation.type);
        this.app.state.operationHistory.undoStack.push(operation);
        this.app.state.operationHistory.redoStack = [];
        
        if (this.app.state.operationHistory.undoStack.length > this.app.state.operationHistory.MAX_STEPS) {
            this.app.state.operationHistory.undoStack.shift();
        }
        
        this.app.updateUndoRedoButtons();
    }
    
    undoAction() {
        if (this.app.state.operationHistory.undoStack.length === 0) return;
        
        const lastOperation = this.app.state.operationHistory.undoStack.pop();
        console.log('Undoing operation:', lastOperation.type);
        
        switch(lastOperation.type) {
            case 'add_node':
                this.undoAddNode(lastOperation.data);
                break;
            case 'delete_node':
                this.redoDeleteNode(lastOperation.data);
                break;
            case 'add_edge':
                this.undoAddEdge(lastOperation.data);
                break;
            case 'delete_edge':
                this.redoDeleteEdge(lastOperation.data);
                break;
            case 'move_node':
                this.undoMoveNode(lastOperation.data);
                break;
            default:
                console.log('Unknown operation type:', lastOperation.type);
        }
        
        this.app.state.operationHistory.redoStack.push(lastOperation);
        this.app.updateUndoRedoButtons();
        this.app.log(`Undo: ${lastOperation.type} operation`);
    }
    
    redoAction() {
        if (this.app.state.operationHistory.redoStack.length === 0) return;
        
        const nextOperation = this.app.state.operationHistory.redoStack.pop();
        console.log('Redoing operation:', nextOperation.type);
        
        switch(nextOperation.type) {
            case 'add_node':
                this.redoAddNode(nextOperation.data);
                break;
            case 'delete_node':
                this.undoDeleteNode(nextOperation.data);
                break;
            case 'add_edge':
                this.redoAddEdge(nextOperation.data);
                break;
            case 'delete_edge':
                this.undoDeleteEdge(nextOperation.data);
                break;
            case 'move_node':
                this.redoMoveNode(nextOperation.data);
                break;
            default:
                console.log('Unknown operation type:', nextOperation.type);
        }
        
        this.app.state.operationHistory.undoStack.push(nextOperation);
        this.app.updateUndoRedoButtons();
        this.app.log(`Redo: ${nextOperation.type} operation`);
    }
    
    undoAddNode(nodeData) {
        const nodeElement = document.getElementById(nodeData.elementId);
        if (nodeElement && nodeElement.parentNode) {
            nodeElement.parentNode.removeChild(nodeElement);
        }
        
        const nodeIndex = this.app.state.workflowNodes.findIndex(n => n.id === nodeData.id);
        if (nodeIndex !== -1) {
            this.app.state.workflowNodes.splice(nodeIndex, 1);
        }
        
        this.app.updateNodeCountDisplay();
        
        if (this.app.state.workflowNodes.length === 0) {
            document.getElementById('canvas-empty-state').style.display = 'flex';
        }
    }
    
    redoAddNode(nodeData) {
        const canvas = document.getElementById('canvas');
        const nodeElement = document.createElement('div');
        nodeElement.className = `canvas-node ${nodeData.type}`;
        nodeElement.id = nodeData.elementId;
        nodeElement.dataset.nodeId = nodeData.id;
        nodeElement.style.left = nodeData.x + 'px';
        nodeElement.style.top = nodeData.y + 'px';
        
        const title = nodeData.name || nodeData.id;
        const icon = nodeData.icon || 'cog';
        const color = nodeData.color || '#667eea';
        
        let inputPort = '', outputPort = '';
        if (nodeData.type === 'start') {
            outputPort = '<div class="port output" data-port-type="output"><div class="port-tooltip">Output</div></div>';
            inputPort = '<div class="port" style="visibility: hidden;"></div>';
        } else if (nodeData.type === 'end') {
            inputPort = '<div class="port input" data-port-type="input"><div class="port-tooltip">Input</div></div>';
            outputPort = '<div class="port" style="visibility: hidden;"></div>';
        } else {
            inputPort = '<div class="port input" data-port-type="input"><div class="port-tooltip">Input</div></div>';
            outputPort = '<div class="port output" data-port-type="output"><div class="port-tooltip">Output</div></div>';
        }

        nodeElement.innerHTML = `
            <div style="position: relative; height: 100%;">
                <div><i class="fas fa-${icon}" style="color: ${color}; font-size: 24px;"></i></div>
                <div style="margin-top: 8px; font-size: 12px; font-weight: 600; color: #333;">${title}</div>
                <div style="font-size: 9px; color: #999; margin-top: 2px; opacity: 0.7;">ID: ${nodeData.id}</div>
                <div class="node-ports">
                    ${inputPort}
                    <div style="font-size: 8px; color: #999; margin-top: 3px;">${nodeData.type}</div>
                    ${outputPort}
                </div>
            </div>
        `;
        
        nodeElement.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            if (this.app.modules.codeEditor) {
                this.app.modules.codeEditor.openEditor(nodeData.id);
            }
        });

        nodeElement.addEventListener('click', (e) => {
            e.stopPropagation();
            this.app.selectNode(nodeElement);
        });

        nodeElement.draggable = true;
        this.app.makeDraggable(nodeElement, nodeData.id);
        
        canvas.appendChild(nodeElement);
        document.getElementById('canvas-empty-state').style.display = 'none';
        
        this.app.state.workflowNodes.push(nodeData);
        this.app.updateNodeCountDisplay();
    }
    
    undoAddEdge(edgeData) {
        const edgeElement = document.getElementById(edgeData.id);
        if (edgeElement && edgeElement.parentNode) {
            edgeElement.parentNode.removeChild(edgeElement);
        }
        
        const edgeIndex = this.app.state.workflowEdges.findIndex(e => e.id === edgeData.id);
        if (edgeIndex !== -1) {
            this.app.state.workflowEdges.splice(edgeIndex, 1);
        }
        
        this.app.updateEdgeCountDisplay();
    }
    
    redoAddEdge(edgeData) {
        this.app.state.workflowEdges.push(edgeData);
        this.app.drawEdge(edgeData);
        this.app.updateEdgeCountDisplay();
    }
    
    undoMoveNode(moveData) {
        const nodeElement = document.getElementById(moveData.elementId);
        if (nodeElement) {
            nodeElement.style.left = moveData.oldX + 'px';
            nodeElement.style.top = moveData.oldY + 'px';
        }
        
        const node = this.app.state.workflowNodes.find(n => n.elementId === moveData.elementId);
        if (node) {
            node.x = moveData.oldX;
            node.y = moveData.oldY;
        }
        
        this.app.updateAllEdges();
    }
    
    redoMoveNode(moveData) {
        const nodeElement = document.getElementById(moveData.elementId);
        if (nodeElement) {
            nodeElement.style.left = moveData.newX + 'px';
            nodeElement.style.top = moveData.newY + 'px';
        }
        
        const node = this.app.state.workflowNodes.find(n => n.elementId === moveData.elementId);
        if (node) {
            node.x = moveData.newX;
            node.y = moveData.newY;
            if (moveData.name) node.name = moveData.name;
            if (moveData.icon) node.icon = moveData.icon;
            if (moveData.color) node.color = moveData.color;
            if (moveData.type) node.type = moveData.type;
            
            if (this.app.modules.nodeManager) {
                this.app.modules.nodeManager.updateCanvasNodeDisplay(node);
            }
        }
        
        this.app.updateAllEdges();
    }
}