# Sokolink Advisor

A comprehensive business compliance guidance system for small entrepreneurs in Kenya, powered by IBM Watsonx Orchestrate and integrated with WhatsApp Business API.

## 🎯 Overview

Sokolink Advisor is an AI-powered compliance assistant that helps small business owners in Kenya navigate the complex regulatory landscape. The system uses IBM Watsonx Orchestrate's agentic AI capabilities to provide personalized, step-by-step compliance roadmaps through WhatsApp conversations.

### Key Features

- **🤖 Multi-Agent AI System**: Four specialized AI agents working in orchestration
- **📱 WhatsApp Integration**: Natural language conversations via WhatsApp Business API
- **🏛️ Regulatory Intelligence**: Comprehensive knowledge of Kenyan business regulations
- **💰 Cost & Timeline Estimates**: Accurate cost and timeline predictions for compliance steps
- **🔒 Enterprise Security**: Secure API key authentication and data validation
- **📊 Monitoring & Metrics**: Prometheus metrics and structured logging

## 🏗️ System Architecture

### IBM Watsonx Orchestrate Integration

The system leverages IBM Watsonx Orchestrate's agentic AI capabilities through a sophisticated multi-agent workflow:

#### 1. **Main Orchestrator Agent** (`sokolink_main_agent`)
- **Role**: Primary interface that coordinates the entire compliance workflow
- **Model**: `watsonx/meta-llama/llama-3-2-90b-vision-instruct`
- **Function**: Routes user queries to the appropriate workflow and formats responses

#### 2. **Intent Classifier Agent** (`intent_classifier`)
- **Role**: Extracts business type and location from natural language input
- **Input**: User's business description (e.g., "I sell mahindi choma in Nairobi CBD")
- **Output**: Structured data with business type, location, products, and confidence score
- **Example Output**:
```json
{
  "business_type": "food_vendor",
  "location": "Nairobi County",
  "specific_area": "Nairobi CBD",
  "products": ["mahindi choma"],
  "confidence_score": 0.95
}
```

#### 3. **Regulatory Mapper Agent** (`regulatory_mapper_agent`)
- **Role**: Maps business type and location to relevant regulatory requirements
- **Input**: Classified business information
- **Output**: List of required permits, licenses, and regulatory requirements
- **Knowledge Base**: Comprehensive database of Kenyan business regulations

#### 4. **Data Synthesizer Agent** (`data_synthesizer`)
- **Role**: Converts regulatory requirements into actionable steps
- **Input**: Regulatory requirements list
- **Output**: Detailed, actionable steps with costs, timelines, and document requirements
- **Features**: Accurate cost estimation, realistic timelines, document lists

#### 5. **Personalized Planner Agent** (`personalized_planner_agent`)
- **Role**: Compiles all information into the final structured response
- **Input**: Detailed compliance steps
- **Output**: Complete compliance roadmap in standardized JSON format
- **Format**: Optimized for FastAPI backend consumption

### Workflow Orchestration

The system uses IBM Watsonx Orchestrate's flow builder to create a sequential workflow:

```
User Message → Intent Classifier → Regulatory Mapper → Data Synthesizer → Personalized Planner → Final Response
```

Each agent processes the output of the previous agent, creating a seamless pipeline that transforms natural language input into structured compliance guidance.

## 🚀 Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Python 3.13**: Latest Python version with enhanced performance
- **Pydantic**: Data validation and settings management
- **SQLAlchemy**: Database ORM with SQLite for development

### AI & Orchestration
- **IBM Watsonx Orchestrate**: Agentic AI orchestration platform
- **Meta Llama 3.2 90B Vision**: Large language model for natural language processing
- **Multi-Agent Architecture**: Specialized agents for different compliance tasks

### Communication
- **WhatsApp Business API**: Primary user interface
- **HTTPX**: Async HTTP client for API communications
- **Webhook Integration**: Secure webhook handling for WhatsApp messages

### Security & Monitoring
- **JWT Authentication**: Secure API access
- **Input Validation**: Comprehensive input sanitization
- **Prometheus Metrics**: Application monitoring and observability
- **Structured Logging**: JSON-formatted logs for better debugging

## 📁 Project Structure

```
sokolink/
├── app/
│   ├── agents/                    # IBM Watsonx agent configurations
│   │   ├── main_sokolink_agent.yaml
│   │   ├── intent_classifier_nobom.yaml
│   │   ├── regulatory_mapper_nobom.yaml
│   │   ├── data_synthesizer_nobom.yaml
│   │   └── personalized_planner_nobom.yaml
│   ├── flows/                     # Workflow orchestration
│   │   └── sokolink_workflow.py
│   ├── models/                    # Pydantic data models
│   │   ├── response_models.py
│   │   └── webhook_models.py
│   ├── routes/                    # API endpoints
│   │   ├── api.py
│   │   └── whatsapp.py
│   ├── services/                  # Business logic services
│   │   ├── watsonx_service.py     # IBM Watsonx integration
│   │   ├── whatsapp_service.py    # WhatsApp API integration
│   │   └── database_service.py    # Database operations
│   ├── utils/                     # Utility functions
│   │   ├── formatters.py
│   │   └── security.py
│   ├── config.py                  # Configuration management
│   └── main.py                    # FastAPI application
├── .env                          # Environment variables (create from env.example)
├── env.example                   # Environment template
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔧 Setup & Installation

### Prerequisites

1. **Python 3.13+**
2. **IBM Watsonx Orchestrate Account**
3. **WhatsApp Business API Account**
4. **Meta for Developers Account**

### 1. Clone the Repository

```bash
git clone <repository-url>
cd sokolink
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file from the template:

