# app.py - Fixed Version with timezone and print output fixes
"""
LangGraph Studio - Fixed Version
Version: 1.2.0
"""

import os
import sys
import json
import time
import uuid
import logging
from datetime import datetime, timezone, UTC
from typing import Dict, Any, Tuple
from io import StringIO, BytesIO
import traceback

# Third-party imports
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from dotenv import load_dotenv

# ── TCGA-PAAD default SVS path ────────────────────────────────────────────────
load_dotenv()
_HERE = Path(__file__).parent

_SVS_FILENAME = (
    "TCGA-HZ-7926-01Z-00-DX1."
    "b3bf02d3-bad0-4451-9c39-b0593f19154c.svs"
)
# Priority: SVS_PATH env var → TCGA_test/ subfolder next to app.py
TCGA_SVS_PATH = os.environ.get(
    "SVS_PATH",
    str(_HERE / "TCGA_test" / _SVS_FILENAME),
)
OUTPUTS_DIR = _HERE / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)


def _load_node_code(filename: str) -> str:
    """Read a node Python file and return its source as a string."""
    p = _HERE / "nodes" / filename
    return p.read_text(encoding="utf-8") if p.exists() else ""

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__,
            template_folder='frontend/templates',
            static_folder='frontend/static')

# Configuration
app.config['SECRET_KEY'] = 'dev-secret-key-for-testing'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # In-memory database for testing
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
CORS(app)
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# ==================== DATABASE MODELS ====================

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Workflow(db.Model):
    __tablename__ = 'workflows'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Store as JSON text
    nodes = db.Column(db.Text, default='[]')
    edges = db.Column(db.Text, default='[]')

    # Fixed: Store user ID as string, not relationship
    user_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4()))
    is_public = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        try:
            nodes_data = json.loads(self.nodes) if self.nodes else []
        except:
            nodes_data = []

        try:
            edges_data = json.loads(self.edges) if self.edges else []
        except:
            edges_data = []

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'nodes': nodes_data,
            'edges': edges_data,
            'user_id': self.user_id,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def set_nodes(self, nodes):
        self.nodes = json.dumps(nodes)

    def set_edges(self, edges):
        self.edges = json.dumps(edges)


# In-memory cache for execution results (keyed by execution_id)
execution_results_cache: Dict[str, Any] = {}

# Track running executions so frontend can heartbeat
running_executions: Dict[str, Any] = {}  # execution_id → {'status', 'current_node', 'started_at'}



def safe_getvalue(obj):
    """
    Safely get value from object, handling both StringIO/BytesIO and regular objects
    """
    if hasattr(obj, 'getvalue'):
        # It's StringIO/BytesIO
        return obj.getvalue()
    elif hasattr(obj, 'read'):
        # It's a file-like object (TextIOWrapper, etc.)
        try:
            # Try to read and get position
            current_pos = obj.tell()
            obj.seek(0)
            content = obj.read()
            obj.seek(current_pos)  # Restore position
            return content
        except:
            # If we can't read, return string representation
            return str(obj)
    else:
        # Regular object
        return str(obj)


def execute_node_code(node_code: str, state: Dict, params: Any = None) -> Tuple[bool, Dict, str, str]:
    """
    Safely execute node Python code
    Returns: (success, modified_state, output, error)
    """
    # Create a clean execution environment
    exec_globals = {
        'state': state.copy() if state else {},
        'params': params,
        '__builtins__': __builtins__
    }

    # Create StringIO to capture ALL output (including prints from code execution)
    output_buffer = StringIO()

    try:
        # Save original stdout and redirect to buffer
        old_stdout = sys.stdout
        sys.stdout = output_buffer

        # Execute the node code - this will capture any print statements in the code itself
        exec(node_code, exec_globals)

        # Get the output from buffer (captures prints from code execution)
        output = safe_getvalue(output_buffer)

        # Check if process function exists and is callable
        if 'process' in exec_globals and callable(exec_globals['process']):
            # Create fresh buffer for process function
            process_buffer = StringIO()
            sys.stdout = process_buffer

            # Execute the process function
            # result_state = exec_globals['process'](state, params)
            result_state = exec_globals['process'](exec_globals['state'], params)
            if result_state is None:
                result_state = exec_globals['state']
            # Get process output
            process_output = safe_getvalue(process_buffer)

            # Combine outputs from both code execution and process function
            full_output = output + process_output

            # Restore stdout
            sys.stdout = old_stdout

            return (True, result_state, full_output, None)
        else:
            # No process function found, restore stdout
            sys.stdout = old_stdout
            return (False, state, output, "No 'process' function defined in node code")

    except Exception as e:
        # Get output before error
        output = safe_getvalue(output_buffer)
        # Restore stdout
        sys.stdout = old_stdout if 'old_stdout' in locals() else sys.__stdout__
        error_trace = traceback.format_exc()
        return (False, state, output, error_trace)


