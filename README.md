# AI Chatbot System - Milestone 1

A production-grade, multi-tenant AI chatbot system with RAG (Retrieval-Augmented Generation), multi-agent architecture, and comprehensive analytics. Built with LangChain, LangGraph, FastAPI, and modern Python technologies.

## 🚀 Features

### Core Features (Milestone 1)
- **Multi-Agent Architecture**: Specialized agents for different tasks (RAG Q&A, API execution, form generation, analytics)
- **RAG System**: Advanced document processing with vector storage (FAISS/Chroma) supporting PDF, DOCX, TXT, CSV, XLSX
- **Dynamic API Connectivity**: Integration with third-party services with authentication, rate limiting, and error handling
- **Multi-Tenant Support**: Complete tenant isolation with auto-scaling capabilities
- **Real-time Chat**: WebSocket-based chat with conversation management
- **AI Form Generation**: Dynamic form creation based on natural language requirements
- **Analytics Integration**: Apache Superset integration for customer behavior analytics
- **LangSmith Monitoring**: Complete observability and monitoring for AI operations

### Technical Stack
- **Backend**: FastAPI, Python 3.11+
- **AI/ML**: LangChain, LangGraph, OpenAI GPT, Sentence Transformers
- **Database**: PostgreSQL, Redis
- **Vector Storage**: FAISS, ChromaDB
- **Task Queue**: Celery
- **Analytics**: Apache Superset
- **Monitoring**: LangSmith, Prometheus
- **Deployment**: Docker, AWS

## 📋 Prerequisites

- Python 3.10+
- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+
- OpenAI API Key (or other LLM provider)

## 🛠 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ai-chatbot-system
```

### 2. Environment Setup
```bash
# Copy environment template
cp env.example .env

# Edit .env with your configurations
# Required: OPENAI_API_KEY, DATABASE_URL, REDIS_URL, SECRET_KEY
```

### 3. Docker Deployment (Recommended)
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app
```

### 4. Manual Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/chatbot_db"
export REDIS_URL="redis://localhost:6379/0"
export OPENAI_API_KEY="your-openai-api-key"
export SECRET_KEY="your-secret-key"

# Run the application
python -m app.main
```

## 🏗 Architecture

### Multi-Agent System
The system uses LangGraph to orchestrate multiple specialized agents:

1. **RAG Agent** (`rag_agent.py`): Document-based Q&A with source citations
2. **API Agent** (`api_agent.py`): Third-party API integration and execution
3. **Form Agent** (`form_agent.py`): Dynamic form generation
4. **Analytics Agent** (`analytics_agent.py`): Data analysis and reporting

### Agent Controller
The `AgentController` uses LangGraph workflows to:
- Analyze user intent
- Route requests to appropriate agents
- Handle fallbacks and error recovery
- Manage conversation flow

### RAG System Components
- **Document Processor**: Handles PDF, DOCX, TXT, CSV, XLSX files
- **Vector Store**: FAISS or ChromaDB for similarity search
- **Document Retriever**: Advanced retrieval with re-ranking and filtering

## 📚 API Documentation

### Authentication
```bash
# Register new user
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "username": "user123",
  "password": "secure_password",
  "tenant_domain": "company"
}

# Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

### Chat
```bash
# Send message
POST /api/v1/chat/message
{
  "content": "What is the main topic of the uploaded document?",
  "conversation_id": "optional-conversation-id"
}

# Get conversations
GET /api/v1/chat/conversations

# Get conversation details
GET /api/v1/chat/conversations/{conversation_id}
```

### Document Management
```bash
# Upload document
POST /api/v1/documents/upload
# Form data with file

# List documents
GET /api/v1/documents/
```

### Agents
```bash
# List available agents
GET /api/v1/agents/
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `REDIS_URL` | Redis connection URL | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `VECTOR_DB_TYPE` | Vector database type (faiss/chroma) | faiss |
| `CHUNK_SIZE` | Document chunk size | 1000 |
| `CHUNK_OVERLAP` | Document chunk overlap | 200 |
| `LANGCHAIN_API_KEY` | LangSmith API key | Optional |

### Multi-Tenancy
The system supports automatic tenant isolation:
- Users are automatically assigned to tenants based on domain
- All data (conversations, documents, agents) are tenant-isolated
- Vector databases maintain tenant separation

## 🚀 Deployment

### AWS Deployment
```bash
# Build and push Docker image
docker build -t ai-chatbot-system .
docker tag ai-chatbot-system:latest your-registry/ai-chatbot-system:latest
docker push your-registry/ai-chatbot-system:latest

# Deploy using your preferred method (ECS, EKS, EC2)
```

### Environment-Specific Configurations
- **Development**: Use `docker-compose.yml`
- **Staging**: Use `docker-compose.staging.yml`
- **Production**: Use orchestration tools (Kubernetes, ECS)

## 📊 Monitoring & Analytics

### LangSmith Integration
The system includes comprehensive monitoring:
- Agent performance tracking
- Conversation analytics
- Error monitoring and alerting
- Token usage tracking

### Apache Superset
Integrated analytics dashboard for:
- User behavior analysis
- Conversation patterns
- Document usage statistics
- System performance metrics

Access Superset at: `http://localhost:8088` (default: admin/admin)

## 🧪 Testing

```bash
# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=app

# Run specific test categories
python -m pytest -m unit
python -m pytest -m integration
```

## 🔒 Security Features

- JWT-based authentication with refresh tokens
- Multi-tenant data isolation
- Rate limiting on API endpoints
- Input validation and sanitization
- Secure file upload handling
- Environment-based configuration

## 🎯 Usage Examples

### Document Q&A
```python
# Upload a document via API, then ask questions
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "What are the key findings in the research paper?"}'
```

### API Integration
```python
# Execute API calls through natural language
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Make a GET request to the users API endpoint"}'
```

### Form Generation
```python
# Generate forms with AI
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Create a customer feedback form with rating and comments"}'
```

## 🛣 Roadmap

### Milestone 2 (Planned)
- Advanced multi-modal support (images, audio)
- Real-time collaboration features
- Advanced workflow automation
- Enhanced security and compliance features
- Mobile SDK

### Milestone 3 (Planned)
- Voice interface integration
- Advanced AI model fine-tuning
- Marketplace for custom agents
- Enterprise SSO integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in `/docs`
- Review the API documentation at `/docs` (when running in debug mode)

## 🔧 Development

### Project Structure
```
ai-chatbot-system/
├── app/
│   ├── agents/          # Multi-agent system
│   ├── api/            # FastAPI routes
│   ├── database/       # Database configuration
│   ├── models/         # SQLAlchemy models
│   ├── rag/           # RAG system components
│   ├── config.py      # Configuration management
│   └── main.py        # FastAPI application
├── tests/             # Test suite
├── data/             # Data storage
├── docker-compose.yml # Docker services
├── Dockerfile        # Container definition
└── requirements.txt  # Python dependencies
```

### Adding New Agents
1. Create new agent class inheriting from `BaseAgent`
2. Implement `can_handle()` and `process_message()` methods
3. Register in `AgentController`
4. Add database configuration

### Extending RAG System
1. Add new document processors in `rag/document_processor.py`
2. Extend vector store implementations
3. Customize retrieval strategies in `rag/retriever.py`

---

**Built with ❤️ for the future of AI-powered customer interactions** 