```bash
cp env.example .env
```

Configure the following environment variables in `.env`:

```env
# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_webhook_verify_token_here

# IBM Watsonx Orchestrate Configuration
WATSONX_API_KEY=your_watsonx_api_key_here
WATSONX_PROJECT_ID=your_project_id_here

# Security Configuration
SECRET_KEY=your_secure_secret_key_here_minimum_32_characters
```

### 5. IBM Watsonx Orchestrate Setup

1. **Create a Project**: Set up a new project in IBM Watsonx Orchestrate
2. **Deploy Agents**: Upload the agent configurations from `app/agents/`
3. **Create Workflow**: Deploy the workflow from `app/flows/sokolink_workflow.py`
4. **Get Credentials**: Obtain your API key and project ID

### 6. WhatsApp Business API Setup

1. **Create App**: Set up a WhatsApp Business app in Meta for Developers
2. **Get Credentials**: Obtain access token and phone number ID
3. **Configure Webhook**: Set webhook URL to `https://yourdomain.com/webhook/whatsapp`
4. **Set Verify Token**: Use the same token in your `.env` file

### 7. Run the Application

```bash
# Development mode
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🔌 API Endpoints

### Core Endpoints

- **`GET /`**: Application information and status
- **`GET /health`**: Health check endpoint
- **`GET /metrics`**: Prometheus metrics (if enabled)

### WhatsApp Integration

- **`GET /webhook/whatsapp`**: Webhook verification
- **`POST /webhook/whatsapp`**: Receive WhatsApp messages

### API Routes

- **`POST /api/compliance/analyze`**: Direct compliance analysis
- **`GET /api/sessions/{session_id}`**: Retrieve session data
- **`POST /api/sessions`**: Create new session

## 🤖 How the AI System Works

### 1. User Input Processing

When a user sends a message like "I sell mahindi choma in Nairobi CBD", the system:

1. **Validates Input**: Sanitizes and validates the user message
2. **Creates Session**: Establishes a session context with user information
3. **Routes to Workflow**: Sends the message to the Watsonx Orchestrate workflow

### 2. Multi-Agent Processing

The workflow processes the message through four specialized agents:

#### Intent Classifier
- Analyzes the message to extract business type and location
- Uses natural language understanding to identify key information
- Returns structured data with confidence scores

#### Regulatory Mapper
- Queries a knowledge base of Kenyan business regulations
- Maps business type and location to specific requirements
- Identifies all necessary permits, licenses, and registrations

#### Data Synthesizer
- Converts regulatory requirements into actionable steps
- Provides accurate cost estimates and timelines
- Lists required documents and procedures

#### Personalized Planner
- Compiles all information into a comprehensive roadmap
- Formats the response for optimal user experience
- Ensures consistency and completeness

### 3. Response Generation

The final response includes:

- **Compliance Steps**: Numbered list of required actions
- **Cost Estimates**: Total and per-step cost breakdown
- **Timeline**: Realistic processing times
- **Document Requirements**: List of needed documents
- **Authority Information**: Contact details for relevant offices

## 📊 Monitoring & Observability

### Prometheus Metrics

The system exposes metrics for:
- HTTP request counts and durations
- API endpoint performance
- Error rates and types
- Business logic metrics

### Structured Logging

All logs are in JSON format with:
- Request/response tracking
- Error details and stack traces
- Performance metrics
- Business logic events

### Health Checks

- **Application Health**: Basic application status
- **External Services**: WhatsApp and Watsonx API connectivity
- **Database Health**: Database connection status

## 🔒 Security Features

### Input Validation
- Comprehensive input sanitization
- Business input validation
- Phone number format validation
- SQL injection prevention

### Authentication
- JWT token-based authentication
- API key validation for external services
- Webhook signature verification

### Data Protection
- Secure credential storage
- Environment variable configuration
- No hardcoded sensitive data

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**: Ensure all sensitive data is in environment variables
2. **Database**: Consider PostgreSQL for production
3. **Load Balancing**: Use multiple workers for high availability
4. **SSL/TLS**: Enable HTTPS for webhook endpoints
5. **Monitoring**: Set up Prometheus and Grafana for monitoring

### Docker Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY .env .

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the agent configurations in `app/agents/`

## 🔮 Future Enhancements

- **Multi-language Support**: Support for Swahili and other local languages
- **Voice Integration**: Voice message processing
- **Document Upload**: Handle document verification
- **Payment Integration**: Direct payment processing for fees
- **Mobile App**: Native mobile application
- **Analytics Dashboard**: Business intelligence and insights

---

**Sokolink Advisor** - Empowering Kenyan entrepreneurs with AI-driven compliance guidance.