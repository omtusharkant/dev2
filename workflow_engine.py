import logging
import json
from datetime import datetime
from models import WorkflowExecution
from database import db
from node_executor import NodeExecutor

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Engine for executing workflows with multiple nodes"""
    
    def __init__(self):
        self.node_executor = NodeExecutor()
    
    def execute_workflow(self, workflow, parameters=None):
        """Execute a workflow with all its steps"""
        # Create workflow execution record
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            status='running'
        )
        db.session.add(execution)
        db.session.commit()
        
        output_lines = []
        
        try:
            logger.info(f"Starting execution of workflow: {workflow.name}")
            
            # Execute each step in order
            for i, step in enumerate(workflow.steps):
                execution.current_step = i + 1
                db.session.commit()
                
                logger.info(f"Executing step {i + 1}/{len(workflow.steps)}: {step.node.name}")
                
                # Merge step parameters with workflow parameters
                step_params = json.loads(step.parameters) if step.parameters else {}
                if parameters:
                    step_params.update(parameters)
                
                # Execute the node
                result = self.node_executor.execute_node(step.node, step_params)
                
                if result['success']:
                    output_lines.append(f"Step {i + 1} ({step.node.name}): SUCCESS")
                    output_lines.append(result['output'])
                else:
                    # Workflow failed at this step
                    error_msg = f"Step {i + 1} ({step.node.name}) failed: {result['error']}"
                    output_lines.append(error_msg)
                    
                    execution.status = 'error'
                    execution.error_message = error_msg
                    execution.end_time = datetime.utcnow()
                    execution.output = '\n'.join(output_lines)
                    db.session.commit()
                    
                    logger.error(f"Workflow {workflow.name} failed at step {i + 1}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'execution_id': execution.id
                    }
                
                output_lines.append('')  # Add blank line between steps
            
            # All steps completed successfully
            execution.status = 'success'
            execution.end_time = datetime.utcnow()
            execution.output = '\n'.join(output_lines)
            db.session.commit()
            
            logger.info(f"Workflow {workflow.name} completed successfully")
            return {
                'success': True,
                'output': '\n'.join(output_lines),
                'execution_id': execution.id
            }
            
        except Exception as e:
            # Unexpected error during workflow execution
            execution.status = 'error'
            execution.error_message = str(e)
            execution.end_time = datetime.utcnow()
            execution.output = '\n'.join(output_lines)
            db.session.commit()
            
            logger.error(f"Workflow {workflow.name} failed with unexpected error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'execution_id': execution.id
            }
    
    def get_execution_status(self, execution_id):
        """Get the status of a workflow execution"""
        execution = WorkflowExecution.query.get(execution_id)
        if not execution:
            return None
        
        return execution.to_dict()
