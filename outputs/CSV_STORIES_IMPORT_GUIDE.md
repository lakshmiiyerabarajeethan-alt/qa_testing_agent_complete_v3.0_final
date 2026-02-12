# CSV Stories Import Guide

**Version**: v3.0+  
**Status**: ✅ Production Ready  
**Purpose**: Import user stories from any system via CSV format

---

## 🎯 Overview

Instead of connecting directly to Azure DevOps, the system now reads user stories from **CSV files** placed in a folder. This makes the system **completely platform-agnostic** - you can:

- ✅ Export stories from **Azure DevOps** to CSV
- ✅ Export stories from **Jira** to CSV
- ✅ Export stories from **Linear** to CSV
- ✅ Export stories from **GitHub Issues** to CSV
- ✅ Manually create CSV files
- ✅ Use any custom format by mapping to our CSV columns

---

## 📋 CSV Format Specification

### Required Columns

| Column Name | Alternative Names | Description | Example |
|-------------|-------------------|-------------|---------|
| **Title** | Summary, Story Title, Feature Title | The user story title/summary | "User Login Feature" |
| **Description** | Story Description, Details, Narrative | Detailed description of the story | "Users should be able to login..." |
| **Acceptance Criteria** | Acceptance_Criteria, Criteria, Acceptance | List of conditions that must be met | "User can login with valid credentials; System shows error for invalid password" |
| **State** | Status, Story Status, Work Item Type | Current state of the story | "New", "In Progress", "Done" |

### Optional Columns

| Column Name | Alternative Names | Description | Default | Example |
|-------------|-------------------|-------------|---------|---------|
| **Priority** | Priority Level | Priority level (1-5, where 1 is highest) | 3 (Medium) | 1, 2, 3, 4, 5 |
| **Assignee** | Assigned To, Owner | Person assigned to work on story | "Unassigned" | "John Smith" |
| **Story Points** | Points, Estimation | Story estimation in points | 0 | 1, 2, 3, 5, 8, 13 |
| **Area** | Iteration, Area Path, Iteration Path, Sprint | Feature area or sprint name | "" | "Authentication", "Sprint 1" |
| **Tags** | Labels, Keywords | Comma-separated tags/labels | "" | "security,critical,ui" |

---

## 📝 CSV File Format Examples

### Example 1: Simple Format (Comma-Separated)

```csv
Title,Description,Acceptance Criteria,Priority,State,Assignee,Story Points,Area,Tags
User Login Feature,Users should be able to login to the system,User can login with valid credentials; System shows error for invalid password; Session maintains login state,1,In Progress,John Smith,8,Authentication,security;critical
Customer Profile Management,Users should be able to manage their profile,User can view profile; User can edit profile; Changes are saved,2,New,Jane Doe,5,User Management,feature;ui
Password Reset,Users should be able to reset their password,User receives reset email; Link valid for 24 hours; New password works,2,Done,Mike Johnson,5,Authentication,security
```

### Example 2: With Line Breaks (Multi-Line Acceptance Criteria)

```csv
Title,Description,"Acceptance Criteria",Priority,State,Assignee,Story Points
"User Dashboard","Display user dashboard with analytics","- User can view dashboard
- Dashboard loads in under 2 seconds
- Data refreshes every 5 minutes",1,In Progress,Alice Brown,8
```

### Example 3: Semicolon-Separated (if your data contains commas)

```csv
Title;Description;Acceptance Criteria;Priority;State;Assignee
User Login Feature;Users login with username and password;User can login with valid credentials; System shows error for invalid password,1,In Progress,John Smith
```

---

## 🚀 How to Export Stories from Different Platforms

### From Azure DevOps

**Option 1: Using Azure DevOps Web Interface**
1. Go to Azure DevOps Boards
2. Select your project
3. Click "Export to CSV" (if available)
4. Choose stories to export
5. Save file to `./stories` folder

**Option 2: Using Power BI or Excel**
1. Connect to Azure DevOps data
2. Export work items query
3. Map columns to our format
4. Save as CSV

**Option 3: Using Azure DevOps CLI**
```bash
az boards work-item list --project "ProjectName" --org "https://dev.azure.com/OrgName" --format csv > stories.csv
```

### From Jira

**Option 1: Using Jira Search & Export**
1. Create a JQL search for your stories
2. Export as CSV
3. Map columns:
   - Summary → Title
   - Description → Description
   - Acceptance Criteria → Acceptance Criteria
   - Priority → Priority
   - Status → State

**Option 2: Using Jira API**
```bash
curl -u email@example.com:api_token https://your-instance.atlassian.net/rest/api/3/search > jira_export.csv
```

