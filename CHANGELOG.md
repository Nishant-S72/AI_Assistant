# Changelog

All notable changes to the AI Chief-of-Staff POC project.

## [1.0.0] - 2024-01-XX

### Added

#### Infrastructure & Setup
- **Bootstrap script** (`scripts/bootstrap.sh`) - One-command setup that verifies Docker, creates `.env`, starts services, installs dependencies, and seeds data
- **Enhanced package.json scripts** - Added `bootstrap`, `test`, `lint` commands
- **Docker Compose** - Postgres, Redis, optional Chroma, and Adminer

#### LLM Abstraction Layer
- **Multi-LLM support** - Unified interface for OpenAI and Ollama
- **OpenAI adapter** (`backend/src/clients/llm/openaiAdapter.ts`) - Wraps official OpenAI SDK
- **Ollama adapter** (`backend/src/clients/llm/ollamaAdapter.ts`) - HTTP client for local Ollama instances
- **Fallback mechanism** (`backend/src/clients/llm/fallback.ts`) - Automatically tries Ollama first (if configured), then OpenAI, with clear error messages
- **Correlation IDs** - All LLM calls include correlation IDs for tracing
- **Latency logging** - Tracks and logs LLM response times

#### Vector Store Abstraction
- **Chroma adapter** (`backend/src/clients/vectorstore/chromaAdapter.ts`) - Full Chroma HTTP API integration with health checks
- **JSON adapter** (`backend/src/clients/vectorstore/jsonAdapter.ts`) - Fallback storage using local JSON file with cosine similarity
- **Auto-detection** (`backend/src/clients/vectorstore/index.ts`) - Automatically detects Chroma availability and falls back to JSON
- **Configurable mode** - `VECTORSTORE_MODE` env var to force chroma/json/auto

#### Embeddings Service
- **LRU cache** (`backend/src/services/embeddings.ts`) - In-memory cache for embeddings (24h TTL, 1000 entry limit)
- **Batch support** - Prepared for batch embedding calls
- **OpenAI integration** - Uses text-embedding-3-small model

#### Prompt Builder Improvements
- **PromptBuilder class** (`backend/src/services/promptBuilder.ts`) - Object-oriented prompt construction
- **Token estimation** - Rough token counting (1 token ≈ 4 chars)
- **Automatic truncation** - Truncates prompts if exceeding `MAX_PROMPT_TOKENS`
- **Text sanitization** - Removes control characters, limits chunk sizes
- **Gzipped storage** - Full prompts stored gzipped in `backend/storage/prompts/`
- **Metadata tracking** - Stores prompt metadata (tone, contact info, chunk counts, token estimates)
- **Template system** - Loads from `prompts/assistant_template.md` with fallback

#### Policy Engine
- **Rule-based system** (`backend/src/policy/policyEngine.ts`) - Configurable JSON-based rules
- **Default rules** - Refund, legal, chargeback, SSN detection
- **Confidence scoring** - Each rule has confidence level, threshold configurable via env
- **Policy file** (`backend/policy.json`) - Easy to edit rules without code changes
- **Reload support** - Rules can be reloaded without restart

#### Audit & Logging
- **Enhanced events table** - Added `correlation_id`, `request_path`, `user_id`, `prompt_ref`, `retrieved_ids`, `raw_model_response`, `final_text`, `latency_ms`
- **Admin endpoints** (`backend/src/routes/admin.ts`):
  - `GET /api/admin/audit` - View audit logs with pagination
  - `GET /api/admin/metrics` - Acceptance rate, avg latency, message counts
- **Token-based auth** - Admin routes protected with `ADMIN_API_KEY` or `DEMO_SEED_TOKEN`
- **Prompt references** - Links to gzipped prompt files in audit logs

#### Health Checks
- **Enhanced `/api/health`** - Checks database, Redis, vector store adapter, LLM availability
- **Structured response** - Returns status per service with overall health
- **Readiness checks** - Returns 503 if services degraded

#### Database
- **Improved schema** - Enhanced events table with audit fields
- **Migration support** - Idempotent schema initialization

#### Testing
- **Jest setup** - Unit test framework configured
- **Test files**:
  - `policyEngine.test.ts` - Policy rule testing
  - `vectorstore.test.ts` - JSON adapter query/similarity tests
  - `promptBuilder.test.ts` - Prompt truncation and sanitization tests
- **CI workflow** (`.github/workflows/ci.yml`) - Runs tests and linting on PRs

#### Linting
- **ESLint configuration** - TypeScript ESLint rules
- **Lint scripts** - `yarn lint` and `yarn lint:fix`

#### Documentation
- **Comprehensive README** - Setup, configuration, troubleshooting, API docs
- **CHANGELOG** - This file
- **Inline code comments** - Added throughout for clarity

### Changed

#### Backend Routes
- **Messages route** (`backend/src/routes/messages.ts`):
  - Uses new LLM abstraction (`generateChatCompletion`)
  - Uses new prompt builder (`PromptBuilder.buildForMessage`)
  - Uses new policy engine (`checkPolicy` with `ESCALATE` action)
  - Enhanced audit logging with correlation IDs and latency
  - Stores prompts (truncated in DB, full gzipped in storage)

#### Vector Store Service
- **Compatibility wrapper** (`backend/src/services/vectorStore.ts`) - Wraps new abstraction for backward compatibility
- **Migration path** - Old code continues to work, new code uses abstraction directly

#### Environment Variables
- Added: `USE_OLLAMA`, `LLM_BASE_URL`, `LLM_MODEL`, `VECTORSTORE_MODE`, `CHROMA_BASE_URL`, `LOG_LEVEL`, `ADMIN_API_KEY`, `POLICY_CONFIDENCE_THRESHOLD`, `MAX_PROMPT_TOKENS`

### Fixed

- Policy engine now returns `ESCALATE` instead of `ESCALATE_TO_HUMAN` (standardized)
- Vector store properly handles Chroma unavailability
- Prompt truncation prevents token limit errors
- Health check properly handles missing services

### Security

- Admin endpoints require authentication
- Policy engine blocks sensitive content before sending
- Audit logs track all LLM interactions
- Environment variables properly documented

### Performance

- Embedding cache reduces API calls
- Vector store JSON adapter limits memory usage (10k vector limit)
- Prompt truncation prevents oversized requests
- Correlation IDs enable request tracing

## Migration Notes

### From Previous Version

1. **Update `.env`**: Add new environment variables from `.env.example`
2. **LLM Configuration**: 
   - If using OpenAI: Set `OPENAI_API_KEY`, leave `USE_OLLAMA=false`
   - If using Ollama: Set `USE_OLLAMA=true`, `LLM_BASE_URL`, `LLM_MODEL`
3. **Vector Store**: System auto-detects, but you can set `VECTORSTORE_MODE=chroma|json|auto`
4. **Policy Rules**: Edit `backend/policy.json` to customize rules
5. **Run migrations**: Schema updates are automatic on server start

### Breaking Changes

- Policy engine action changed from `ESCALATE_TO_HUMAN` to `ESCALATE` (update frontend if checking this)
- Vector store interface changed (but compatibility wrapper maintains backward compatibility)

## Future Improvements

- [ ] Rate limiting middleware
- [ ] WebSocket support for real-time updates
- [ ] Gmail/WhatsApp actual integrations (currently simulated)
- [ ] Multi-tenant support
- [ ] Advanced RAG with re-ranking
- [ ] Fine-tuned policy models
- [ ] Dashboard for metrics visualization
- [ ] Export audit logs to external systems

