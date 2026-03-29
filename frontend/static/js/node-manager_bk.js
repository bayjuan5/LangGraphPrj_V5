// frontend/static/js/node-manager.js
/**
 * Node Manager Module
 * Handles node creation, editing, and management
 */

export default class NodeManager {
    constructor(app) {
        this.app = app;
        console.log('NodeManager initialized');
    }
    
    // Methods from views.js that handle node operations
    editNodeCode(nodeId) {
        // This will be handled by CodeEditor module
        console.log(`Opening editor for node: ${nodeId}`);
        
        // Get node data
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
    Modify this function to implement your logic.
    """
    # Your logic here
    return state`;
            
            document.getElementById('node-display-name').value = displayName;
            document.getElementById('node-type-select').value = nodeId;
            document.getElementById('node-icon-select').value = nodeId === 'start' ? 'play' : nodeId === 'end' ? 'stop' : 'plus';
            document.getElementById('node-color-select').value = nodeId === 'start' ? '#10B981' : nodeId === 'end' ? '#EF4444' : '#F59E0B';
            document.getElementById('node-id-display').value = nodeId;
        }
        
        // Show modal
        document.getElementById('code-modal').classList.add('active');
        this.app.state.selectedNode = nodeId;
        this.switchTab('code');
        
        setTimeout(() => {
            document.getElementById('code-editor').focus();
            const textarea = document.getElementById('code-editor');
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        }, 100);
    }
    
    switchTab(tabName) {
        document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        document.querySelector(`.tab[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }
    
    applyNodeProperties() {
        const nodeName = document.getElementById('node-display-name').value;
        const nodeType = document.getElementById('node-type-select').value;
        const nodeIcon = document.getElementById('node-icon-select').value;
        const nodeColor = document.getElementById('node-color-select').value;
        
        if (!this.app.state.selectedNode) return;
        
        const customNodes = JSON.parse(localStorage.getItem('customNodes') || '[]');
        const nodeIndex = customNodes.findIndex(n => n.id === this.app.state.selectedNode);
        
        if (nodeIndex !== -1) {
            customNodes[nodeIndex].name = nodeName || `Node ${this.app.state.selectedNode.slice(-4)}`;
            customNodes[nodeIndex].type = nodeType;
            customNodes[nodeIndex].icon = nodeIcon;
            customNodes[nodeIndex].color = nodeColor;
            customNodes[nodeIndex].lastModified = new Date().toISOString();
            localStorage.setItem('customNodes', JSON.stringify(customNodes));
        } else if (this.app.state.selectedNode.startsWith('node_')) {
            customNodes.push({
                id: this.app.state.selectedNode,
                name: nodeName || `Node ${this.app.state.selectedNode.slice(-4)}`,
                type: nodeType,
                icon: nodeIcon,
                color: nodeColor,
                code: document.getElementById('code-editor').value || '',
                created: new Date().toISOString(),
                lastModified: new Date().toISOString()
            });
            localStorage.setItem('customNodes', JSON.stringify(customNodes));
        }
        
        const canvasNode = this.app.state.workflowNodes.find(n => n.id === this.app.state.selectedNode);
        if (canvasNode) {
            canvasNode.name = nodeName || `Node ${this.app.state.selectedNode.slice(-4)}`;
            canvasNode.type = nodeType;
            canvasNode.icon = nodeIcon;
            canvasNode.color = nodeColor;
            
            this.updateCanvasNodeDisplay(canvasNode);
        }
        
        this.app.loadNodes();
        this.app.log(`Updated properties for node: ${nodeName || this.app.state.selectedNode}`);
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
        
        const idElement = nodeElement.querySelector('div[style*="font-size: 9px"]');
        if (idElement) {
            idElement.textContent = `ID: ${canvasNode.id}`;
        }
        
        const typeElement = nodeElement.querySelector('div[style*="font-size: 8px"]');
        if (typeElement) {
            typeElement.textContent = canvasNode.type;
        }
        
        nodeElement.className = `canvas-node ${canvasNode.type}`;
    }
    
    loadTemplate() {
        const templateName = document.getElementById('template-selector').value;
        if (templateName && this.app.getCodeTemplates()[templateName]) {
            document.getElementById('template-preview').textContent = this.app.getCodeTemplates()[templateName];
        }
    }
    
    applyParams() {
        const inputKey = document.getElementById('input-key').value;
        const outputKey = document.getElementById('output-key').value;
        const timeout = document.getElementById('timeout').value;

        if (inputKey || outputKey) {
            let code = document.getElementById('code-editor').value;
            if (!code.includes('def process')) {
                code = `def process(state, params=None):\n    # Node: ${this.app.state.selectedNode}\n    # Input key: ${inputKey}\n    # Output key: ${outputKey}\n    # Timeout: ${timeout}s\n    \n    # Your logic here\n    return state`;
            }
            document.getElementById('code-editor').value = code;
            this.app.log(`Applied parameters to ${this.app.state.selectedNode}`);
        }
    }
}