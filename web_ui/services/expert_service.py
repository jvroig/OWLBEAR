import os
import yaml
import logging
from typing import List, Dict, Any, Optional
import sys

# Add the parent directory to the path to be able to import OWLBEAR modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger("owlbear-web-ui.expert-service")

class ExpertService:
    """Service for managing OWLBEAR experts."""
    
    def __init__(self):
        self.experts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "experts")
        self.experts_cache = {}  # Cache expert data to avoid repeated file operations
        
    async def list_experts(self) -> List[Dict[str, Any]]:
        """
        List all available experts.
        
        Returns:
            List[Dict[str, Any]]: List of expert summary information
        """
        experts = []
        
        # List all YAML files in the experts directory
        for filename in os.listdir(self.experts_dir):
            if filename.endswith(('.yml', '.yaml')):
                try:
                    # Load the expert file to extract metadata
                    with open(os.path.join(self.experts_dir, filename), 'r') as file:
                        expert_data = yaml.safe_load(file)
                    
                    # Skip files without required fields
                    if 'ExpertID' not in expert_data or 'SystemPrompt' not in expert_data:
                        logger.warning(f"Expert file {filename} missing required fields")
                        continue
                    
                    # Extract expert information
                    expert_id = expert_data['ExpertID']
                    description = expert_data.get('Description', f"Expert {expert_id}")
                    
                    # Extract tools available to this expert
                    tools = expert_data.get('ToolsAvailable', [])
                    
                    # Create basic expert info
                    experts.append({
                        "id": expert_id,
                        "name": expert_id,  # Preserve original case
                        "description": description,
                        "tools": tools,
                        "icon": expert_data.get('Icon', 'user')  # Default icon is 'user'
                    })
                    
                    # Cache the expert data
                    self.experts_cache[expert_id] = expert_data
                    
                except Exception as e:
                    logger.error(f"Error loading expert {filename}: {str(e)}")
        
        return experts
    
    async def get_expert_details(self, expert_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific expert.
        
        Args:
            expert_id (str): ID of the expert
            
        Returns:
            Dict[str, Any]: Detailed expert information
            
        Raises:
            FileNotFoundError: If the expert is not found
        """

        # Check cache first
        expert_id_lower = expert_id.lower()
        if expert_id_lower in self.experts_cache:
            expert_data = self.experts_cache[expert_id_lower]
        else:
            # Try to find the expert file
            expert_data = await self._find_expert(expert_id)
            
            if expert_data:
                # Cache the expert data
                self.experts_cache[expert_id_lower] = expert_data
            else:
                raise FileNotFoundError(f"Expert {expert_id} not found")
        
        # Build response
        endpoint_info = expert_data.get('Endpoint', {})
        
        # Get icon value
        icon_value = expert_data.get('Icon', 'user')
        
        return {
            "id": expert_data['ExpertID'],
            "name": expert_data['ExpertID'],  # Preserve original case
            "description": expert_data.get('Description', f"Expert {expert_id}"),
            "system_prompt": expert_data['SystemPrompt'],
            "tools": expert_data.get('ToolsAvailable', []),
            "icon": icon_value,  # Default icon is 'user'
            "endpoint": {
                "host": endpoint_info.get('Host', None),
                "model": endpoint_info.get('Model', None)
            }
        }
    
    async def _find_expert(self, expert_id: str) -> Optional[Dict[str, Any]]:
        """
        Find an expert by ID in the experts directory.
        
        Args:
            expert_id (str): ID of the expert to find
            
        Returns:
            Optional[Dict[str, Any]]: Expert data if found, None otherwise
        """
        expert_id_lower = expert_id.lower()
        
        # List all YAML files in the experts directory
        for filename in os.listdir(self.experts_dir):
            if filename.endswith(('.yml', '.yaml')):
                try:
                    # Load the expert file
                    with open(os.path.join(self.experts_dir, filename), 'r') as file:
                        expert_data = yaml.safe_load(file)
                    
                    # Check if this is the expert we're looking for
                    if 'ExpertID' in expert_data and expert_data['ExpertID'].lower() == expert_id_lower:
                        return expert_data
                        
                except Exception as e:
                    logger.error(f"Error loading expert {filename}: {str(e)}")
        
        return None
    
    def _format_expert_name(self, expert_id: str) -> str:
        """
        Format an expert ID into a display name.
        
        Args:
            expert_id (str): Expert ID
            
        Returns:
            str: Formatted display name
        """
        # Replace hyphens and underscores with spaces
        name = expert_id.replace('-', ' ').replace('_', ' ')
        
        # Split CamelCase into separate words
        import re
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        
        # Title case
        return name.title()
