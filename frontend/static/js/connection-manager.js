// frontend/static/js/connection-manager.js
/**
 * Connection Manager Module
 * Handles node connections and edge management
 */

export default class ConnectionManager {
    constructor(app) {
        this.app = app;
        console.log('ConnectionManager initialized');
    }
    
    handlePortClick(nodeId, portType, portElement) {
        if (!this.app.state.isConnectingMode) {
            this.app.log(`Click the "Connect Nodes" button first to create connections`);
            return;
        }

        if (!this.app.state.connectingFromNode) {
            this.app.state.connectingFromNode = nodeId;
            this.app.state.connectingFromPort = portType;
            portElement.style.backgroundColor = '#F59E0B';
            this.app.log(`Starting connection from ${nodeId} (${portType}) - Now click target port`);
        } else {
            if (this.app.state.connectingFromNode === nodeId) {
                this.app.log(`Cannot connect a node to itself`);
                this.resetConnectingMode();
                return;
            }

            if (this.app.state.connectingFromPort === portType) {
                this.app.log(`Cannot connect ${this.app.state.connectingFromPort} to ${portType} - need input/output pair`);
                this.resetConnectingMode();
                return;
            }

            let sourceNode, targetNode;
            if (this.app.state.connectingFromPort === 'output' && portType === 'input') {
                sourceNode = this.app.state.connectingFromNode;
                targetNode = nodeId;
            } else if (this.app.state.connectingFromPort === 'input' && portType === 'output') {
                sourceNode = nodeId;
                targetNode = this.app.state.connectingFromNode;
            } else {
                this.app.log(`Invalid connection: ${this.app.state.connectingFromPort} to ${portType}`);
                this.resetConnectingMode();
                return;
            }

            const existingEdge = this.app.state.workflowEdges.find(edge => 
                edge.source === sourceNode && edge.target === targetNode
            );

            if (existingEdge) {
                this.app.log(`Connection already exists between ${sourceNode} and ${targetNode}`);
                this.resetConnectingMode();
                return;
            }

            this.app.createEdge(sourceNode, targetNode);
            this.resetConnectingMode();
        }
    }
    
    resetConnectingMode() {
        this.app.state.isConnectingMode = false;
        this.app.state.connectingFromNode = null;
        this.app.state.connectingFromPort = null;

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