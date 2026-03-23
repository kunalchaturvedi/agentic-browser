# Agentic Browser - Implementation Plan

## Project Vision
Create an agentic web browser that combines the power of LLMs with traditional web browsing. Instead of returning text summaries (like Perplexity/Google AI), this system generates beautiful, navigable HTML pages from search results while maintaining the rich visual presentation of traditional websites.

## Core Concept
- User enters a search query
- System searches web (Bing API), fetches relevant content
- LLM (Azure AI Foundry) processes and synthesizes information
- Generates a rendered HTML webpage (not just text)
- Hyperlinks are context-aware and generate new pages when clicked
- Seamless browser-like experience (not a chat interface)

## Technology Stack

### Backend
- **Python 3.10+** - Core application logic
- **FastAPI** - Web server framework (async, modern, fast)
- **Jinja2** - Template engine for HTML generation
- **Azure AI Foundry SDK** - LLM integration
- **Bing Search API** - Web search and content retrieval
- **BeautifulSoup4/Playwright** - Web scraping for content extraction
- **httpx** - Async HTTP client

### Frontend
- **HTML5/CSS3** - Page rendering
- **Vanilla JavaScript** - Minimal interactivity (no heavy frameworks initially)
- **Tailwind CSS** - Modern, utility-first styling

### Development Tools
- **Poetry/pip** - Dependency management
- **pytest** - Testing
- **black/ruff** - Code formatting
- **python-dotenv** - Environment configuration

## Architecture Design

```
┌─────────────────┐
│   Web Browser   │
│  (User's own)   │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────────────────────────────┐
│         FastAPI Server (Python)         │
│  ┌───────────────────────────────────┐  │
│  │      Route Handlers               │  │
│  │  /search, /page, /navigate        │  │
│  └────────┬──────────────────────────┘  │
│           │                              │
│  ┌────────▼──────────┐  ┌─────────────┐ │
│  │  Query Processor  │  │  Renderer   │ │
│  │   - Parse query   │  │  - Template │ │
│  │   - Context mgmt  │  │  - HTML gen │ │
│  └────────┬──────────┘  └──────▲──────┘ │
│           │                     │        │
│  ┌────────▼─────────────────────┴──────┐ │
│  │        Content Pipeline             │ │
│  │  ┌──────────┐  ┌──────────────┐    │ │
│  │  │ Search   │  │   Scraper    │    │ │
│  │  │ (Bing)   │─▶│ (Extract)    │    │ │
│  │  └──────────┘  └──────┬───────┘    │ │
│  │                       │              │ │
│  │  ┌────────────────────▼────────────┐ │ │
│  │  │    LLM Synthesizer              │ │ │
│  │  │    (Azure AI Foundry)           │ │ │
│  │  │  - Aggregate content            │ │ │
│  │  │  - Generate structured data     │ │ │
│  │  └─────────────────────────────────┘ │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Foundation Setup
- [ ] Initialize Python project structure
- [ ] Setup Poetry/pip with dependencies
- [ ] Create .env template for API keys
- [ ] Setup basic FastAPI application
- [ ] Create health check endpoint
- [ ] Test server runs on localhost

### Phase 2: Search Integration
- [ ] Integrate Bing Search API
- [ ] Create search query handler
- [ ] Implement rate limiting/error handling
- [ ] Test search results retrieval
- [ ] Parse search results into structured format

### Phase 3: Content Extraction
- [ ] Implement web scraper (BeautifulSoup4)
- [ ] Extract main content from URLs
- [ ] Clean and sanitize HTML
- [ ] Handle different webpage formats
- [ ] Implement content deduplication
- [ ] Add timeout and error handling

### Phase 4: LLM Integration (Azure AI Foundry)
- [ ] Setup Azure AI Foundry client
- [ ] Design prompt templates for synthesis
- [ ] Create structured output schema (JSON)
  - Title
  - Summary
  - Sections with headings
  - Key points
  - Related links with context
  - Images/media references
- [ ] Implement LLM content synthesis
- [ ] Add retry logic and error handling
- [ ] Test with various query types

### Phase 5: Rendering Engine
- [ ] Design base HTML template (Jinja2)
- [ ] Create CSS styling (Tailwind or custom)
- [ ] Implement JSON-to-HTML renderer
- [ ] Add navigation elements
- [ ] Create search interface page
- [ ] Implement responsive design
- [ ] Test rendering various content types

### Phase 6: Context-Aware Navigation
- [ ] Implement session management
- [ ] Store conversation context/history
- [ ] Create link handler for context updates
- [ ] Implement "navigate" endpoint
  - Accept link click + current context
  - Generate new page with updated context
- [ ] Add breadcrumb navigation
- [ ] Implement back/forward functionality

### Phase 7: User Interface Polish
- [ ] Design landing/search page
- [ ] Add loading states/animations
- [ ] Implement error pages (404, 500, etc.)
- [ ] Add keyboard shortcuts
- [ ] Create "new search" functionality
- [ ] Add accessibility features (ARIA labels)

### Phase 8: Testing & Optimization
- [ ] Write unit tests for core modules
- [ ] Write integration tests
- [ ] Performance testing (caching strategies)
- [ ] LLM response quality evaluation
- [ ] Cross-browser compatibility testing
- [ ] Load testing

### Phase 9: Enhancement Features (Future)
- [ ] Implement caching layer (Redis)
- [ ] Add bookmark/save functionality
- [ ] Create user preferences
- [ ] Implement search history
- [ ] Add export to PDF/markdown
- [ ] Multi-language support
- [ ] Mobile-responsive improvements

### Phase 10: Production Preparation (Future)
- [ ] Docker containerization
- [ ] Azure deployment configuration
- [ ] Setup CI/CD pipeline
- [ ] Production logging and monitoring
- [ ] Security hardening
- [ ] API key rotation strategy
- [ ] Documentation for deployment

## Project Structure

```
agentic-browser/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration management
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   ├── query.py           # Query models
│   │   └── content.py         # Content structure models
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── search.py          # Bing Search integration
│   │   ├── scraper.py         # Web content extraction
│   │   ├── llm.py             # Azure AI Foundry client
│   │   └── synthesizer.py     # Content synthesis orchestration
│   ├── rendering/              # HTML generation
│   │   ├── __init__.py
│   │   ├── renderer.py        # Template renderer
│   │   └── templates/         # Jinja2 templates
│   │       ├── base.html
│   │       ├── search.html
│   │       └── page.html
│   ├── routes/                 # API endpoints
│   │   ├── __init__.py
│   │   ├── search.py
│   │   └── navigate.py
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── context.py         # Context management
│       └── cache.py           # Simple caching
├── static/                     # Static assets
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
├── tests/
│   ├── __init__.py
│   ├── test_search.py
│   ├── test_scraper.py
│   ├── test_llm.py
│   └── test_rendering.py
├── .env.example               # Template for environment variables
├── .gitignore
├── pyproject.toml             # Poetry configuration
├── requirements.txt           # pip fallback
├── README.md
└── run.py                     # Development server script
```

## Key Design Decisions

### 1. Modular Renderer Architecture
- Abstract renderer interface allows swapping template-based → full HTML generation
- Initial: JSON schema → Jinja templates (predictable, fast)
- Future: Can add LLM-generated raw HTML renderer

### 2. Context Management
- Each page maintains conversation context
- Links include contextual metadata
- Enables "drill-down" navigation (e.g., "tell me more about X")

### 3. Search Strategy
- Initial: Bing Search API (1000 free queries/month, MS employee benefits)
- Fetch top 5-10 results
- Scrape and aggregate content
- LLM synthesizes into cohesive page

### 4. Rendering Strategy
- LLM outputs structured JSON (title, sections, links, etc.)
- Backend renders using Jinja2 templates
- Consistent styling, sanitized output
- Fast and reliable

### 5. Local-First Development
- Start with localhost:8000
- No authentication initially
- SQLite for session storage (if needed)
- Easy to deploy to Azure later

## Environment Variables Needed

```bash
# Azure AI Foundry
AZURE_OPENAI_ENDPOINT=your-endpoint
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment

