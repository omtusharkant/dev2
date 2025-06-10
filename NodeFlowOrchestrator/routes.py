from flask import render_template, request, jsonify, abort
from app import app, db
from models import Node, Workflow, WorkflowStep, NodeExecution, WorkflowExecution
from node_executor import NodeExecutor
from workflow_engine import WorkflowEngine
import json
import logging

logger = logging.getLogger(__name__)

# Initialize executors
node_executor = NodeExecutor()
workflow_engine = WorkflowEngine()


@app.route('/')
def index():
    """Main documentation interface"""
    return render_template('index.html')


# Node Management Routes

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Get all nodes"""
    nodes = Node.query.all()
    return jsonify([node.to_dict() for node in nodes])


@app.route('/api/nodes', methods=['POST'])
def create_node():
    """Create a new node"""
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('node_type'):
        return jsonify({'error': 'Name and node_type are required'}), 400
    
    try:
        node = Node(
            name=data['name'],
            node_type=data['node_type'],
            description=data.get('description', ''),
            configuration=json.dumps(data.get('configuration', {}))
        )
        
        db.session.add(node)
        db.session.commit()
        
        logger.info(f"Created node: {node.name}")
        return jsonify(node.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create node: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes/<int:node_id>', methods=['GET'])
def get_node(node_id):
    """Get a specific node"""
    node = Node.query.get_or_404(node_id)
    return jsonify(node.to_dict())


@app.route('/api/nodes/<int:node_id>', methods=['PUT'])
def update_node(node_id):
    """Update a node"""
    node = Node.query.get_or_404(node_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        if 'name' in data:
            node.name = data['name']
        if 'node_type' in data:
            node.node_type = data['node_type']
        if 'description' in data:
            node.description = data['description']
        if 'configuration' in data:
            node.configuration = json.dumps(data['configuration'])
        
        db.session.commit()
        
        logger.info(f"Updated node: {node.name}")
        return jsonify(node.to_dict())
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update node {node_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes/<int:node_id>', methods=['DELETE'])
def delete_node(node_id):
    """Delete a node"""
    node = Node.query.get_or_404(node_id)
    
    try:
        db.session.delete(node)
        db.session.commit()
        
        logger.info(f"Deleted node: {node.name}")
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete node {node_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes/<int:node_id>/execute', methods=['POST'])
def execute_node(node_id):
    """Execute a specific node"""
    node = Node.query.get_or_404(node_id)
    data = request.get_json() or {}
    
    parameters = data.get('parameters', {})
    
    try:
        result = node_executor.execute_node(node, parameters)
        
        if result['success']:
            return jsonify({
                'success': True,
                'output': result['output'],
                'node_name': node.name
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'node_name': node.name
            }), 400
            
    except Exception as e:
        logger.error(f"Failed to execute node {node_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Workflow Management Routes

@app.route('/api/workflows', methods=['GET'])
def get_workflows():
    """Get all workflows"""
    workflows = Workflow.query.all()
    return jsonify([workflow.to_dict() for workflow in workflows])


@app.route('/api/workflows', methods=['POST'])
def create_workflow():
    """Create a new workflow"""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400
    
    try:
        workflow = Workflow(
            name=data['name'],
            description=data.get('description', '')
        )
        
        db.session.add(workflow)
        db.session.flush()  # Get the ID
        
        # Add steps if provided
        if 'steps' in data:
            for step_data in data['steps']:
                if 'node_id' not in step_data or 'order' not in step_data:
                    return jsonify({'error': 'Each step must have node_id and order'}), 400
                
                step = WorkflowStep(
                    workflow_id=workflow.id,
                    node_id=step_data['node_id'],
                    order=step_data['order'],
                    parameters=json.dumps(step_data.get('parameters', {}))
                )
                db.session.add(step)
        
        db.session.commit()
        
        logger.info(f"Created workflow: {workflow.name}")
        return jsonify(workflow.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create workflow: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows/<int:workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    """Get a specific workflow"""
    workflow = Workflow.query.get_or_404(workflow_id)
    return jsonify(workflow.to_dict())


@app.route('/api/workflows/<int:workflow_id>', methods=['PUT'])
def update_workflow(workflow_id):
    """Update a workflow"""
    workflow = Workflow.query.get_or_404(workflow_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        if 'name' in data:
            workflow.name = data['name']
        if 'description' in data:
            workflow.description = data['description']
        
        # Update steps if provided
        if 'steps' in data:
            # Remove existing steps
            WorkflowStep.query.filter_by(workflow_id=workflow.id).delete()
            
            # Add new steps
            for step_data in data['steps']:
                if 'node_id' not in step_data or 'order' not in step_data:
                    return jsonify({'error': 'Each step must have node_id and order'}), 400
                
                step = WorkflowStep(
                    workflow_id=workflow.id,
                    node_id=step_data['node_id'],
                    order=step_data['order'],
                    parameters=json.dumps(step_data.get('parameters', {}))
                )
                db.session.add(step)
        
        db.session.commit()
        
        logger.info(f"Updated workflow: {workflow.name}")
        return jsonify(workflow.to_dict())
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update workflow {workflow_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows/<int:workflow_id>', methods=['DELETE'])
def delete_workflow(workflow_id):
    """Delete a workflow"""
    workflow = Workflow.query.get_or_404(workflow_id)
    
    try:
        db.session.delete(workflow)
        db.session.commit()
        
        logger.info(f"Deleted workflow: {workflow.name}")
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete workflow {workflow_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows/<int:workflow_id>/execute', methods=['POST'])
def execute_workflow(workflow_id):
    """Execute a workflow"""
    workflow = Workflow.query.get_or_404(workflow_id)
    data = request.get_json() or {}
    
    parameters = data.get('parameters', {})
    
    try:
        result = workflow_engine.execute_workflow(workflow, parameters)
        
        if result['success']:
            return jsonify({
                'success': True,
                'output': result['output'],
                'execution_id': result['execution_id'],
                'workflow_name': workflow.name
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'execution_id': result['execution_id'],
                'workflow_name': workflow.name
            }), 400
            
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Execution History Routes

@app.route('/api/executions/nodes', methods=['GET'])
def get_node_executions():
    """Get node execution history"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    executions = NodeExecution.query.order_by(NodeExecution.start_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'executions': [execution.to_dict() for execution in executions.items],
        'total': executions.total,
        'pages': executions.pages,
        'current_page': page
    })


