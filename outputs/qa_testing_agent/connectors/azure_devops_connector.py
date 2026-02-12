"""
Azure DevOps Connector
Connects to Azure DevOps to fetch user stories and requirements
"""
import logging
import requests
import json
from typing import List, Dict, Any, Optional
from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class AzureDevOpsStory:
    """Represents an Azure DevOps user story"""
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: int
    area_path: str
    iteration_path: str
    assigned_to: Optional[str] = None
    state: str = "New"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class AzureDevOpsConnector:
    """
    Connector to Azure DevOps for fetching user stories and requirements
    
    Usage:
        connector = AzureDevOpsConnector(
            organization="my-org",
            project="my-project",
            pat_token="your-pat-token"
        )
        stories = connector.get_user_stories(area_path="MyApp\\Features")
    """
    
    def __init__(self, organization: str, project: str, pat_token: str):
        """
        Initialize Azure DevOps connector
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            pat_token: Personal Access Token for authentication
        """
        self.organization = organization
        self.project = project
        self.pat_token = pat_token
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis"
        self.headers = self._get_headers()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _get_headers(self) -> Dict[str, str]:
        """Generate authentication headers"""
        # Encode PAT token for Basic auth
        auth_string = b64encode(f":{self.pat_token}".encode()).decode()
        
        return {
            "Authorization": f"Basic {auth_string}",
            "Content-Type": "application/json"
        }
    
    def get_user_stories(self, 
                        area_path: Optional[str] = None,
                        iteration_path: Optional[str] = None,
                        state: str = "Active",
                        top: int = 100) -> List[AzureDevOpsStory]:
        """
        Fetch user stories from Azure DevOps
        
        Args:
            area_path: Filter by area path (e.g., "MyProject\\Features")
            iteration_path: Filter by iteration path
            state: Filter by state (Active, Closed, etc.)
            top: Number of stories to fetch (max 200)
            
        Returns:
            List of AzureDevOpsStory objects
        """
        logger.info(f"Fetching user stories from Azure DevOps...")
        
        # Build WIQL query
        wiql_query = "Select [System.Id], [System.Title] From WorkItems"
        conditions = ["[System.WorkItemType] = 'User Story'"]
        
        if state:
            conditions.append(f"[System.State] = '{state}'")
        if area_path:
            conditions.append(f"[System.AreaPath] = '{area_path}'")
        if iteration_path:
            conditions.append(f"[System.IterationPath] = '{iteration_path}'")
        
        if conditions:
            wiql_query += " Where " + " AND ".join(conditions)
        
        wiql_query += f" Order By [System.CreatedDate] Desc"
        
        try:
            # Query work items
            stories = self._query_work_items(wiql_query)
            
            # Get detailed information for each story
            detailed_stories = []
            for story in stories[:top]:
                detailed = self._get_work_item_details(story["id"])
                if detailed:
                    detailed_stories.append(detailed)
            
            logger.info(f"Fetched {len(detailed_stories)} user stories")
            return detailed_stories
            
        except Exception as e:
            logger.error(f"Error fetching user stories: {str(e)}")
            raise
    
    def _query_work_items(self, wiql_query: str) -> List[Dict[str, Any]]:
        """Execute WIQL query to get work items"""
        url = f"{self.base_url}/wit/wiql"
        
        payload = {"query": wiql_query}
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data.get("workItems", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"WIQL Query failed: {str(e)}")
            raise
    
    def _get_work_item_details(self, work_item_id: int) -> Optional[AzureDevOpsStory]:
        """
        Get detailed information for a work item
        
        Args:
            work_item_id: Work item ID
            
        Returns:
            AzureDevOpsStory or None if fetch fails
        """
        url = f"{self.base_url}/wit/workitems/{work_item_id}"
        params = {
            "api-version": "7.0",
            "$expand": "relations"
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            item = response.json()
            fields = item.get("fields", {})
            
            # Extract acceptance criteria from description or custom field
            acceptance_criteria = self._extract_acceptance_criteria(
                fields.get("System.Description", "")
            )
            
            story = AzureDevOpsStory(
                id=str(item.get("id", "")),
                title=fields.get("System.Title", ""),
                description=fields.get("System.Description", ""),
                acceptance_criteria=acceptance_criteria,
                priority=fields.get("Microsoft.VSTS.Common.Priority", 3),
                area_path=fields.get("System.AreaPath", ""),
                iteration_path=fields.get("System.IterationPath", ""),
                assigned_to=fields.get("System.AssignedTo", {}).get("displayName"),
                state=fields.get("System.State", "New"),
                tags=fields.get("System.Tags", "").split(";") if fields.get("System.Tags") else []
            )
            
            return story
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get details for work item {work_item_id}: {str(e)}")
            return None
    
    def _extract_acceptance_criteria(self, description: str) -> List[str]:
        """
        Extract acceptance criteria from description
        
        Looks for "Acceptance Criteria:" section or bullet points
        
        Args:
            description: Work item description
            
        Returns:
            List of acceptance criteria
        """
        if not description:
            return []
        
        criteria = []
        lines = description.split('\n')
        in_criteria_section = False
        
        for line in lines:
            line = line.strip()
            
            # Look for acceptance criteria section
            if "acceptance criteria" in line.lower():
                in_criteria_section = True
                continue
            
            # Extract bullet points or numbered items
            if in_criteria_section:
                if line.startswith(('- ', '* ', '• ')) or line[0:1].isdigit() and '.' in line[:3]:
                    # Remove bullet/number prefix
                    criterion = line.lstrip('- *•0123456789. ').strip()
                    if criterion:
                        criteria.append(criterion)
                elif line == "":
                    # Empty line might end criteria section
                    pass
                elif not line[0:1].isspace() and line:
                    # New section started
                    in_criteria_section = False
        
        return criteria if criteria else ["Execute the user story functionality"]
    
    def get_story_by_id(self, story_id: int) -> Optional[AzureDevOpsStory]:
        """Get a specific story by ID"""
        try:
            return self._get_work_item_details(story_id)
        except Exception as e:
            logger.error(f"Error fetching story {story_id}: {str(e)}")
            return None
    
    def get_story_by_area(self, area_path: str) -> List[AzureDevOpsStory]:
        """Get all stories in a specific area"""
        return self.get_user_stories(area_path=area_path)
    
    def get_story_by_iteration(self, iteration_path: str) -> List[AzureDevOpsStory]:
        """Get all stories in a specific iteration/sprint"""
        return self.get_user_stories(iteration_path=iteration_path)
    
    def update_story_status(self, story_id: int, new_state: str) -> bool:
        """
        Update story status after test execution
        
        Args:
            story_id: Work item ID
            new_state: New state (e.g., "Testing", "Tested")
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/wit/workitems/{story_id}"
        params = {"api-version": "7.0"}
        
        # PATCH request format
        patch_data = [
            {
                "op": "replace",
                "path": "/fields/System.State",
                "value": new_state
            }
        ]
        
        try:
            response = self.session.patch(
                url,
                json=patch_data,
                params=params,
                headers={"Content-Type": "application/json-patch+json"}
            )
            response.raise_for_status()
            
            logger.info(f"Updated story {story_id} status to {new_state}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update story {story_id}: {str(e)}")
            return False
    
    def add_test_results_comment(self, story_id: int, test_results: str) -> bool:
        """
        Add test results as comment to work item
        
        Args:
            story_id: Work item ID
            test_results: Test results summary
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/wit/workitems/{story_id}/comments"
        params = {"api-version": "7.0-preview.3"}
        
        data = {
            "text": f"[TEST RESULTS]\n{test_results}\n\nGenerated by QA Testing Agent"
        }
        
        try:
            response = self.session.post(url, json=data, params=params)
            response.raise_for_status()
            
            logger.info(f"Added test results comment to story {story_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add comment to story {story_id}: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """Test Azure DevOps connection"""
        try:
            url = f"{self.base_url}/projects"
            params = {"api-version": "7.0", "$top": "1"}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            logger.info("Azure DevOps connection successful")
            return True
            
        except Exception as e:
            logger.error(f"Azure DevOps connection failed: {str(e)}")
            return False
