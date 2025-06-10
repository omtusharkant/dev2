import subprocess
import os
import logging
import json
from datetime import datetime
from models import NodeExecution, db

logger = logging.getLogger(__name__)


class NodeExecutor:
    """Class responsible for executing different types of nodes"""
    
    def __init__(self):
        self.node_types = {
            'git_clone': self._execute_git_clone,
            'env_setup': self._execute_env_setup,
            'dependency_install': self._execute_dependency_install,
            'shell_command': self._execute_shell_command,
            'file_operation': self._execute_file_operation
        }
    
    def execute_node(self, node, parameters=None):
        """Execute a node with given parameters"""
        # Create execution record
        execution = NodeExecution(
            node_id=node.id,
            status='running',
            parameters=json.dumps(parameters or {})
        )
        db.session.add(execution)
        db.session.commit()
        
        try:
            # Merge node configuration with execution parameters
            config = node.get_config()
            if parameters:
                config.update(parameters)
            
            # Execute based on node type
            if node.node_type in self.node_types:
                result = self.node_types[node.node_type](config)
                
                # Update execution record with success
                execution.status = 'success'
                execution.output = result.get('output', '')
                execution.end_time = datetime.utcnow()
                
                logger.info(f"Node {node.name} executed successfully")
                return {'success': True, 'output': result.get('output', '')}
                
            else:
                raise ValueError(f"Unsupported node type: {node.node_type}")
                
        except Exception as e:
            # Update execution record with error
            execution.status = 'error'
            execution.error_message = str(e)
            execution.end_time = datetime.utcnow()
            
            logger.error(f"Node {node.name} execution failed: {str(e)}")
            return {'success': False, 'error': str(e)}
        
        finally:
            db.session.commit()
    
    def _execute_git_clone(self, config):
        """Execute git clone operation"""
        url = config.get('url')
        branch = config.get('branch', 'main')
        target_dir = config.get('target_dir', './cloned_repo')
        
        if not url:
            raise ValueError("Git URL is required")
        
        # Prepare git clone command
        cmd = ['git', 'clone', '--branch', branch, url, target_dir]
        
        # Execute command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")
        
        return {
            'output': f"Successfully cloned {url} (branch: {branch}) to {target_dir}\n{result.stdout}"
        }
    
    def _execute_env_setup(self, config):
        """Execute environment setup"""
        env_vars = config.get('environment_variables', {})
        output_lines = []
        
        for key, value in env_vars.items():
            os.environ[key] = str(value)
            output_lines.append(f"Set {key}={value}")
        
        return {
            'output': '\n'.join(output_lines) if output_lines else 'No environment variables to set'
        }
    
    def _execute_dependency_install(self, config):
        """Execute dependency installation"""
        package_manager = config.get('package_manager', 'pip')
        packages = config.get('packages', [])
        requirements_file = config.get('requirements_file')
        
        output_lines = []
        
        if requirements_file:
            # Install from requirements file
            if package_manager == 'pip':
                cmd = ['pip', 'install', '-r', requirements_file]
            elif package_manager == 'npm':
                cmd = ['npm', 'install']
            else:
                raise ValueError(f"Unsupported package manager: {package_manager}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                raise RuntimeError(f"Dependency installation failed: {result.stderr}")
            
            output_lines.append(f"Installed dependencies from {requirements_file}")
            output_lines.append(result.stdout)
        
        if packages:
            # Install individual packages
            for package in packages:
                if package_manager == 'pip':
                    cmd = ['pip', 'install', package]
                elif package_manager == 'npm':
                    cmd = ['npm', 'install', package]
                else:
                    raise ValueError(f"Unsupported package manager: {package_manager}")
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to install {package}: {result.stderr}")
                
                output_lines.append(f"Installed {package}")
        
        return {
            'output': '\n'.join(output_lines) if output_lines else 'No packages to install'
        }
    
    def _execute_shell_command(self, config):
        """Execute shell command"""
        command = config.get('command')
        working_dir = config.get('working_dir', '.')
        timeout = config.get('timeout', 300)
        
        if not command:
            raise ValueError("Command is required")
        
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=working_dir,
            timeout=timeout
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Command failed with exit code {result.returncode}: {result.stderr}")
        
        return {
            'output': f"Command executed successfully\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        }
    
    def _execute_file_operation(self, config):
        """Execute file operations"""
        operation = config.get('operation')  # copy, move, delete, create
        source = config.get('source')
        destination = config.get('destination')
        content = config.get('content')
        
        if operation == 'create':
            if not destination or content is None:
                raise ValueError("Destination and content are required for create operation")
            
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, 'w') as f:
                f.write(content)
            
            return {'output': f"Created file: {destination}"}
        
        elif operation == 'copy':
            if not source or not destination:
                raise ValueError("Source and destination are required for copy operation")
            
            import shutil
            shutil.copy2(source, destination)
            
            return {'output': f"Copied {source} to {destination}"}
        
        elif operation == 'move':
            if not source or not destination:
                raise ValueError("Source and destination are required for move operation")
            
            import shutil
            shutil.move(source, destination)
            
            return {'output': f"Moved {source} to {destination}"}
        
        elif operation == 'delete':
            if not source:
                raise ValueError("Source is required for delete operation")
            
            if os.path.isfile(source):
                os.remove(source)
                return {'output': f"Deleted file: {source}"}
            elif os.path.isdir(source):
                import shutil
                shutil.rmtree(source)
                return {'output': f"Deleted directory: {source}"}
            else:
                raise ValueError(f"Path does not exist: {source}")
        
        else:
            raise ValueError(f"Unsupported file operation: {operation}")
