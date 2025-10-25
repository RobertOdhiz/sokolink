# sokolink-setup.ps1
# PowerShell script to create Sokolink Advisor project structure and files

# Create project directory
$ProjectRoot = "sokolink-advisor"
New-Item -ItemType Directory -Path $ProjectRoot -Force
Set-Location $ProjectRoot

Write-Host "Creating Sokolink Advisor project structure..." -ForegroundColor Green

# Create subdirectories
$directories = @("agents", "flows", "utils", "services", "models", "routes")
foreach ($dir in $directories) {
    New-Item -ItemType Directory -Path $dir -Force
    Write-Host "Created directory: $dir" -ForegroundColor Yellow
}

# 1. Create .env file
$envContent = @"
# Application Configuration
APP_NAME=Sokolink Advisor
APP_VERSION=1.0.0
DEBUG=True
ENVIRONMENT=production

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database Configuration
DATABASE_URL=sqlite:///./sokolink_advisor.db

# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN=test_whatsapp_access_token_123456789
WHATSAPP_PHONE_NUMBER_ID=test_phone_number_id_123456789
WHATSAPP_WEBHOOK_VERIFY_TOKEN=test_webhook_verify_token_123456789
WHATSAPP_API_VERSION=v18.0

# IBM Watsonx Orchestrate Configuration - UPDATED FOR ADK
WATSONX_API_KEY=your_actual_ibm_cloud_api_key_here
WATSONX_URL=https://us-south.watson-orchestrate.cloud.ibm.com
WATSONX_PROJECT_ID=your_actual_project_id_here

