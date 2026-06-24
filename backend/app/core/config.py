from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    API_V1_STR: str
    PROJECT_NAME: str
    DEBUG: bool
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    PORT: int
    BACKEND_CORS_ORIGINS: list[str]
    BACKEND_CORS_METHODS: list[str]
    BACKEND_CORS_HEADERS: list[str]
    # Provider configuration
    RBAC_PROVIDER: str = "database"  # "database" | "entra" (future)
    AUTH_PROVIDER: str = "local"  # "local" | "oidc" (future)
    USER_PROVIDER: str = "local"  # "local" | "entra" | "hybrid" (future)

    # Database
    DATABASE_URL: PostgresDsn

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ASYNC_DATABASE_URI(self) -> PostgresDsn:
        return self.DATABASE_URL

    # Logging
    LOG_LEVEL: str
    LOG_FILE: str
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_MAX_BYTES: int = 50 * 1024  # 50 KB default
    LOG_BACKUP_COUNT: int = 10  # Keep up to 10 rotated log files

    # AI Token Buffering
    AI_TOKEN_BUFFER_ENABLED: bool = True
    AI_TOKEN_BUFFER_INTERVAL_MS: int = 2000  # 2 seconds default
    AI_TOKEN_BUFFER_MAX_SIZE: int = 10000  # Max tokens before forced flush

    # AI Approval Settings (used by BackcastSecurityMiddleware polling loop)
    AI_APPROVAL_TIMEOUT_SECONDS: float = 60.0
    AI_APPROVAL_POLL_INTERVAL_MS: float = 200.0
    AI_APPROVAL_HEARTBEAT_INTERVAL_SECONDS: float = 5.0

    # Specialist retry (transient API errors)
    AI_SPECIALIST_MAX_RETRIES: int = 3
    # Hard cap on tool calls WITHIN a single specialist invocation.  Lower than
    # the supervisor's budget (which inherits the graph recursion limit) because
    # a specialist does a focused 2-4 tool calls/step; an unbounded ReAct loop
    # (flat default 25) accumulates tool CALL+RESULT mass that drives GLM latency
    # super-linearly into the 120s active-time timeout.  Mounted alongside
    # ContextGuard on the specialist middleware stack.
    AI_SPECIALIST_MAX_TOOL_ITERATIONS: int = 8
    # Specialist-specific ContextGuard threshold.  Calibrated SEPARATELY from the
    # supervisor's ``AI_CONTEXT_TOKEN_LIMIT`` (120k) because specialists hit GLM's
    # ~25-30k-token latency knee (and the 120s active-time limit) far below the
    # supervisor's threshold.  A live e2e showed a specialist's prompt_tokens
    # running away to 31k at the 6th tool call — the supervisor's 120k guard never
    # triggered.  24000 sits safely under the knee; trimming kicks in at ~80%
    # (~19k).  Mounted on the specialist ContextGuard in ``compile_subagents``.
    AI_SPECIALIST_CONTEXT_TOKEN_LIMIT: int = 24000
    # Number of recent tool CALL/RESULT pairs kept verbatim by the specialist
    # ContextGuard (older results are summarized).  Lower than the supervisor's
    # ``AI_CONTEXT_KEEP_RECENT`` (8) because a specialist does a focused 2-4
    # calls/step — keeping 4 pairs preserves the current step's evidence without
    # re-inflating context past the latency knee.
    AI_SPECIALIST_CONTEXT_KEEP_RECENT: int = 4
    # Wall-clock timeout (seconds) for a single specialist invocation,
    # bounding provider stalls that never raise.
    AI_SPECIALIST_STEP_TIMEOUT: int = 120
    # Active (non-paused) seconds budget for a single planner LLM call
    # (fresh plan AND replan).  Bounds provider stalls that never raise;
    # pauses while an ask_user human-wait is pending.
    AI_PLANNER_STEP_TIMEOUT: int = 120
    # Active (non-paused) seconds budget around the WHOLE graph
    # astream_events loop (planner, supervisor reasoning, handoff tools,
    # middleware).  Bounds stalls anywhere outside a specialist body;
    # pauses while an ask_user human-wait is pending.
    AI_GRAPH_EXECUTION_TIMEOUT: int = 600

    # Default timeout (seconds) the ask_user tool waits for a human answer.
    # Must exceed AI_SPECIALIST_STEP_TIMEOUT so the specialist step clock
    # (which PAUSES while ask_user awaits a human) never races the answer.
    AI_ASK_USER_TIMEOUT_SECONDS: int = 300
    # Hard cap on USER-FACING ask_user prompts per execution.  Generous default
    # (8) allows a full legitimate requirements round while making runaway
    # re-asking structurally impossible regardless of model behavior (39
    # observed in a single runaway session).  Enforced inside the ask_user tool
    # BEFORE it publishes an event or marks the execution awaiting-user.
    AI_MAX_ASK_USER_PER_EXECUTION: int = 8

    # ExecutionLifecycle registry bounds + disconnect grace.
    # ``AI_EXECUTION_REGISTRY_MAX`` caps the in-memory execution context map
    # (single-server deployment); overflow drops the OLDEST entry with a warning
    # (non-destructive -- it never sets a live execution's stop_event).
    # ``AI_DISCONNECT_GRACE_SECONDS`` is the window after the last transport
    # observer detaches during which a still-running execution keeps going
    # before being requested to stop (lets a brief WS reconnect not abort a
    # long-running agent run).
    AI_EXECUTION_REGISTRY_MAX: int = 200
    AI_DISCONNECT_GRACE_SECONDS: int = 30

    # AI context trimming (ContextGuardMiddleware) + runtime toggles.
    # Exposed here (rather than read via os.environ in app.ai.config) so that
    # values in .env actually take effect; app.ai.config re-exports these.
    AI_CONTEXT_TOKEN_LIMIT: int = 120000
    AI_CONTEXT_SUMMARY_THRESHOLD_PCT: int = 80
    AI_CONTEXT_KEEP_RECENT: int = 8
    AI_DELEGATION_ENFORCED: bool = True
    AI_SEQUENTIAL_TOOL_CALLS: bool = True
    AI_MCP_TOOL_CATEGORY_PREFIX: str = "mcp:"
    AI_TOOLS_DEFAULT_PAGE_SIZE: int = 50

    # Refresh Token Configuration
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days default

    # OpenTelemetry
    OTEL_ENABLED: bool = False
    OTLP_ENDPOINT: str = "http://localhost:6006/v1/traces"

    # Cost Registration Attachments
    COST_REGISTRATION_MAX_ATTACHMENT_SIZE_MB: int = 10  # 10MB default

    # RustFS / S3 Storage
    RUSTFS_ENDPOINT_URL: str = "http://rustfs:9000"
    RUSTFS_ACCESS_KEY: str = "rustfsadmin"
    RUSTFS_SECRET_KEY: str = "rustfsadmin"
    RUSTFS_BUCKET_NAME: str = "backcast-documents"
    RUSTFS_PRESIGNED_URL_EXPIRY_SECONDS: int = 900  # 15 minutes
    # Public (browser-facing) base for presigned download URLs. Empty → fall back to
    # RUSTFS_ENDPOINT_URL (dev: localhost works; prod: the Traefik storage subdomain).
    RUSTFS_PUBLIC_URL: str = ""

    # Document Repository
    DOCUMENT_MAX_FILE_SIZE_MB: int = 50
    DOCUMENT_MAX_STORAGE_PER_PROJECT_MB: int = 10240  # 10 GB
    DOCUMENT_ALLOWED_EXTENSIONS: list[str] = [
        "pdf",
        "docx",
        "xlsx",
        "pptx",
        "txt",
        "csv",
        "md",
        "png",
        "jpg",
        "jpeg",
        "gif",
        "webp",
        "svg",
        "dwg",
        "dxf",
        "step",
        "igs",
        "zip",
        "rar",
    ]

    # Telegram Notifications
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_USE_POLLING: bool = False
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # Unified Notifications
    NOTIFICATION_DELIVERY_RETENTION_DAYS: int = 30

    # Agent Scheduling (in-process scheduler loop in the API server lifespan)
    SCHEDULER_POLL_INTERVAL_SECONDS: int = 60
    SCHEDULER_MAX_CONCURRENCY: int = 5
    SCHEDULER_MISFIRE_GRACE_SECONDS: int = 120


settings = Settings()