def fix_file_like_objects(state: Dict) -> Dict:
    """
    Convert file-like objects in state to strings to avoid getvalue() errors
    """
    fixed_state = {}
    for key, value in state.items():
        if hasattr(value, 'read'):
            # It's a file-like object
            try:
                # Try to read it
                if hasattr(value, 'seek'):
                    current_pos = value.tell()
                    value.seek(0)

                content = value.read()

                if hasattr(value, 'seek'):
                    value.seek(current_pos)

                # Handle bytes
                if isinstance(content, bytes):
                    try:
                        content = content.decode('utf-8')
                    except:
                        content = str(content)

                fixed_state[key] = content
            except Exception as e:
                fixed_state[key] = f"<Error reading {type(value).__name__}: {str(e)}>"
        else:
            fixed_state[key] = value

    return fixed_state


def compute_state_diff(before: Dict, after: Dict) -> Dict:
    """
    Compare state before and after node execution.
    Returns dict with added/changed/removed keys and a preview of values.
    """
    def preview(v, max_len=200):
        """Short human-readable preview of any value."""
        import numpy as np
        try:
            if hasattr(v, 'shape'):   # numpy / tensor
                return f"<array shape={v.shape} dtype={getattr(v,'dtype','?')}>"
            if isinstance(v, (list, tuple)):
                inner = str(v[:3])[:-1] + (', ...]' if len(v) > 3 else str(v)[len(str(v[:3]))-1:])
                return f"{type(v).__name__}[{len(v)}] {inner}"
            if isinstance(v, dict):
                keys = list(v.keys())[:5]
                return f"dict({len(v)} keys: {keys})"
            s = str(v)
            return s if len(s) <= max_len else s[:max_len] + '...'
        except:
            return str(type(v))

    added   = {k: preview(after[k])  for k in after  if k not in before}
    removed = {k: preview(before[k]) for k in before if k not in after}
    changed = {k: {'before': preview(before[k]), 'after': preview(after[k])}
               for k in after if k in before and str(before[k]) != str(after[k])}
    unchanged_keys = [k for k in after if k in before and k not in changed]

    return {
        'added':          added,
        'changed':        changed,
        'removed':        removed,
        'unchanged_keys': unchanged_keys,
    }


def build_execution_order(nodes, edges, manual_start_id=None):
    """
    Builds the execution path starting from a specific node.
    It ignores disconnected nodes and stops at the 'end' node.
    """
    from collections import defaultdict, deque

    # 1. Build adjacency list (Graph)
    graph = defaultdict(list)
    for edge in edges:
        source = edge.get('source')
        target = edge.get('target')
        if source and target:
            graph[source].append(target)

    # 2. Determine the entry point
    start_id = manual_start_id
    if not start_id:
        start_node = next((n for n in nodes if n.get('id') == 'start'), None)
        if start_node:
            start_id = start_node.get('id')

    # If no start node found, fallback to first node in list
    if not start_id and nodes:
        start_id = nodes[0].get('id')

    if not start_id:
        return []

    # 3. Traverse path using BFS (Breadth-First Search)
    execution_order = []
    queue = deque([start_id])
    visited = {start_id}

    while queue:
        curr_id = queue.popleft()
        execution_order.append(curr_id)

        # Stop if we hit the explicit 'end' node
        if curr_id == 'end':
            break

        for neighbor in graph[curr_id]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return execution_order

# ==================== BASIC ROUTES ====================

@app.route('/')
def index():
    return render_template('perfect_fixed.html')


@app.route('/api/executions/<execution_id>', methods=['GET'])
def get_execution_result(execution_id):
    """Poll endpoint — frontend calls this if socket missed the execution_complete event."""
    result = execution_results_cache.get(execution_id)
    if not result:
        return jsonify({'status': 'pending'}), 202
    return jsonify(result), 200


@app.route('/api/executions/<execution_id>/heartbeat', methods=['GET'])
def execution_heartbeat(execution_id):
    """
    Lightweight heartbeat endpoint.
    Frontend polls this every 5s to confirm the backend is still alive.
    Returns status while running, completed/error when done.
    """
    if execution_id in running_executions:
        info = running_executions[execution_id]
        elapsed = time.time() - info.get('started_at', time.time())
        return jsonify({
            'status':       'running',
            'current_node': info.get('current_node', 'unknown'),
            'elapsed_s':    int(elapsed),
            'alive':        True,
        }), 200

    result = execution_results_cache.get(execution_id)
    if result:
        return jsonify({
            'status': result.get('status', 'completed'),
            'alive':  False,
        }), 200

    return jsonify({'status': 'not_found', 'alive': False}), 404


@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'LangGraph Studio',
        'version': '1.2.0',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.route('/api/nodes')
def get_nodes():
    return jsonify({
        "nodes": [
            {"id": "start", "name": "Start", "type": "start", "icon": "play", "color": "#10B981"},
            {"id": "end", "name": "End", "type": "end", "icon": "stop", "color": "#EF4444"},
            {"id": "llm", "name": "LLM", "type": "llm", "icon": "brain", "color": "#3B82F6"},
            {"id": "input", "name": "Input", "type": "input", "icon": "keyboard", "color": "#8B5CF6"},
            {"id": "output", "name": "Output", "type": "output", "icon": "terminal", "color": "#F59E0B"},
            {"id": "custom", "name": "Custom", "type": "custom", "icon": "cog", "color": "#6B7280"}
        ]
    })


