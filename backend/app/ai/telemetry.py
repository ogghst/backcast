"""OpenTelemetry initialization for LangGraph/LangChain monitoring.

Exports traces to Jaeger for distributed tracing with OpenInference semantic conventions.
"""

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Environment variables (read at import time, before logging is configured)
OTEL_ENABLED = settings.OTEL_ENABLED
OTLP_ENDPOINT = settings.OTLP_ENDPOINT
ENABLE_CONSOLE_EXPORT = os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true"

# Debug: print to stdout since logging isn't configured yet
print(f"[DEBUG] OTEL_ENABLED={OTEL_ENABLED}, OTLP_ENDPOINT={OTLP_ENDPOINT}")


def initialize_telemetry(
    service_name: str = "backcast-ai",
    enable_console: bool = False,
    otlp_endpoint: str | None = None,
) -> TracerProvider | None:
    """
    Initialize OpenTelemetry with OpenInference instrumentors.

    Exports to Jaeger via OTLP with OpenInference semantic conventions.

    Controlled by the OTEL_ENABLED environment variable (default: "false").
    When disabled, returns None and no instrumentation is set up.

    Args:
        service_name: Name for this service in traces
        enable_console: If True, export to console for debugging
        otlp_endpoint: OTLP collector endpoint (default from OTLP_ENDPOINT env var)

    Returns:
        Configured TracerProvider, or None if telemetry is disabled
    """
    print(f"[DEBUG] initialize_telemetry called: OTEL_ENABLED={OTEL_ENABLED}")

    if not OTEL_ENABLED:
        logger.info("[OPEN_TELEMETRY] Disabled (OTEL_ENABLED=false)")
        return None

    # Set up trace provider with resource attributes
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource

    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Add OTLP exporter for Jaeger
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint or OTLP_ENDPOINT)
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Add console exporter for debugging (optional)
    if enable_console or ENABLE_CONSOLE_EXPORT:
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Instrument LangChain (works for LangGraph too!)
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

    # Instrument OpenAI (for token usage tracking)
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

    logger.info(f"[OPEN_TELEMETRY] Initialized with OTLP endpoint: {otlp_endpoint or OTLP_ENDPOINT}")

    return tracer_provider


@contextmanager
def trace_context(
    name: str,
    attributes: dict[str, str] | None = None,
) -> Generator[None, None, None]:
    """Context manager for creating custom spans.

    Use this to add custom tracing around specific operations.

    Example:
        with trace_context("agent.chat", attributes={"session_id": "123"}):
            # Your code here
            pass
    """
    if not OTEL_ENABLED:
        yield
        return

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name, attributes=attributes or {}):
        yield


@contextmanager
def trace_subagent_delegation(
    subagent_type: str,
    description: str | None = None,
) -> Generator[None, None, None]:
    """Context manager for tracing subagent delegation events.

    Creates a span with attributes indicating which subagent was delegated to.

    Args:
        subagent_type: Type of subagent (e.g., "evm_analyst", "project_admin")
        description: Optional task description

    Example:
        with trace_subagent_delegation("evm_analyst", "Calculate EVM metrics"):
            # Delegate to subagent
            pass
    """
    if not OTEL_ENABLED:
        yield
        return

    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)
    attrs = {
        "subagent.type": subagent_type,
        "subagent.delegated": "true",
    }
    if description:
        attrs["subagent.description"] = description

    with tracer.start_as_current_span("subagent.delegate", attributes=attrs):
        yield
