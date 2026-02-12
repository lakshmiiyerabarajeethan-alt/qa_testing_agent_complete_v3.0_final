"""
CSV Story Reader
Reads user stories from CSV files and converts them to TestCase objects
Supports any project management tool (Azure DevOps, Jira, Linear, etc.)
"""
import logging
import csv
import os
from typing import List, Dict, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CSVStory:
    """Represents a story read from CSV"""
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: int
    state: str
    assignee: str
    story_points: int
    area_iteration: str
    tags: List[str]
    
    def __post_init__(self):
        """Post-initialization validation"""
        if not self.title:
            raise ValueError("Title/Summary is required")
        if not self.description:
            self.description = ""
        if not self.acceptance_criteria:
            self.acceptance_criteria = []
        if not self.assignee:
            self.assignee = "Unassigned"
        if not self.tags:
            self.tags = []

class CSVStoryReader:
    """
    Reads user stories from CSV files
    
    Expected CSV columns (order flexible, names case-insensitive):
    - Title (or Summary)
    - Description
    - Acceptance Criteria (or Acceptance_Criteria)
    - Priority (1-5, optional)
    - State (or Status)
    - Assignee
    - Story Points (optional)
    - Area (or Iteration, Area_Iteration)
    - Tags (or Labels)
    
    Example:
        reader = CSVStoryReader("./stories")
        stories = reader.read_all_stories()
    """
    
    # Column name mappings (case-insensitive)
    REQUIRED_COLUMNS = {
        'title': ['title', 'summary', 'story title', 'feature title'],
        'description': ['description', 'story description', 'details', 'narrative'],
        'acceptance_criteria': ['acceptance criteria', 'acceptance_criteria', 'criteria', 'acceptance'],
        'state': ['state', 'status', 'story status', 'work item type'],
    }
    
    OPTIONAL_COLUMNS = {
        'priority': ['priority', 'priority level'],
        'assignee': ['assignee', 'assigned to', 'owner'],
        'story_points': ['story points', 'points', 'estimation'],
        'area_iteration': ['area', 'iteration', 'area path', 'iteration path', 'sprint'],
        'tags': ['tags', 'labels', 'keywords'],
    }
    
    def __init__(self, stories_folder: str = "./stories"):
        """
        Initialize CSV Story Reader
        
        Args:
            stories_folder: Folder containing CSV story files
        """
        self.stories_folder = stories_folder
        self.file_encoding = 'utf-8'
        os.makedirs(stories_folder, exist_ok=True)
    
    def read_all_stories(self) -> List[CSVStory]:
        """
        Read all CSV files from the stories folder
        
        Returns:
            List of CSVStory objects
        """
        logger.info(f"\n[CSV Story Reader] Scanning folder: {self.stories_folder}")
        
        csv_files = list(Path(self.stories_folder).glob("*.csv"))
        
        if not csv_files:
            logger.warning(f"No CSV files found in {self.stories_folder}")
            return []
        
        logger.info(f"Found {len(csv_files)} CSV file(s)")
        
        all_stories = []
        
        for csv_file in csv_files:
            logger.info(f"\nReading: {csv_file.name}")
            stories = self.read_csv_file(str(csv_file))
            all_stories.extend(stories)
            logger.info(f"  Loaded {len(stories)} stories from {csv_file.name}")
        
        logger.info(f"\nTotal stories loaded: {len(all_stories)}")
        return all_stories
    
    def read_csv_file(self, filepath: str) -> List[CSVStory]:
        """
        Read a single CSV file
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            List of CSVStory objects
        """
        stories = []
        
        try:
            with open(filepath, 'r', encoding=self.file_encoding) as csvfile:
                # Detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                delimiter = self._detect_delimiter(sample)
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                
                if not reader.fieldnames:
                    logger.error(f"No headers found in {filepath}")
                    return stories
                
                # Map column names
                column_mapping = self._map_columns(reader.fieldnames)
                
                row_num = 0
                for row_num, row in enumerate(reader, 1):
                    try:
                        story = self._parse_row(row, column_mapping)
                        if story:
                            stories.append(story)
                    except Exception as e:
                        logger.warning(f"  Row {row_num}: Error parsing row - {str(e)}")
                        continue
                
                logger.info(f"  Processed {row_num} rows, {len(stories)} valid stories")
                
        except Exception as e:
            logger.error(f"Error reading CSV file {filepath}: {str(e)}")
        
        return stories
    
    def _detect_delimiter(self, sample: str) -> str:
        """
        Detect CSV delimiter from sample
        
        Args:
            sample: Sample of file content
            
        Returns:
            Detected delimiter (comma, semicolon, or tab)
        """
        delimiters = [',', ';', '\t']
        delimiter_counts = {d: sample.count(d) for d in delimiters}
        
        # Return the delimiter with the highest count
        return max(delimiter_counts, key=delimiter_counts.get)
    
    def _map_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """
        Map CSV column names to our internal field names
        
        Args:
            fieldnames: Column names from CSV
            
        Returns:
            Mapping dictionary
        """
        mapping = {}
        fieldnames_lower = {f.lower().strip(): f for f in fieldnames}
        
        # Map required columns
        for field, aliases in self.REQUIRED_COLUMNS.items():
            for alias in aliases:
                if alias.lower() in fieldnames_lower:
                    mapping[field] = fieldnames_lower[alias.lower()]
                    break
        
        # Map optional columns
        for field, aliases in self.OPTIONAL_COLUMNS.items():
            for alias in aliases:
                if alias.lower() in fieldnames_lower:
                    mapping[field] = fieldnames_lower[alias.lower()]
                    break
        
        return mapping
    
    def _parse_row(self, row: Dict, column_mapping: Dict) -> CSVStory:
        """
        Parse a CSV row into a CSVStory object
        
        Args:
            row: CSV row as dictionary
            column_mapping: Column name mapping
            
        Returns:
            CSVStory object or None if invalid
        """
        # Extract required fields
        title = row.get(column_mapping.get('title', ''), '').strip()
        description = row.get(column_mapping.get('description', ''), '').strip()
        acceptance_criteria_str = row.get(column_mapping.get('acceptance_criteria', ''), '').strip()
        state = row.get(column_mapping.get('state', ''), 'New').strip()
        
        # Extract optional fields
        priority_str = row.get(column_mapping.get('priority', ''), '3').strip()
        assignee = row.get(column_mapping.get('assignee', ''), 'Unassigned').strip()
        points_str = row.get(column_mapping.get('story_points', ''), '0').strip()
        area_iteration = row.get(column_mapping.get('area_iteration', ''), '').strip()
        tags_str = row.get(column_mapping.get('tags', ''), '').strip()
        
        # Parse acceptance criteria (split by bullet, number, or semicolon)
        acceptance_criteria = self._parse_criteria(acceptance_criteria_str)
        
        # Parse priority
        try:
            priority = int(priority_str) if priority_str else 3
            priority = max(1, min(5, priority))  # Constrain to 1-5
        except ValueError:
            priority = 3
        
        # Parse story points
        try:
            story_points = int(points_str) if points_str else 0
        except ValueError:
            story_points = 0
        
        # Parse tags
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        
        return CSVStory(
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            priority=priority,
            state=state,
            assignee=assignee,
            story_points=story_points,
            area_iteration=area_iteration,
            tags=tags
        )
    
    def _parse_criteria(self, criteria_str: str) -> List[str]:
        """
        Parse acceptance criteria from string
        
        Handles various formats:
        - Newline separated
        - Bullet point (-, *, •)
        - Numbered (1., 2., etc.)
        - Semicolon separated
        
        Args:
            criteria_str: Acceptance criteria as string
            
        Returns:
            List of criteria
        """
        if not criteria_str:
            return []
        
        criteria = []
        lines = criteria_str.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Remove bullet points or numbering
            if line.startswith(('- ', '* ', '• ')):
                line = line[2:].strip()
            elif line and line[0].isdigit() and '.' in line[:3]:
                # Remove numbering like "1. " or "1) "
                line = line.split('.', 1)[1].strip() if '.' in line else line
                line = line.split(')', 1)[1].strip() if ')' in line else line
            
            # Split by semicolon if multiple criteria on one line
            if ';' in line and len(line) > 20:
                for subline in line.split(';'):
                    subline = subline.strip()
                    if subline:
                        criteria.append(subline)
            elif line:
                criteria.append(line)
        
        return criteria if criteria else ["No specific acceptance criteria provided"]
    
    def create_sample_csv(self, filename: str = "sample_stories.csv") -> str:
        """
        Create a sample CSV file with the correct format
        
        Args:
            filename: Output filename
            
        Returns:
            Path to created file
        """
        filepath = os.path.join(self.stories_folder, filename)
        
        sample_data = [
            {
                'Title': 'User Login Feature',
                'Description': 'Users should be able to login to the system with their credentials',
                'Acceptance Criteria': 'User can login with valid credentials; System shows error for invalid password; Session maintains login state',
                'Priority': '1',
                'State': 'In Progress',
                'Assignee': 'John Smith',
                'Story Points': '8',
                'Area': 'Authentication',
                'Tags': 'security,critical'
            },
            {
                'Title': 'Customer Profile Management',
                'Description': 'Users should be able to view and edit their profile information',
                'Acceptance Criteria': '- User can view profile information\n- User can edit profile fields\n- Changes are saved to database\n- Validation occurs for email field',
                'Priority': '2',
                'State': 'New',
                'Assignee': 'Jane Doe',
                'Story Points': '5',
                'Area': 'User Management',
                'Tags': 'feature,ui'
            },
            {
                'Title': 'Password Reset Functionality',
                'Description': 'Users should be able to reset their password if forgotten',
                'Acceptance Criteria': '1. User receives email with reset link\n2. Reset link is valid for 24 hours\n3. User can set new password\n4. Old password becomes invalid',
                'Priority': '2',
                'State': 'Ready',
                'Assignee': 'Mike Johnson',
                'Story Points': '5',
                'Area': 'Authentication',
                'Tags': 'security,feature'
            }
        ]
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = list(sample_data[0].keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(sample_data)
            
            logger.info(f"Sample CSV created: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error creating sample CSV: {str(e)}")
            return ""
    
    def validate_csv_file(self, filepath: str) -> Tuple[bool, List[str]]:
        """
        Validate a CSV file for required fields and format
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            with open(filepath, 'r', encoding=self.file_encoding) as csvfile:
                sample = csvfile.read(1024)
                csvfile.seek(0)
                delimiter = self._detect_delimiter(sample)
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                
                if not reader.fieldnames:
                    return False, ["No headers found in CSV"]
                
                # Check for required columns
                fieldnames_lower = {f.lower(): f for f in reader.fieldnames}
                
                found_required = False
                for field, aliases in self.REQUIRED_COLUMNS.items():
                    found = any(alias.lower() in fieldnames_lower for alias in aliases)
                    if found:
                        found_required = True
                        break
                
                if not found_required:
                    return False, ["No recognized title/summary column found"]
                
                # Check row count
                row_count = sum(1 for _ in reader)
                if row_count == 0:
                    return False, ["CSV file has no data rows"]
                
                return True, []
        
        except Exception as e:
            return False, [f"Error reading file: {str(e)}"]
    
    def list_csv_files(self) -> List[str]:
        """
        List all CSV files in the stories folder
        
        Returns:
            List of CSV filenames
        """
        try:
            csv_files = [f.name for f in Path(self.stories_folder).glob("*.csv")]
            return sorted(csv_files)
        except Exception as e:
            logger.error(f"Error listing CSV files: {str(e)}")
            return []
