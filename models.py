from database import db
from datetime import datetime
import json


class Node(db.Model):
    """Model for workflow nodes"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    node_type = db.Column(db.String(50), nullable=False)  # git_clone, env_setup, dependency_install, etc.
    description = db.Column(db.Text)
    configuration = db.Column(db.Text)  # JSON string for node parameters
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    executions = db.relationship('NodeExecution', backref='node', lazy=True, cascade='all, delete-orphan')
    workflow_steps = db.relationship('WorkflowStep', backref='node', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert node to dictionary for JSON response"""
        return {
            'id': self.id,
            'name': self.name,
            'node_type': self.node_type,
            'description': self.description,
            'configuration': json.loads(self.configuration) if self.configuration else {},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_config(self):
        """Get parsed configuration as dictionary"""
        if self.configuration:
            try:
                return json.loads(self.configuration)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_config(self, config_dict):
        """Set configuration from dictionary"""
        self.configuration = json.dumps(config_dict)


class Workflow(db.Model):
    """Model for workflows containing multiple nodes"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    steps = db.relationship('WorkflowStep', backref='workflow', lazy=True, order_by='WorkflowStep.order', cascade='all, delete-orphan')
    executions = db.relationship('WorkflowExecution', backref='workflow', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert workflow to dictionary for JSON response"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'steps': [step.to_dict() for step in self.steps],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class WorkflowStep(db.Model):
    """Model for steps within a workflow"""
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=False)
    node_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    parameters = db.Column(db.Text)  # JSON string for step-specific parameters
    
    def to_dict(self):
        """Convert workflow step to dictionary"""
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'node_id': self.node_id,
            'node_name': self.node.name if self.node else None,
            'node_type': self.node.node_type if self.node else None,
            'order': self.order,
            'parameters': json.loads(self.parameters) if self.parameters else {}
        }


class NodeExecution(db.Model):
    """Model for tracking node execution history"""
    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # pending, running, success, error
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    output = db.Column(db.Text)  # Execution output/logs
    error_message = db.Column(db.Text)
    parameters = db.Column(db.Text)  # JSON string of parameters used
    
    def to_dict(self):
        """Convert execution to dictionary for JSON response"""
        return {
            'id': self.id,
            'node_id': self.node_id,
            'node_name': self.node.name if self.node else None,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'output': self.output,
            'error_message': self.error_message,
            'parameters': json.loads(self.parameters) if self.parameters else {}
        }


class WorkflowExecution(db.Model):
    """Model for tracking workflow execution history"""
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # pending, running, success, error
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    current_step = db.Column(db.Integer, default=0)
    output = db.Column(db.Text)
    error_message = db.Column(db.Text)
    
    def to_dict(self):
        """Convert workflow execution to dictionary"""
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'workflow_name': self.workflow.name if self.workflow else None,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'current_step': self.current_step,
            'total_steps': len(self.workflow.steps) if self.workflow else 0,
            'output': self.output,
            'error_message': self.error_message
        }