# ==================== AUTH ROUTES ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or 'username' not in data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409

    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Simple session token
    token = str(uuid.uuid4())

    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'token': token
    })


# ==================== WORKFLOW ROUTES ====================

@app.route('/api/workflows', methods=['GET'])
def list_workflows():
    workflows = Workflow.query.filter_by(is_public=True).order_by(Workflow.updated_at.desc()).all()
    return jsonify({'workflows': [w.to_dict() for w in workflows]})


@app.route('/api/workflows', methods=['POST'])
def create_workflow():
    data = request.get_json()

    if not data or 'name' not in data:
        return jsonify({'error': 'Workflow name is required'}), 400

    # Create or get demo user
    demo_user = User.query.filter_by(username='demo').first()
    if not demo_user:
        demo_user = User(username='demo', email='demo@langgraph.studio')
        demo_user.set_password('demo123')
        db.session.add(demo_user)
        db.session.commit()
        logger.info(f"Created demo user with ID: {demo_user.id}")

    workflow = Workflow(
        name=data['name'],
        description=data.get('description', ''),
        user_id=demo_user.id,  # Use real user ID
        is_public=data.get('is_public', True)
    )

    # Set nodes and edges
    workflow.set_nodes(data.get('nodes', []))
    workflow.set_edges(data.get('edges', []))

    db.session.add(workflow)
    db.session.commit()

    socketio.emit('workflow_created', {
        'workflow_id': workflow.id,
        'name': workflow.name,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

    return jsonify({
        'message': 'Workflow created successfully',
        'workflow': workflow.to_dict()
    }), 201


@app.route('/api/workflows/<workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    workflow = Workflow.query.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404

    return jsonify(workflow.to_dict())


@app.route('/api/workflows/<workflow_id>', methods=['PUT'])
def update_workflow(workflow_id):
    workflow = Workflow.query.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404

    data = request.get_json()

    if 'name' in data:
        workflow.name = data['name']
    if 'description' in data:
        workflow.description = data.get('description', '')
    if 'nodes' in data:
        workflow.set_nodes(data['nodes'])
    if 'edges' in data:
        workflow.set_edges(data['edges'])
    if 'is_public' in data:
        workflow.is_public = data['is_public']

    workflow.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'message': 'Workflow updated successfully',
        'workflow': workflow.to_dict()
    })


@app.route('/api/workflows/<workflow_id>/execute', methods=['POST'])
def execute_workflow(workflow_id):
    workflow = Workflow.query.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404

    data = request.get_json()
    input_data = data.get('input', {})

    # Get initial state from input and fix file-like objects
    initial_state = fix_file_like_objects(input_data.get('initial_state', {}))

    # Use workflow nodes/edges if not provided in input
    try:
        nodes_data = input_data.get('nodes', json.loads(workflow.nodes) if workflow.nodes else [])
        edges_data = input_data.get('edges', json.loads(workflow.edges) if workflow.edges else [])
    except:
        nodes_data = input_data.get('nodes', [])
        edges_data = input_data.get('edges', [])

    execution_id = f"exec_{int(time.time())}"

    # Send start event
    socketio.emit('execution_started', {
        'execution_id': execution_id,
        'workflow_id': workflow_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'message': 'Workflow execution started'
    })

    # Execute in background thread
    def execute_nodes_background():
        # ── Register this execution as "running" ──────────────────────────
        running_executions[execution_id] = {
            'status':       'running',
            'current_node': 'initializing',
            'started_at':   time.time(),
            'workflow_id':  workflow_id,
        }

        def node_log(node_name, message, level='info'):
            """Emit a real-time log line for a specific node."""
            socketio.emit('node_log', {
                'execution_id': execution_id,
                'node':         node_name,
                'message':      message,
                'level':        level,   # 'info' | 'success' | 'warning' | 'error'
                'timestamp':    datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"[{node_name}] {message}")

        try:
            # Get nodes with their code
            node_codes = {}
            for node in nodes_data:
                node_id = node.get('id')
                node_code = node.get('code', '')
                node_codes[node_id] = {
                    'name': node.get('name', node_id),
                    'type': node.get('type', 'custom'),
                    'code': node_code
                }

            # Build execution order
            execution_order = build_execution_order(nodes_data, edges_data)

            if not execution_order:
                logger.warning("No execution order built, executing all nodes in order")
                execution_order = [node['id'] for node in nodes_data]

            current_state = initial_state.copy()
            execution_log = []

            logger.info(f"Executing {len(execution_order)} nodes in order: {execution_order}")

            # Execute each node
            for idx, node_id in enumerate(execution_order):
                node_info = node_codes.get(node_id, {})
                node_name = node_info.get('name', node_id)
                node_code = node_info.get('code', '')

                # Update heartbeat tracker
                running_executions[execution_id]['current_node'] = node_name

                logger.info(f"Executing node {idx + 1}/{len(execution_order)}: {node_name}")
                node_log(node_name, f'▶ Starting node ({idx+1}/{len(execution_order)})')

                # Progress update
                progress = int((idx + 1) / len(execution_order) * 100)
                socketio.emit('execution_progress', {
                    'execution_id': execution_id,
                    'progress': progress,
                    'message': f'Executing node: {node_name}',
                    'current_node': node_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

                log_entry = {
                    'node': node_name,
                    'node_id': node_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

                # Execute node code if it exists
                if node_code and node_code.strip():
                    logger.info(f"Running code for {node_name}")

                    # Snapshot state BEFORE execution for diff
                    safe_state = fix_file_like_objects(current_state)
                    state_before = safe_state.copy()

                    success, new_state, output, error = execute_node_code(
                        node_code,
                        safe_state,
                        params=None
                    )

                    if success:
                        current_state = new_state
                        diff = compute_state_diff(state_before, fix_file_like_objects(new_state))
                        log_entry['status']      = 'completed'
                        log_entry['output']      = output.strip()
                        log_entry['message']     = f'Successfully executed {node_name}'
                        log_entry['state_diff']  = diff
                        log_entry['input_keys']  = list(state_before.keys())
                        log_entry['output_keys'] = list(new_state.keys())

                        if output and output.strip():
                            logger.info(f"Node {node_name} output:\n{output}")
                            # Stream each output line as a node_log event
                            for line in output.strip().splitlines():
                                if line.strip():
                                    node_log(node_name, line, 'info')
                        else:
                            logger.info(f"Node {node_name} executed but produced no output")

                        node_log(node_name, f'✅ Completed', 'success')
                    else:
                        log_entry['status']  = 'error'
                        log_entry['error']   = error
                        log_entry['message'] = f'Error in {node_name}'
                        log_entry['state_diff'] = {}
                        logger.error(f"Node {node_name} error:\n{error}")
                        node_log(node_name, f'❌ Error: {error[:300]}', 'error')

                        # Continue execution even on error
                else:
                    log_entry['status']  = 'skipped'
                    log_entry['message'] = f'{node_name} has no code'
                    log_entry['state_diff'] = {}
                    logger.warning(f"Node {node_name} has no code to execute")
                    node_log(node_name, 'skipped (no code)', 'warning')

                execution_log.append(log_entry)
                time.sleep(0.3)

            # Send completion
            result_data = {
                'success': True,
                'nodes_executed': len(execution_order),
                'execution_time': f'{len(execution_order) * 0.3:.1f}s',
                'workflow_name': workflow.name,
                'final_state': fix_file_like_objects(current_state),  # Fix final state
                'execution_log': execution_log,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info("Workflow execution completed successfully")

            # Cache result so frontend can poll if socket missed the event
            execution_results_cache[execution_id] = {
                'status': 'completed',
                'result': result_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Remove from running tracker
            running_executions.pop(execution_id, None)

            socketio.emit('execution_complete', {
                'execution_id': execution_id,
                'workflow_id': workflow_id,
                'status': 'completed',
                'result': result_data,
                'message': 'Workflow execution completed',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

        except Exception as e:
            logger.error(f"Execution error: {str(e)}")
            error_trace = traceback.format_exc()
            logger.error(f"Traceback:\n{error_trace}")

            running_executions.pop(execution_id, None)

            socketio.emit('execution_error', {
                'execution_id': execution_id,
                'error': str(e),
                'traceback': error_trace,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            execution_results_cache[execution_id] = {
                'status': 'error',
                'error': str(e),
                'traceback': error_trace,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    # Run in background
    import threading
    thread = threading.Thread(target=execute_nodes_background)
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'Execution started',
        'execution_id': execution_id,
        'workflow_id': workflow_id
    })


# ==================== WEBSOCKET HANDLERS ====================

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to LangGraph Studio',
        'version': '1.2.0',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('workflow_update')
def handle_workflow_update(data):
    logger.info(f"Workflow update: {data}")
    emit('workflow_updated', data)


@socketio.on('node_created')
def handle_node_created(data):
    logger.info(f"Node created: {data}")
    emit('node_created', data)

# Node
@socketio.on('node_deleted')
def handle_node_deleted(data):
    logger.info(f"Node deleted: {data}")
    # Broadcast node removal to all connected clients
    emit('node_removed', data, broadcast=True)
# -----------------------

@socketio.on('execute_workflow')
def handle_execute_workflow(data):
    """Handle WebSocket execution request"""
    workflow_id = data.get('workflow_id')
    if not workflow_id:
        return

    execution_id = f"exec_ws_{int(time.time())}"

    emit('execution_started', {
        'execution_id': execution_id,
        'workflow_id': workflow_id,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

    # Simulate progress
    for i in range(1, 6):
        time.sleep(0.5)
        progress = i * 20
        emit('execution_progress', {
            'execution_id': execution_id,
            'progress': progress,
            'message': f'Step {i} of 5 completed',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    emit('execution_complete', {
        'execution_id': execution_id,
        'workflow_id': workflow_id,
        'status': 'completed',
        'result': {
            'success': True,
            'message': 'Workflow executed successfully via WebSocket'
        },
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


# ==================== EXPORT PACKAGE ====================

@app.route('/api/workflows/<workflow_id>/export_package', methods=['GET'])
def export_package(workflow_id):
    """Export workflow nodes as a standalone Python package (zip)."""
    import zipfile
    import io
    import textwrap

    workflow = Workflow.query.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404

    try:
        nodes_data = json.loads(workflow.nodes) if workflow.nodes else []
        edges_data = json.loads(workflow.edges) if workflow.edges else []
    except Exception:
        nodes_data, edges_data = [], []

    # Build execution order via BFS (handles branches like chemical_qc -> render_images + compute_features)
    code_nodes = [n for n in nodes_data if n.get('type') not in ('start', 'end') and n.get('code', '').strip()]

    from collections import defaultdict, deque
    adj = defaultdict(list)
    in_degree = defaultdict(int)
    all_ids = {n['id'] for n in nodes_data}
    for e in edges_data:
        adj[e['source']].append(e['target'])
        in_degree[e['target']] += 1

    # Topological sort (Kahn's algorithm)
    queue = deque([n['id'] for n in nodes_data if in_degree[n['id']] == 0])
    ordered_ids = []
    visited = set()
    while queue:
        cur = queue.popleft()
        if cur in visited:
            continue
        visited.add(cur)
        node = next((n for n in nodes_data if n['id'] == cur), None)
        if node and node.get('type') not in ('start', 'end') and node.get('code', '').strip():
            ordered_ids.append(cur)
        for nxt in adj[cur]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    ordered_nodes = [next((n for n in code_nodes if n['id'] == oid), None) for oid in ordered_ids]
    ordered_nodes = [n for n in ordered_nodes if n]

    workflow_name = (workflow.name or 'pipeline').replace(' ', '_').lower()
    pkg = workflow_name

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:

        # ── config.py ────────────────────────────────────────────────────
        config_src = textwrap.dedent("""\
            \"\"\"
            config.py — edit paths and hyperparameters here.
            \"\"\"
            import os

            # ── Paths (update these for your machine) ─────────────────────
            BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
            DATA_PATH  = os.path.join(BASE_DIR, 'data', 'input.xlsx')
            IMAGE_DIR  = os.path.join(BASE_DIR, 'data', 'mol_images')
            OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')
        """)
        zf.writestr(f'{pkg}/config.py', config_src)

        # ── nodes/__init__.py ────────────────────────────────────────────
        zf.writestr(f'{pkg}/nodes/__init__.py', '# nodes package\n')

        # ── one file per node ────────────────────────────────────────────
        for node in ordered_nodes:
            node_name = node.get('name', node['id']).replace(' ', '_').lower()
            raw_code  = node.get('code', '')

            # Wrap the process() function into a proper module function
            node_src = textwrap.dedent(f"""\
                \"\"\"
                Node: {node_name}
                {node.get('spec', {}).get('description', '')}

                Input keys : {node.get('spec', {}).get('input_key', '-')}
                Output keys: {node.get('spec', {}).get('output_key', '-')}
                \"\"\"

                {raw_code}


                def {node_name}(state: dict) -> dict:
                    return process(state)
            """)
            zf.writestr(f'{pkg}/nodes/{node_name}.py', node_src)

        # ── pipeline.py ──────────────────────────────────────────────────
        imports = '\n'.join(
            f"from nodes.{n.get('name','').replace(' ','_').lower()} import "
            f"{n.get('name','').replace(' ','_').lower()}"
            for n in ordered_nodes
        )
        node_list = ', '.join(f'"{n.get("name","").replace(" ","_").lower()}"' for n in ordered_nodes)
        fn_dict   = '\n'.join(
            f'    "{n.get("name","").replace(" ","_").lower()}": '
            f'{n.get("name","").replace(" ","_").lower()},'
            for n in ordered_nodes
        )
        pipeline_src = textwrap.dedent(f"""\
            \"\"\"Pipeline orchestrator — auto-generated from {workflow.name}.\"\"\"
            import time
            from typing import Optional

            {imports}

            NODE_ORDER = [{node_list}]

            NODE_FN = {{
            {fn_dict}
            }}


            class Pipeline:
                def run(self, stop_after: Optional[str] = None) -> dict:
                    state = {{}}
                    for node_name in NODE_ORDER:
                        print(f"▶ [{{node_name}}]")
                        t0 = time.time()
                        state = NODE_FN[node_name](state)
                        print(f"   ✓ done ({{time.time()-t0:.2f}}s)\\n")
                        if stop_after and node_name == stop_after:
                            print(f"⏹  Stopped after '{{stop_after}}'.")
                            break
                    return state
        """)
        zf.writestr(f'{pkg}/pipeline.py', pipeline_src)

        # ── run_pipeline.py ──────────────────────────────────────────────
        run_src = textwrap.dedent(f"""\
            \"\"\"
            Entry point for {workflow.name}.

            Terminal:
                python run_pipeline.py
                python run_pipeline.py --stop-after <node_name>

            PyCharm / Jupyter:
                from run_pipeline import run
                state = run(stop_after='scaffold_split')
                print(state.keys())
            \"\"\"
            import argparse
            import time
            from pipeline import Pipeline


            def run(stop_after=None) -> dict:
                return Pipeline().run(stop_after=stop_after)


            if __name__ == '__main__':
                parser = argparse.ArgumentParser()
                parser.add_argument('--stop-after', type=str, default=None)
                args = parser.parse_args()
                t0 = time.time()
                state = run(stop_after=args.stop_after)
                print(f"\\n✅ Done in {{time.time()-t0:.1f}}s  |  state keys: {{list(state.keys())}}")
        """)
        zf.writestr(f'{pkg}/run_pipeline.py', run_src)

        # ── requirements.txt ────────────────────────────────────────────
        zf.writestr(f'{pkg}/requirements.txt', 'rdkit>=2023.9.1\npandas>=2.0\nnumpy>=1.24\nPillow>=10.0\nopenpyxl>=3.1\n')

        # ── empty data / outputs dirs ────────────────────────────────────
        zf.writestr(f'{pkg}/data/.gitkeep', '')
        zf.writestr(f'{pkg}/outputs/.gitkeep', '')

    buf.seek(0)
    filename = f'{workflow_name}_package.zip'
    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )


# ==================== SVS / PATHOLOGY ROUTES ====================

@app.route('/api/svs/info')
def svs_info():
    """Return metadata for the configured SVS file."""
    path = request.args.get('path', TCGA_SVS_PATH)
    if not Path(path).exists():
        return jsonify({'error': f'SVS not found: {path}'}), 404
    try:
        from svs_utils import get_slide_info
        info = get_slide_info(path)
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/svs/thumbnail')
def svs_thumbnail():
    """Return a JPEG thumbnail of the SVS file (max 1024 px on longest side)."""
    path     = request.args.get('path', TCGA_SVS_PATH)
    max_size = int(request.args.get('max_size', 1024))
    if not Path(path).exists():
        return jsonify({'error': 'SVS not found'}), 404
    try:
        from svs_utils import get_thumbnail_bytes
        data = get_thumbnail_bytes(path, max_size=max_size)
        return send_file(BytesIO(data), mimetype='image/jpeg')
    except Exception as e:
        logger.error(f"Thumbnail error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/svs/patch')
def svs_patch():
    """Return a JPEG 512×512 patch at (x, y) from the SVS level 0."""
    path       = request.args.get('path', TCGA_SVS_PATH)
    x          = int(request.args.get('x', 0))
    y          = int(request.args.get('y', 0))
    patch_size = int(request.args.get('size', 512))
    if not Path(path).exists():
        return jsonify({'error': 'SVS not found'}), 404
    try:
        from svs_utils import read_patch_rgb, patch_to_jpeg_bytes
        rgb   = read_patch_rgb(path, x, y, patch_size)
        data  = patch_to_jpeg_bytes(rgb)
        return send_file(BytesIO(data), mimetype='image/jpeg')
    except Exception as e:
        logger.error(f"Patch error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/svs/tissue_tiles')
def svs_tissue_tiles():
    """Return JSON list of tissue tile coordinates."""
    path       = request.args.get('path', TCGA_SVS_PATH)
    patch_size = int(request.args.get('size', 512))
    threshold  = float(request.args.get('threshold', 0.4))
    max_tiles  = int(request.args.get('max', 400))
    if not Path(path).exists():
        return jsonify({'error': 'SVS not found'}), 404
    try:
        from svs_utils import extract_tissue_tiles
        tiles = extract_tissue_tiles(path, patch_size=patch_size,
                                     tissue_threshold=threshold,
                                     max_tiles=max_tiles)
        return jsonify({'n_tiles': len(tiles), 'tiles': tiles})
    except Exception as e:
        logger.error(f"Tissue tiles error: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found.',
        'status_code': 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred.',
        'status_code': 500
    }), 500


# ==================== INITIALIZATION ====================

def init_database():
    """Initialize database with sample data"""
    with app.app_context():
        # Create tables
        db.create_all()

        # Check if demo user exists
        demo_user = User.query.filter_by(username='demo').first()
        if not demo_user:
            demo_user = User(username='demo', email='demo@langgraph.studio')
            demo_user.set_password('demo123')
            db.session.add(demo_user)
            db.session.flush()  # Get ID before commit
            logger.info(f"Created demo user with ID: {demo_user.id}")

            # Create sample workflows - Use real user ID
            sample_workflows = [
                {
                    'name': 'Simple Chatbot',
                    'description': 'A basic chatbot workflow',
                    'nodes': [
                        {
                            "id": "start",
                            "type": "start",
                            "position": {"x": 100, "y": 100},
                            "code": "def process(state, params=None):\n    print('Starting chatbot...')\n    return state"
                        },
                        {
                            "id": "input",
                            "type": "input",
                            "position": {"x": 300, "y": 100},
                            "code": "def process(state, params=None):\n    print('Processing input...')\n    state['processed'] = True\n    return state"
                        },
                        {
                            "id": "llm",
                            "type": "llm",
                            "position": {"x": 500, "y": 100},
                            "code": "def process(state, params=None):\n    print('Simulating LLM response...')\n    state['response'] = 'Hello! How can I help you?'\n    return state"
                        },
                        {
                            "id": "output",
                            "type": "output",
                            "position": {"x": 700, "y": 100},
                            "code": "def process(state, params=None):\n    print('Final output:')\n    print(f\"Response: {state.get('response', 'No response')}\")\n    return state"
                        }
                    ],
                    'edges': [
                        {"id": "e1", "source": "start", "target": "input"},
                        {"id": "e2", "source": "input", "target": "llm"},
                        {"id": "e3", "source": "llm", "target": "output"}
                    ]
                },
                {
                    'name': 'Data Processing Pipeline',
                    'description': 'Process and analyze data',
                    'nodes': [
                        {
                            "id": "start",
                            "type": "start",
                            "position": {"x": 100, "y": 200},
                            "code": "def process(state, params=None):\n    print('Starting data processing...')\n    return state"
                        },
                        {
                            "id": "data_input",
                            "type": "input",
                            "position": {"x": 300, "y": 200},
                            "code": "def process(state, params=None):\n    print('Reading input data...')\n    state['data'] = 'Sample data to process'\n    return state"
                        },
                        {
                            "id": "process",
                            "type": "custom",
                            "position": {"x": 500, "y": 200},
                            "code": "def process(state, params=None):\n    print('Processing data...')\n    if 'data' in state:\n        state['processed_data'] = state['data'].upper()\n    return state"
                        },
                        {
                            "id": "result",
                            "type": "output",
                            "position": {"x": 700, "y": 200},
                            "code": "def process(state, params=None):\n    print('Final result:')\n    result = state.get('processed_data', 'No result')\n    print(f\"Processed: {result}\")\n    state['final_result'] = result\n    return state"
                        }
                    ],
                    'edges': [
                        {"id": "e1", "source": "start", "target": "data_input"},
                        {"id": "e2", "source": "data_input", "target": "process"},
                        {"id": "e3", "source": "process", "target": "result"}
                    ]
                }
            ]

            # ── TCGA-PAAD computational pathology workflow ──────────────────
            node1_code  = _load_node_code("node1_tiling.py")
            node21_code = _load_node_code("node2_1_rosie.py")
            node22_code = _load_node_code("node2_2_hed.py")
            node3_code  = _load_node_code("node3_petri_net.py")
            node4_code  = _load_node_code("node4_niche.py")

            tcga_workflow = {
                'name': 'TCGA-PAAD Spatiotemporal Pipeline',
                'description': (
                    'LLM-orchestrated computational pathology pipeline for '
                    'spatiotemporal reconstruction of the pancreatic tumour '
                    'microenvironment from H&E whole-slide images (SVS). '
                    'Node 1: Adaptive tiling | Node 2.1: ROSIE biomarker inference | '
                    'Node 2.2: HED segmentation | Node 3: Petri Net temporal model | '
                    'Node 4: Spatial niche analysis.'
                ),
                'nodes': [
                    {
                        "id": "start",
                        "name": "Start",
                        "type": "start",
                        "position": {"x": 80, "y": 300},
                        "code": (
                            "def process(state, params=None):\n"
                            "    import os\n"
                            f"    svs = state.get('svs_path', r'{TCGA_SVS_PATH}')\n"
                            "    state['svs_path'] = svs\n"
                            "    state['patch_size'] = 512\n"
                            "    state['tissue_threshold'] = 0.40\n"
                            "    state['max_tiles'] = 300\n"
                            "    print('=== TCGA-PAAD Spatiotemporal Pipeline ===')\n"
                            "    print(f'SVS : {os.path.basename(svs)}')\n"
                            "    print(f'Patch: {state[\"patch_size\"]}×{state[\"patch_size\"]} px')\n"
                            "    return state\n"
                        ),
                    },
                    {
                        "id": "node1_tiling",
                        "name": "Node 1 — Adaptive Tiling",
                        "type": "custom",
                        "position": {"x": 320, "y": 300},
                        "code": node1_code,
                        "spec": {
                            "description": "Adaptive WSI tiling with tissue detection",
                            "input_key": "svs_path, patch_size, tissue_threshold",
                            "output_key": "tiles, n_tiles, wsi_dims",
                        },
                    },
                    {
                        "id": "node2_1_rosie",
                        "name": "Node 2.1 — ROSIE Biomarker",
                        "type": "custom",
                        "position": {"x": 560, "y": 160},
                        "code": node21_code,
                        "spec": {
                            "description": "50-channel protein inference from H&E colour features",
                            "input_key": "tiles, svs_path",
                            "output_key": "protein_matrix, immune_score, stromal_score",
                        },
                    },
                    {
                        "id": "node2_2_hed",
                        "name": "Node 2.2 — HED Segmentation",
                        "type": "custom",
                        "position": {"x": 560, "y": 440},
                        "code": node22_code,
                        "spec": {
                            "description": "HED colour deconvolution + nucleus segmentation",
                            "input_key": "tiles, svs_path",
                            "output_key": "cell_features, n_cells, mean_nuclear_area",
                        },
                    },
                    {
                        "id": "node3_petri",
                        "name": "Node 3 — Petri Net",
                        "type": "custom",
                        "position": {"x": 800, "y": 300},
                        "code": node3_code,
                        "spec": {
                            "description": "Timed Petri Net temporal immune trajectory",
                            "input_key": "protein_matrix, immune_score, stromal_score",
                            "output_key": "temporal_trajectory, tpn_summary",
                        },
                    },
                    {
                        "id": "node4_niche",
                        "name": "Node 4 — Spatial Niche",
                        "type": "custom",
                        "position": {"x": 1040, "y": 300},
                        "code": node4_code,
                        "spec": {
                            "description": "DBSCAN+KMeans spatial niche construction",
                            "input_key": "tiles, protein_matrix, wsi_dims",
                            "output_key": "niches, pathway_heatmap, niche_summary",
                        },
                    },
                    {
                        "id": "end",
                        "name": "End",
                        "type": "end",
                        "position": {"x": 1280, "y": 300},
                        "code": (
                            "def process(state, params=None):\n"
                            "    print('=== Pipeline Complete ===')\n"
                            "    print(f'Tiles      : {state.get(\"n_tiles\", 0)}')\n"
                            "    print(f'Cells      : {state.get(\"n_cells\", 0)}')\n"
                            "    print(f'Niches     : {state.get(\"n_niches\", 0)}')\n"
                            "    print(f'Immune score  : {state.get(\"immune_score\", 0):.3f}')\n"
                            "    print(f'Stromal score : {state.get(\"stromal_score\", 0):.3f}')\n"
                            "    summary = state.get('niche_summary', '')\n"
                            "    if summary:\n"
                            "        print(f'Niche summary: {summary}')\n"
                            "    return state\n"
                        ),
                    },
                ],
                'edges': [
                    {"id": "e_start_n1",   "source": "start",        "target": "node1_tiling"},
                    {"id": "e_n1_n21",     "source": "node1_tiling", "target": "node2_1_rosie"},
                    {"id": "e_n1_n22",     "source": "node1_tiling", "target": "node2_2_hed"},
                    {"id": "e_n21_n3",     "source": "node2_1_rosie","target": "node3_petri"},
                    {"id": "e_n22_n3",     "source": "node2_2_hed",  "target": "node3_petri"},
                    {"id": "e_n3_n4",      "source": "node3_petri",  "target": "node4_niche"},
                    {"id": "e_n4_end",     "source": "node4_niche",  "target": "end"},
                ],
            }
            sample_workflows.append(tcga_workflow)
            # ── end TCGA workflow ────────────────────────────────────────────

            for workflow_data in sample_workflows:
                workflow = Workflow(
                    name=workflow_data['name'],
                    description=workflow_data['description'],
                    user_id=demo_user.id,
                    is_public=True
                )
                workflow.set_nodes(workflow_data['nodes'])
                workflow.set_edges(workflow_data['edges'])
                db.session.add(workflow)
                logger.info(f"Created workflow: {workflow_data['name']} for user: {demo_user.id}")

            db.session.commit()
            logger.info(f"Database initialized. Demo user ID: {demo_user.id}")


# ==================== MAIN ====================

def main():
    # Initialize database
    init_database()

    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')

    print("=" * 60)
    print("LangGraph Studio - Visual Workflow Builder")
    print(f"Version: 1.2.0")
    print("=" * 60)
    print(f"Dashboard: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/")
    print(f"Health Check: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/api/health")
    print("=" * 60)
    print("Available Endpoints:")
    print("  GET  /              - Dashboard")
    print("  POST /api/auth/register - Register user")
    print("  POST /api/auth/login    - Login")
    print("  GET  /api/workflows     - List workflows")
    print("  POST /api/workflows     - Create workflow")
    print("  PUT  /api/workflows/{id} - Update workflow")
    print("  POST /api/workflows/{id}/execute - Execute workflow")
    print("=" * 60)
    print("WebSocket Events:")
    print("  workflow_update - Update workflow")
    print("  node_created    - Create node")
    print("  execute_workflow - Execute via WebSocket")
    print("=" * 60)
    print("Sample Credentials:")
    print("  Username: demo")
    print("  Email: demo@langgraph.studio")
    print("  Password: demo123")
    print("=" * 60)
    print("Fixed Issues:")
    print("  - datetime.utcnow() deprecation (now uses timezone-aware UTC)")
    print("  - Print statements now properly captured and shown in output")
    print("  - Better output handling for empty prints")
    print("=" * 60)

    # Auto-open browser (skip if running inside Docker or CI)
    if os.environ.get("NO_BROWSER") != "1" and os.environ.get("DOCKER") != "1":
        import threading, webbrowser
        def _open():
            import time; time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}/")
        threading.Thread(target=_open, daemon=True).start()

    socketio.run(app,
                 host=host,
                 port=port,
                 debug=False,
                 use_reloader=False,
                 allow_unsafe_werkzeug=True)

if __name__ == '__main__':

    main()