# Bing Search
BING_SEARCH_API_KEY=your-bing-key
BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0/search

# Application
DEBUG=true
PORT=8000
HOST=localhost
```

## Success Metrics (MVP)

1. ✅ User can enter a search query
2. ✅ System fetches and displays a rendered HTML page (not text)
3. ✅ Page includes relevant content synthesized from multiple sources
4. ✅ Hyperlinks work and generate new context-aware pages
5. ✅ Experience feels like browsing, not chatting
6. ✅ Runs locally on localhost:8000

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM hallucinations | Include source citations, show "Sources" section |
| API rate limits | Implement caching, rate limiting, fallback strategies |
| Slow response times | Add loading states, async processing, CDN for static assets |
| Poor HTML generation | Start with templates (Option 2), iterate |
| Content extraction failures | Fallback to search snippets, handle errors gracefully |
| Cost overruns | Free tiers initially, monitor usage, implement quotas |

## Next Steps

1. ✅ **Discuss and refine requirements** (this document)
2. 🔲 **Get approval from you to proceed**
3. 🔲 **Setup project structure** (Phase 1)
4. 🔲 **Implement basic search** (Phase 2)
5. 🔲 **Integrate LLM and rendering** (Phases 4-5)
6. 🔲 **Build context-aware navigation** (Phase 6)
7. 🔲 **Test and iterate**

---

## Notes & Considerations

- **Flexibility**: Architecture supports both template-based and full HTML generation
- **Scalability**: Designed to scale from hobby project → production
- **MS Employee Benefits**: Leverage Azure/Bing free tiers
- **Learning Opportunity**: Combines web scraping, LLMs, full-stack development
- **User Experience**: Priority on feeling like a browser, not a chatbot

**Timeline Note**: This is a hobby project - no time estimates. Work at your own pace!
