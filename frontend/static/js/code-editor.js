// frontend/static/js/code-editor.js
/**
 * Code Editor Module
 * Handles code editing, templates, and saving
 */

export default class CodeEditor {
    constructor(app) {
        this.app = app;
        console.log('CodeEditor initialized');
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Template selector
        const templateSelector = document.getElementById('template-selector');
        if (templateSelector) {
            templateSelector.addEventListener('change', () => this.loadTemplate());
        }
        
        // Apply parameters button
        const applyParamsBtn = document.getElementById('apply-params-btn');
        if (applyParamsBtn) {
            applyParamsBtn.addEventListener('click', () => {
                if (this.app.modules.nodeManager) {
                    this.app.modules.nodeManager.applyParams();
                }
            });
        }
        
        // Apply properties button
        const applyPropertiesBtn = document.getElementById('apply-properties-btn');
        if (applyPropertiesBtn) {
            applyPropertiesBtn.addEventListener('click', () => {
                if (this.app.modules.nodeManager) {
                    this.app.modules.nodeManager.applyNodeProperties();
                }
            });
        }
        
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.getAttribute('data-tab');
                if (this.app.modules.nodeManager) {
                    this.app.modules.nodeManager.switchTab(tabName);
                }
            });
        });
        
        // Save code button
        const saveCodeBtn = document.getElementById('save-code-btn');
        if (saveCodeBtn) {
            saveCodeBtn.addEventListener('click', () => this.saveNodeCode());
        }
        
        // Cancel buttons
        const cancelModalBtn = document.getElementById('cancel-modal-btn');
        if (cancelModalBtn) {
            cancelModalBtn.addEventListener('click', () => this.app.closeModal());
        }
        
        const closeModalBtn = document.getElementById('close-modal-btn');
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => this.app.closeModal());
        }
        
        // Modal backdrop click
        const codeModal = document.getElementById('code-modal');
        if (codeModal) {
            codeModal.addEventListener('click', (e) => {
                if (e.target === codeModal) {
                    this.app.closeModal();
                }
            });
        }
    }
    
    openEditor(nodeId) {
        if (this.app.modules.nodeManager) {
            this.app.modules.nodeManager.editNodeCode(nodeId);
        }
    }
    
    loadTemplate() {
        if (this.app.modules.nodeManager) {
            this.app.modules.nodeManager.loadTemplate();
        }
    }
    
    async saveNodeCode() {
        if (!this.app.state.selectedNode) return;
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

        try {
            const customNodes = JSON.parse(localStorage.getItem('customNodes') || '[]');
            const nodeIndex = customNodes.findIndex(n => n.id === this.app.state.selectedNode);
            
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
            } else if (this.app.state.selectedNode.startsWith('node_')) {
                customNodes.push({
                    id: this.app.state.selectedNode,
                    name: nodeName || `Node ${this.app.state.selectedNode.slice(-4)}`,
                    type: nodeType || 'custom',
                    icon: nodeIcon || 'plus',
                    color: nodeColor || '#F59E0B',
                    code: code,
                    created: new Date().toISOString(),
                    lastModified: new Date().toISOString()
                });
                localStorage.setItem('customNodes', JSON.stringify(customNodes));
            }
            
            const canvasNode = this.app.state.workflowNodes.find(n => n.id === this.app.state.selectedNode);
            if (canvasNode) {
                canvasNode.name = nodeName || `Node ${this.app.state.selectedNode.slice(-4)}`;
                canvasNode.type = nodeType || 'custom';
                canvasNode.icon = nodeIcon || 'plus';
                canvasNode.color = nodeColor || '#F59E0B';
                
                if (this.app.modules.nodeManager) {
                    this.app.modules.nodeManager.updateCanvasNodeDisplay(canvasNode);
                }
            }
            
            this.app.closeModal();
            this.app.log(`Code saved for ${nodeName || this.app.state.selectedNode}`);
            this.app.loadNodes();
        } catch (error) {
            console.error('Failed to save code:', error);
            this.app.log('Error saving node code: ' + error.message);
        }
    }
}