### From Linear

**Option 1: Using Linear Export**
1. Go to Linear workspace settings
2. Export issues/stories
3. Map columns to our format
4. Save as CSV

### From GitHub Issues

**Option 1: Using GitHub CLI**
```bash
gh issue list --repo owner/repo --limit 100 --format csv > github_stories.csv
```

### Manual Creation

Create a new CSV file with the required columns:
```bash
# Create stories folder
mkdir stories

# Create your CSV file
cat > stories/my_stories.csv << EOF
Title,Description,Acceptance Criteria,Priority,State,Assignee,Story Points,Area,Tags
Feature Name,Feature description,Criteria 1; Criteria 2,1,New,Your Name,5,Feature Area,tag1;tag2
EOF
```

---

## 🔄 Column Mapping

The CSV reader is **flexible** with column names. It matches columns case-insensitively:

### Title Column Variants
- `Title`
- `Summary`
- `Story Title`
- `Feature Title`
- `Name`

### Description Column Variants
- `Description`
- `Story Description`
- `Details`
- `Narrative`

### Acceptance Criteria Variants
- `Acceptance Criteria`
- `Acceptance_Criteria`
- `Criteria`
- `Acceptance`

### State Column Variants
- `State`
- `Status`
- `Story Status`
- `Work Item Type`

### Priority Column Variants
- `Priority`
- `Priority Level`
- `Severity`

---

## 📂 Folder Structure

```
your_project/
├── qa_testing_agent/
│   ├── stories/
│   │   ├── sprint_1_stories.csv
│   │   ├── features_list.csv
│   │   └── user_stories.csv
│   ├── test_inputs/
│   └── reports/
```

**Default folder**: `./stories`

**Change folder in code**:
```bash
python main.py
# When prompted:
# Select: Option 1 (CSV Stories)
# Enter: /path/to/your/csv/folder
```

---

## 💡 Best Practices

### 1. **Column Names**
- Use standard English names
- Consistency across all CSV files
- Keep names simple (avoid special characters)

### 2. **Data Quality**
- Ensure all required columns present
- Validate acceptance criteria format
- Use consistent priority levels (1-5)
- Use consistent state/status values

### 3. **File Naming**
- Use descriptive names: `sprint1_stories.csv`, `product_features.csv`
- Avoid spaces (use underscores instead): `my_stories.csv` ✅ vs `my stories.csv` ❌
- One file per sprint or feature area

### 4. **Encoding**
- Use UTF-8 encoding
- Include BOM if needed: `UTF-8 BOM`
- Test with special characters