# ADK Specific - NEW
IBM_API_KEY=`${WATSONX_API_KEY}
IBM_URL=`${WATSONX_URL}
IBM_PROJECT_ID=`${WATSONX_PROJECT_ID}

# Security Configuration
SECRET_KEY=this_is_a_test_secret_key_that_is_long_enough_for_validation_123456789
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_BURST=20

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
ENABLE_METRICS=True
METRICS_PORT=9090
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Host "Created .env file" -ForegroundColor Green

# 2. Create requirements.txt
$requirementsContent = @"
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
httpx==0.25.2
python-dotenv==1.0.0
pydantic==2.5.0
sqlalchemy==2.0.23
aiosqlite==0.19.0
ibm-watsonx-orchestrate==0.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
redis==5.0.1
"@

$requirementsContent | Out-File -FilePath "requirements.txt" -Encoding UTF8
Write-Host "Created requirements.txt" -ForegroundColor Green

# 3. Create Agent Files

# intent_classifier.yaml
$intentClassifierContent = @"
spec_version: v1
kind: native
name: intent_classifier
description: Extract business type and location from user message
instructions: |
  Analyze the user's message and automatically identify the business type and location.
  
  Return JSON:
  {
    "business_type": "food_vendor",
    "location": "Nairobi County", 
    "specific_area": "Nairobi CBD",
    "products": ["mahindi choma"],
    "confidence_score": 0.95
  }
  
  DO NOT ask questions. Extract from the message automatically.
llm: watsonx/meta-llama/llama-3-2-90b-vision-instruct
style: default
collaborators: []
tools: []
"@

$intentClassifierContent | Out-File -FilePath "agents\intent_classifier.yaml" -Encoding UTF8
Write-Host "Created agents\intent_classifier.yaml" -ForegroundColor Green

# regulatory_mapper_agent.yaml
$regulatoryMapperContent = @"
spec_version: v1
kind: native
name: regulatory_mapper_agent
description: Query knowledge base and map to relevant regulations
instructions: |
  Based on business type and location, determine ALL required permits and licenses.
  
  Return JSON:
  {
    "requirements": [
      {
        "requirement_id": "county_business_permit",
        "name": "Single Business Permit",
        "authority": "Nairobi County Government",
        "category": "business_license"
      }
    ]
  }
llm: watsonx/meta-llama/llama-3-2-90b-vision-instruct
style: default
collaborators: []
tools: []
"@

$regulatoryMapperContent | Out-File -FilePath "agents\regulatory_mapper_agent.yaml" -Encoding UTF8
Write-Host "Created agents\regulatory_mapper_agent.yaml" -ForegroundColor Green

# data_synthesizer.yaml
$dataSynthesizerContent = @"
spec_version: v1
kind: native
name: data_synthesizer
description: Create legal requirements into actionable steps
instructions: |
  Convert regulatory requirements into detailed, actionable steps with accurate costs and timelines.
  
  Return JSON:
  {
    "detailed_steps": [
      {
        "requirement_id": "county_business_permit",
        "step_number": 1,
        "title": "Single Business Permit",
        "description": "Apply at Nairobi County Government offices or online portal",
        "actionable_steps": ["Visit county offices", "Complete form", "Submit documents", "Pay fee"],
        "documents_required": ["ID copy", "Passport photo", "Business location sketch"],
        "authority_office": "Nairobi County Business Permits Office",
        "processing_time_days": 7,
        "official_cost": 5000
      }
    ]
  }
llm: watsonx/meta-llama/llama-3-2-90b-vision-instruct
style: default
collaborators: []
tools: []
"@

$dataSynthesizerContent | Out-File -FilePath "agents\data_synthesizer.yaml" -Encoding UTF8
Write-Host "Created agents\data_synthesizer.yaml" -ForegroundColor Green

# personalized_planner_agent.yaml
$personalizedPlannerContent = @"
spec_version: v1
kind: native
name: personalized_planner_agent
description: Create final structured response
instructions: |
  Compile all steps into the final JSON format. Use the provided session_id or "default-session".
  
  Return EXACTLY this JSON format without any additional text:
  {
    "session_id": "{{session_id}}",
    "compliance_steps": [
      {
        "step_number": 1,
        "title": "Single Business Permit",
        "description": "Apply at Nairobi County Government offices",
        "cost": 5000,
        "timeline_days": 7,
        "authority": "Nairobi County Government",
        "documents_required": ["ID copy", "Passport photo"],
        "requirement_id": "county_business_permit"
      }
    ],
    "total_estimated_cost": 7000,
    "total_timeline_days": 14,
    "business_type": "{{business_type}}",
    "location": "{{location}}"
  }
  
  DO NOT ask any questions. Use the provided data only.
llm: watsonx/meta-llama/llama-3-2-90b-vision-instruct
style: default
collaborators: []
tools: []
"@

$personalizedPlannerContent | Out-File -FilePath "agents\personalized_planner_agent.yaml" -Encoding UTF8
Write-Host "Created agents\personalized_planner_agent.yaml" -ForegroundColor Green

# 4. Create Workflow File
$workflowContent = @"
spec_version: v1
kind: flow
name: sokolink_compliance_workflow
description: Complete compliance guidance for small businesses
parameters:
  user_message:
    type: string
    description: "User's business query"
  session_id:
    type: string
    description: "Session identifier"

steps:
  - name: classify_business
    agent: intent_classifier
    input:
      message: "{{user_message}}"
  
  - name: map_regulations
    agent: regulatory_mapper_agent
    input:
      business_type: "{{classify_business.output.business_type}}"
      location: "{{classify_business.output.location}}"
  
  - name: synthesize_steps
    agent: data_synthesizer
    input:
      regulations: "{{map_regulations.output.requirements}}"
  
  - name: generate_final_output
    agent: personalized_planner_agent
    input:
      detailed_steps: "{{synthesize_steps.output.detailed_steps}}"
      session_id: "{{session_id}}"
      business_type: "{{classify_business.output.business_type}}"
      location: "{{classify_business.output.location}}"
"@

$workflowContent | Out-File -FilePath "flows\sokolink_workflow.yaml" -Encoding UTF8
Write-Host "Created flows\sokolink_workflow.yaml" -ForegroundColor Green

# 5. Create ADK setup script
$adkScriptContent = @"
# adk-setup.ps1
# Script to import agents and workflow using ADK

Write-Host "Setting up IBM Watsonx Orchestrate ADK..." -ForegroundColor Green

# Configure environment
orchestrate env add -n sokolink -u https://us-south.watson-orchestrate.cloud.ibm.com --type ibm_iam --activate

Write-Host "Importing agents..." -ForegroundColor Yellow
orchestrate agents import -f agents/intent_classifier.yaml
orchestrate agents import -f agents/regulatory_mapper_agent.yaml
orchestrate agents import -f agents/data_synthesizer.yaml
orchestrate agents import -f agents/personalized_planner_agent.yaml

Write-Host "Importing workflow..." -ForegroundColor Yellow
orchestrate flows import -f flows/sokolink_workflow.yaml

Write-Host "Setup completed! Check your IBM Watsonx Orchestrate dashboard." -ForegroundColor Green
"@

$adkScriptContent | Out-File -FilePath "adk-setup.ps1" -Encoding UTF8
Write-Host "Created adk-setup.ps1" -ForegroundColor Green

# 6. Create main.py starter
$mainPyContent = @"
from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title=os.getenv("APP_NAME"), version=os.getenv("APP_VERSION"))

@app.get("/")
async def root():
    return {"message": "Sokolink Advisor API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sokolink-advisor"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )
"@

$mainPyContent | Out-File -FilePath "main.py" -Encoding UTF8
Write-Host "Created main.py" -ForegroundColor Green

# 7. Create README.md
$readmeContent = @"
# Sokolink Advisor

A WhatsApp-based AI assistant for business compliance guidance in Kenya.

## Project Structure
- `agents/`: Contains AI agents for business classification, regulatory mapping, and compliance guidance.
- `flows/`: Defines the workflow orchestration using IBM Watsonx Orchestrate.
- `utils/`: Utility functions for formatting and validation.
- `services/`: Core services for database management, API endpoints, and external integrations.
- `models/`: Pydantic models for request and response data validation.
- `routes/`: FastAPI route definitions.
- `main.py`: FastAPI application entry point.
- `requirements.txt`: Python package dependencies.
- `.env`: Environment variables configuration.
- `adk-setup.ps1`: Script to import agents and workflow using ADK.
- `README.md`: Project documentation.
"@

$readmeContent | Out-File -FilePath "README.md" -Encoding UTF8
Write-Host "Created README.md" -ForegroundColor Green

Write-Host "`nProject setup completed!`n" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update .env file with your actual IBM credentials" -ForegroundColor White
Write-Host "2. Run: .\adk-setup.ps1 to import agents and workflow" -ForegroundColor White
Write-Host "3. Run: python main.py to start the FastAPI server" -ForegroundColor White
Write-Host "`nProject created in: $((Get-Location).Path)" -ForegroundColor Cyan