@app.route('/api/executions/workflows', methods=['GET'])
def get_workflow_executions():
    """Get workflow execution history"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    executions = WorkflowExecution.query.order_by(WorkflowExecution.start_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'executions': [execution.to_dict() for execution in executions.items],
        'total': executions.total,
        'pages': executions.pages,
        'current_page': page
    })


@app.route('/api/executions/workflows/<int:execution_id>', methods=['GET'])
def get_workflow_execution(execution_id):
    """Get specific workflow execution details"""
    execution = WorkflowExecution.query.get_or_404(execution_id)
    return jsonify(execution.to_dict())


# Node Type Information

@app.route('/api/node-types', methods=['GET'])
def get_node_types():
    """Get available node types and their configuration schemas"""
    node_types = {
        'git_clone': {
            'name': 'Git Clone',
            'description': 'Clone a Git repository',
            'parameters': {
                'url': {'type': 'string', 'required': True, 'description': 'Git repository URL'},
                'branch': {'type': 'string', 'required': False, 'default': 'main', 'description': 'Branch to clone'},
                'target_dir': {'type': 'string', 'required': False, 'default': './cloned_repo', 'description': 'Target directory'}
            }
        },
        'env_setup': {
            'name': 'Environment Setup',
            'description': 'Set environment variables',
            'parameters': {
                'environment_variables': {'type': 'object', 'required': True, 'description': 'Key-value pairs of environment variables'}
            }
        },
        'dependency_install': {
            'name': 'Dependency Installation',
            'description': 'Install dependencies using package managers',
            'parameters': {
                'package_manager': {'type': 'string', 'required': False, 'default': 'pip', 'description': 'Package manager (pip, npm)'},
                'packages': {'type': 'array', 'required': False, 'description': 'List of packages to install'},
                'requirements_file': {'type': 'string', 'required': False, 'description': 'Path to requirements file'}
            }
        },
        'shell_command': {
            'name': 'Shell Command',
            'description': 'Execute shell commands',
            'parameters': {
                'command': {'type': 'string', 'required': True, 'description': 'Command to execute'},
                'working_dir': {'type': 'string', 'required': False, 'default': '.', 'description': 'Working directory'},
                'timeout': {'type': 'integer', 'required': False, 'default': 300, 'description': 'Timeout in seconds'}
            }
        },
        'file_operation': {
            'name': 'File Operation',
            'description': 'Perform file operations',
            'parameters': {
                'operation': {'type': 'string', 'required': True, 'description': 'Operation type (copy, move, delete, create)'},
                'source': {'type': 'string', 'required': False, 'description': 'Source path'},
                'destination': {'type': 'string', 'required': False, 'description': 'Destination path'},
                'content': {'type': 'string', 'required': False, 'description': 'File content for create operation'}
            }
        }
    }
    
    return jsonify(node_types)


# Error handlers

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500
