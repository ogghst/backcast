"""Custom exceptions for the AI agent system."""


class ExecutionStoppedError(Exception):
    """Raised when a graph execution is gracefully stopped by user request or WS disconnect.

    Attributes:
        execution_id: The ID of the execution that was stopped.
    """

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        super().__init__(f"Execution {execution_id} stopped by user")
