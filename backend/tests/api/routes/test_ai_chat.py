"""Tests for AI chat WebSocket endpoint."""


import pytest


def test_ai_chat_websocket_endpoint_exists():
    """Test that AI chat WebSocket endpoint exists."""
    # We verify the endpoint is registered by checking the router
    try:
        from app.api.routes import ai_chat

        assert hasattr(ai_chat, "router")
        # Check that router has websocket route
        routes = list(ai_chat.router.routes)
        assert len(routes) > 0
        # Find websocket route
        ws_routes = [r for r in routes if hasattr(r, "path") and "ws" in r.path]
        assert len(ws_routes) > 0
    except ImportError:
        # Router doesn't exist yet (expected in RED phase)
        pytest.fail("AI chat router not found - implementation needed")
