# Claude Environment Reference

## Commands
- **Install dependencies**: `npm install`
- **Run tests**: `npm test` (currently not configured)
- **Start application**: Not available in current configuration

## Code Style Guidelines
- **Formatting**: Follow JavaScript Standard Style
- **Naming Conventions**: 
  - camelCase for variables and functions
  - PascalCase for classes and components
  - UPPER_SNAKE_CASE for constants
- **Imports**: Group imports by source (built-in, external, internal)
- **Types**: Use TypeScript or JSDoc type annotations when possible
- **Error Handling**: Use try/catch blocks and avoid silent failures
- **Comments**: Document complex logic and public APIs

## Project Structure
This is a basic Node.js environment with Claude Code CLI installed. The project appears to be in early setup stages with minimal configuration.

## Dependencies
- @anthropic-ai/claude-code: ^0.2.32

## Environment Configuration

### Gitea Integration
Configuration stored in `.env` files:

- **Global**: `/home/micke/claude-env/.env`
- **Project**: `/home/micke/claude-env/docs-site/.env`

**Gitea Settings:**
- URL: `http://172.16.16.138:8181`
- Username: `micke`
- Token: `35cc69fd8ca1b7e6ee72fda67e7ee59d4ba47aa5`

### Docs-Site Project
Located at: `/home/micke/claude-env/docs-site/`

**Repository:** 
- Gitea: `http://172.16.16.138:8181/micke/docs-site`
- Local Git: Configured and synced

**Key Features:**
- MkDocs Material theme
- PlantUML integration (server: `http://localhost:8080`)
- MCP communication script (`update_docs.py`)
- Git automation (`push.sh`)
- Port: 6885 (configurable)

**Usage:**
```bash
cd docs-site
source .venv/bin/activate
mkdocs serve -a localhost:6885
```

**MCP Integration:**
```bash
python update_docs.py --file "page-name" --content "# Content" --nav-title "Title"
```

### How Configuration is Stored

1. **Environment Variables**: Stored in `.env` files (gitignored for security)
2. **Project Config**: `mkdocs.yml` contains project-specific settings
3. **Global Access**: Main `.env` in `/home/micke/claude-env/` for Claude Code reference
4. **Repository Links**: All URLs updated to point to correct Gitea instance

This ensures Claude Code will find the correct Gitea configuration in future sessions.

## Processhantering

När du startar eller stoppar servrar eller processer (exempelvis `npm start`, `vite`, `uvicorn`, etc), ska du alltid:

1. Försöka avsluta processen korrekt via `Ctrl+C` eller `npm stop`.
2. Om porten är upptagen, identifiera processen med `ps aux | grep <namn>` eller `lsof -i :PORT`.
3. Döda processen med `kill -TERM PID`. Om det inte räcker, använd `kill -9 PID` som sista utväg.
4. Alternativt kan `fuser -k PORT/tcp` användas för att frigöra porten.

Starta aldrig nya instanser på andra portar utan att först frigöra originalporten. Det är kritiskt eftersom andra systemkomponenter är beroende av specifika portar.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.