### 5. **Acceptance Criteria Format**
Use any of these formats (they're all recognized):

**Semicolon-Separated:**
```
User can login with valid credentials; System shows error; Session maintains state
```

**Bullet Points:**
```
- User can login with valid credentials
- System shows error for invalid password
- Session maintains login state
```

**Numbered:**
```
1. User can login with valid credentials
2. System shows error for invalid password
3. Session maintains login state
```

**New Lines (in quoted field):**
```
"- User can login with valid credentials
- System shows error for invalid password
- Session maintains login state"
```

---

## ✅ CSV Validation

The system automatically validates CSV files:

### Checks Performed
✅ File exists and is readable
✅ Contains required columns
✅ Has data rows
✅ Proper CSV formatting
✅ Character encoding valid

### Validation Errors
```
❌ No CSV files found in folder
❌ No headers found in file
❌ No recognized title column
❌ CSV file has no data rows
❌ Error reading file (encoding issue)
```

---

## 🎯 Example Workflow

### Step 1: Export Stories
```
Azure DevOps/Jira/etc. → Export to CSV → Save to ./stories folder
```

### Step 2: Run System
```bash
python main.py
# Select: Option 1 (CSV Stories)
# Enter: ./stories (or your custom folder)
```

### Step 3: System Processes
```
✓ Reads all CSV files from folder
✓ Parses stories and validates format
✓ Generates test cases from each story
✓ Saves to Excel
✓ Presents approval workflow
✓ Continues with normal pipeline
```

### Step 4: Results
```
HTML Report with test results
```

---

## 📊 Sample CSV File

Complete example with all fields:

```csv
Title,Description,Acceptance Criteria,Priority,State,Assignee,Story Points,Area,Tags
"User Authentication","Implement secure user login system","- Users can login with email and password
- System validates credentials against database
- Failed login shows error message
- Successful login creates session
- Session timeout after 30 minutes of inactivity",1,In Progress,John Smith,8,Authentication,security;critical;backend
"Customer Dashboard","Display personalized customer dashboard","User can view dashboard; Dashboard shows recent orders; Dashboard shows account balance; Page loads in under 2 seconds",2,New,Jane Doe,5,UI;Dashboard,feature;ui;customer-facing
"Password Reset Feature","Allow users to reset forgotten passwords","- User receives reset email with link
- Reset link valid for 24 hours only
- Link redirects to password reset form
- User can set new password
- Email confirmation sent after reset
- Old password becomes invalid",2,Done,Mike Johnson,5,Authentication,security;email
"Export Reports","Enable users to export reports as PDF","Accepts multiple formats; Generates PDF; Email delivery option; Scheduled exports supported",3,Not Started,Sarah Lee,8,Reporting,feature;export;pdf
"Mobile Optimization","Optimize UI for mobile devices","Works on iOS Safari; Works on Android Chrome; Touch-friendly buttons; Responsive layout",2,In Progress,Tom Brown,13,UI,mobile;responsive;ux
```

---

## 🔧 Advanced: Custom Column Mapping

If your CSV has non-standard column names, the system tries to match them:

### Example Non-Standard CSV
```csv
Feature Name,Story Description,Requirements,Severity,Current Status,Owned By
Login System,Users need to login securely,Validate credentials,1,In Development,John
```

**Mapping (Automatic)**
```
Feature Name → Title
Story Description → Description
Requirements → Acceptance Criteria
Severity → Priority
Current Status → State
Owned By → Assignee
```

If automatic mapping fails, edit your CSV to use standard column names or rename columns.

---

## 📚 Examples by Platform

### Example: Azure DevOps Export

Create a `.csv` with this structure:
```csv
Title,Description,Acceptance Criteria,Priority,State,Assignee,Story Points
Login Feature,Users can login securely,"Valid credentials work; Invalid credentials rejected; Session created",1,In Progress,John,8
```

### Example: Jira Export

Map Jira columns:
```
Jira Column         → Our Column
Summary             → Title
Description         → Description
Acceptance Criteria → Acceptance Criteria
Priority            → Priority
Status              → State
Assignee            → Assignee
Story Point Estimate → Story Points
Epic Link           → Area
Labels              → Tags
```

### Example: Linear Export

Map Linear columns:
```
Linear Column       → Our Column
Title               → Title
Description         → Description
State               → State
Priority            → Priority
Assignee            → Assignee
Issue Labels        → Tags
```

---

## 🚀 Getting Started

### Quickest Path (5 minutes)

1. **Create Sample CSV**
   ```bash
   python main.py
   # Select: Option 3 (Create Sample CSV)
   # File created: ./stories/sample_stories.csv
   ```

2. **Edit Sample CSV**
   - Open `./stories/sample_stories.csv`
   - Modify with your stories
   - Save file

3. **Run System**
   ```bash
   python main.py
   # Select: Option 1 (CSV Stories)
   # Press Enter (default ./stories)
   ```

4. **Make Approval Decision**
   - System will prompt for approval (1-5)
   - Choose option 1 for fastest execution

5. **Review Report**
   - HTML report generated automatically

---

## ✅ Verification Checklist

Before running the system, verify:

- [ ] CSV files in correct folder
- [ ] All required columns present
- [ ] Valid UTF-8 encoding
- [ ] No empty rows at beginning
- [ ] Column headers in first row
- [ ] At least 1 data row
- [ ] No special characters in file names
- [ ] File extension is `.csv`

---

## 🎓 Common Issues & Solutions

### "No CSV files found"
- Check folder path is correct
- Ensure files have `.csv` extension
- Verify folder permissions

### "No recognized column"
- Check column names match specification
- Use case-insensitive names
- Remove extra spaces from column names

### "Encoding error"
- Save file as UTF-8
- Avoid special characters in headers
- Use consistent delimiter (comma or semicolon)

### "Invalid CSV format"
- Ensure proper quoting for multi-line fields
- Use quote character for fields with commas
- Validate with CSV validator tool

---

## 📞 Support

For CSV format issues:
1. Check this guide first
2. Review example CSV files
3. Validate using CSV validator
4. Check file encoding (must be UTF-8)

---

## 🔗 Related Documentation

- **NAVIGATION_GUIDE.md** - How to find documentation
- **README_COMPLETE_SYSTEM.md** - System overview
- **SETUP_AND_DEPLOYMENT.md** - Installation
- **MANUAL_APPROVAL_WORKFLOW.md** - Approval options

---

**CSV Stories Import: Platform-Agnostic Story Management** ✅

Import stories from **any system** using standard CSV format!
