# Project Structure

This document describes the repository layout for the `agentic-intelligence-codebase-parser` project.
Each file or folder includes a short explanation of its purpose.

> Note: `.venv/` is the Python virtual environment and is not part of the application source.

```
./                                      # Repository root
├── .venv/                              # Local Python virtual environment
├── codebase-agent/                     # Main application package
│   ├── .env                            # Runtime configuration values
│   ├── .env.example                    # Example environment configuration
│   ├── .gitignore                      # Git ignore rules for the app package
│   ├── cli/                            # Command-line interface code
│   │   ├── __init__.py                 # CLI package marker
│   │   ├── config_ui.py                # Interactive configuration editor
│   │   ├── file_browser.py             # Repository browsing and file filter navigation
│   │   ├── main.py                     # CLI entry point and doctor command
│   │   └── repo.py                     # Isolated repository cloning helper
│   ├── core/                           # Core configuration and settings
│   │   ├── __init__.py                 # Core package marker
│   │   └── config.py                   # Environment settings loader
│   ├── data/                           # Storage for app data and artifacts
│   │   ├── cache/                      # Cache storage
│   │   ├── repos/                      # Cloned repository storage
│   │   └── vector/                     # Vector data storage
│   ├── models/                         # Model adapter implementations
│   │   ├── __init__.py                 # Models package marker
│   │   ├── base.py                     # Base model interface for adapters
│   │   ├── gemini.py                   # Gemini model adapter implementation
│   │   └── ollama.py                   # Ollama model adapter implementation
│   ├── output/                         # Output-related package placeholder
│   │   └── __init__.py                 # Output package marker
│   ├── prompts/                        # Prompt templates and system prompts
│   │   └── system.md                   # System prompt content
│   ├── requirements.txt                # Python dependencies required by the app
│   ├── storage/                        # Storage-related package placeholder
│   │   ├── __init__.py                 # Storage package marker
│   │   └── sqlite_store.py             # Phase 1 placeholder for SQLite storage
│   ├── indexing/                       # Phase 1 raw RAG loop components
│   │   ├── __init__.py                 # Indexing package marker
│   │   ├── scanner.py                  # Placeholder for repository scanning logic
│   │   ├── chunker.py                  # Placeholder for content chunking logic
│   │   └── embedder.py                 # Placeholder for embedding logic
│   ├── context/                        # Phase 2 retrieval and context utilities
│   │   ├── __init__.py                 # Context package marker
│   │   ├── retriever.py                # Placeholder for similarity retrieval
│   │   └── context_pack.py             # Placeholder for prompt context assembly
│   └── tools/                          # Helper tools package placeholder
│       └── __init__.py                 # Tools package marker
└── phases/                             # Project phase documentation
    └── phase-0.md                      # Phase 0 setup and status notes
```

