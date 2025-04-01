# BigData-Hackathon - Mass Legal Research Assistant

A comprehensive legal research system powered by Massachusetts Reports (1768-2017), combining historical case law with current web information using Retrieval-Augmented Generation (RAG) and Machine Conversation Protocol (MCP).

## 🚀 Features

- **Historical Case Law Analysis**: Query Massachusetts Reports spanning from 1768 to 2017
- **Current Legal Commentary**: Search web sources for recent legal interpretations
- **MCP Protocol Support**: Use the Machine Conversation Protocol for AI assistants
- **Comprehensive Research Reports**: Generate 20-30 page legal research reports
- **Metadata Filtering**: Filter cases by year range
- **Web Interface**: User-friendly Streamlit interface for research

## 📋 System Architecture

The system consists of three main components:

1. **Legal RAG Agent**: Queries the Pinecone vector database containing Massachusetts Reports
2. **Web Search Agent**: Searches the web for current legal information and commentary
3. **Synthesis Agent**: Combines historical and current information into a comprehensive report

These components are accessible through:
- **FastAPI Backend**: For direct API access
- **MCP Server**: For AI assistant integration
- **Streamlit Frontend**: For user interaction

### Architecture Diagram

![image](https://github.com/user-attachments/assets/a75d3446-5b9c-4a6f-9d40-8c8db1474354)


## 🌐 Live Links

- **Frontend** (Streamlit Web Interface): [http://67.205.171.239:8501/](http://67.205.171.239:8501/)
- **Backend** (FastAPI API Server): [http://67.205.171.239:8000/](http://67.205.171.239:8000/)

## 🛠️ Installation

### Prerequisites

- Docker and Docker Compose
- API keys for:
  - OpenAI
  - Pinecone
  - Tavily (for web search)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/DAMG7245/BigData-Hackathon.git
cd mass-legal-research
```

2. Run the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

3. Edit the `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=mass-reports
TAVILY_API_KEY=your_tavily_api_key
```

4. Start the application:
```bash
docker-compose up -d
```

## 📚 Usage

### Web Interface

Access the web interface at: [http://67.205.171.239:8501/](http://67.205.171.239:8501/)

1. Enter your legal research query
2. Select research parameters
3. Choose components (Case Law, Web Sources)
4. Generate your research report

### API Access

The API is available at: [http://67.205.171.239:8000/](http://67.205.171.239:8000/)

- `POST /research`: Start a new research request
- `GET /research/{research_id}`: Get research results
- `GET /research`: List all research requests

### MCP Protocol

The MCP server is available at: http://localhost:8080

- Resource: `research://{topic}`
- Tools:
  - `conduct_research`
  - `check_research_status`
  - `get_research_sources`

## 📁 Project Structure

```
DAMG-ASSIGMNENT5A/
├── backend/
│   ├── agents/
│   │   ├── legal_rag_agent.py
│   │   ├── websearch_agent.py
│   │   └── synthesis_agent.py
│   ├── langraph/
│   │   └── orchestrator.py
│   ├── utils/
│   │   └── helpers.py
│   ├── app.py
│   ├── server.py
│   └── requirements.txt
├── frontend/
│   ├── components/
│   │   ├── header.py
│   │   ├── sidebar.py
│   │   └── results.py
│   ├── app.py
│   └── requirements.txt
└── docker-compose.yml
```

## 🔍 Technical Details

### Vector Database

The system uses Pinecone for semantic search through the Massachusetts Reports. Each document is chunked and embedded with OpenAI's embedding model.

### LLM Integration

GPT-4 is used for:
- Legal analysis from case law
- Synthesis of web search results
- Generation of comprehensive reports

### Research Report Format

Reports are structured with:
- Executive summary
- Table of contents
- Legal analysis by principle
- Case citations
- Current interpretations
- Conclusion and recommendations

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contribution

- **Sai Priya Veerabomma** - 33.3% 
- **Sai Srunith Silvery** - 33.3% 
- **Vishal Prasanna** - 33.3% 
