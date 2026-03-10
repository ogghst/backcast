"""LangGraph StateGraph for AI agent orchestration.

Implements StateGraph with agent node, ToolNode, conditional edges, and MemorySaver checkpointer.
Follows LangGraph 1.0+ patterns with TypedDict state and bind_tools().
"""

from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.ai.state import AgentState

# Constants
MAX_TOOL_ITERATIONS = 5

# Constants
MAX_TOOL_ITERATIONS = 5


def should_continue(state: AgentState) -> Literal["agent", "tools", "end"]:
    """Determine the next step in the agent loop.

    Context: Conditional edge function for StateGraph that routes based on
    the last message type and tool call count.

    Args:
        state: Current agent state containing messages and tool_call_count

    Returns:
        "tools" if the last message has tool calls and under iteration limit
        "end" if no tool calls or max iterations reached
        "agent" (currently not used, reserved for future logic)

    Examples:
        >>> state = AgentState(
        ...     messages=[AIMessage(content="Hi", tool_calls=[...])],
        ...     tool_call_count=0,
        ...     next="agent"
        ... )
        >>> should_continue(state)
        'tools'
    """
    messages = state["messages"]
    tool_call_count = state["tool_call_count"]

    if not messages:
        return "end"

    last_message = messages[-1]

    # If the last message is from a tool, continue to agent
    if isinstance(last_message, ToolMessage):
        return "agent"

    # If the last message has tool calls, route to tools
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        # Check iteration limit
        if tool_call_count >= MAX_TOOL_ITERATIONS:
            return "end"
        return "tools"

    # Otherwise, end
    return "end"


def agent_node(
    state: AgentState,
    config: dict[str, Any],
    *,
    llm: BaseChatModel,
    tools: list[BaseTool],
) -> dict[str, Any]:
    """Agent node that calls the LLM with tools bound.

    Context: Node function for StateGraph that invokes the LLM with
    bind_tools() to enable tool calling. Updates messages and tool_call_count.

    Args:
        state: Current agent state
        config: Configuration dict (may contain model parameters)
        llm: The language model to use
        tools: List of tools to bind to the LLM

    Returns:
        Dictionary with updated state (messages list and tool_call_count)

    Examples:
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> tools = [list_projects_tool]
        >>> result = agent_node(state, {}, llm=llm, tools=tools)
        >>> updated_messages = result["messages"]
    """
    messages = state["messages"]
    tool_call_count = state["tool_call_count"]

    # Bind tools to LLM
    # This is the LangGraph 1.0+ way to enable tool calling
    llm_with_tools = llm.bind_tools(tools)

    # Invoke the LLM
    # The response will be an AIMessage, possibly with tool_calls
    response_message: BaseMessage = llm_with_tools.invoke(messages)

    # Update tool_call_count if tool calls were made
    new_tool_call_count = tool_call_count
    if isinstance(response_message, AIMessage) and response_message.tool_calls:
        new_tool_call_count += 1

    return {
        "messages": [response_message],
        "tool_call_count": new_tool_call_count,
    }


def create_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
) -> Any:  # Returns CompiledStateGraph[AgentState]
    """Create and compile a StateGraph for agent orchestration.

    Context: Factory function that builds the StateGraph with proper nodes,
    edges, and checkpointer. This is the main entry point for creating
    the LangGraph agent.

    Args:
        llm: The language model to use for the agent
        tools: List of tools available to the agent

    Returns:
        Compiled StateGraph ready for invocation

    Examples:
        >>> from langchain_openai import ChatOpenAI
        >>> from app.ai.tools import create_project_tools
        >>>
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> tools = create_project_tools(context)
        >>> graph = create_graph(llm, tools)
        >>>
        >>> # Invoke the graph
        >>> result = await graph.ainvoke({
        ...     "messages": [HumanMessage(content="Hello")],
        ...     "tool_call_count": 0,
        ...     "next": "agent"
        ... })
    """
    # Create StateGraph with AgentState
    workflow = StateGraph(AgentState)

    # Add agent node
    # We use a lambda to pass llm and tools to the node function
    workflow.add_node(
        "agent",
        lambda state, config: agent_node(
            state,
            config,
            llm=llm,
            tools=tools,
        ),
    )

    # Add tools node using LangGraph's prebuilt ToolNode
    # ToolNode automatically handles tool execution and result formatting
    tool_node = ToolNode(tools)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges from agent
    # Routes to "tools" if tool calls present, "end" otherwise
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # Add edge from tools back to agent
    # This creates the tool calling loop
    workflow.add_edge("tools", "agent")

    # Create checkpointer for state persistence
    # MemorySaver stores state in memory (for production, use PostgreSQL checkpointer)
    checkpointer = MemorySaver()

    # Compile the graph
    app = workflow.compile(checkpointer=checkpointer)

    return app


def export_graphviz(graph: Any) -> str:
    """Export a compiled StateGraph to DOT format for visualization.

    Context: Generates DOT format representation of the graph structure
    for debugging and documentation purposes. The output can be rendered
    using Graphviz tools or online DOT viewers.

    Args:
        graph: A compiled StateGraph from create_graph()

    Returns:
        DOT format string representing the graph structure

    Examples:
        >>> from langchain_openai import ChatOpenAI
        >>> from app.ai.tools import create_project_tools
        >>>
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> tools = create_project_tools(context)
        >>> graph = create_graph(llm, tools)
        >>>
        >>> # Export to DOT format
        >>> dot_output = export_graphviz(graph)
        >>> print(dot_output)
        >>>
        >>> # Save to file
        >>> with open("graph.dot", "w") as f:
        ...     f.write(dot_output)
        >>>
        >>> # Render with Graphviz (if installed)
        >>> # $ dot -Tpng graph.dot -o graph.png

    Note:
        This is a simplified DOT representation showing the basic structure.
        For more detailed visualization, consider using LangGraph's built-in
        visualization methods or the Mermaid export functionality.
    """
    # Get the graph structure from the compiled graph
    # The compiled graph has access to the underlying StateGraph
    try:
        # Access the underlying StateGraph
        builder = graph.builder

        # Start DOT format
        dot_lines = ["digraph AgentGraph {"]
        dot_lines.append("  rankdir=TB;")  # Top to Bottom layout
        dot_lines.append("  node [shape=box, style=rounded];")
        dot_lines.append("")

        # Add nodes
        # The builder stores the nodes added to the graph
        nodes_dict = builder.nodes

        for node_name, _node_fn in nodes_dict.items():
            # Format node label
            if node_name == "agent":
                label = "Agent\\n(LLM + Tools)"
            elif node_name == "tools":
                label = "Tools\\n(ToolNode)"
            else:
                label = node_name

            dot_lines.append(f'  {node_name} [label="{label}"];')

        dot_lines.append("")

        # Add edges
        # Entry point
        entry_point = builder.entry_point
        if entry_point:
            dot_lines.append(f'  __start__ -> {entry_point} [label="start"];')

        # Conditional edges from agent
        # should_continue routes to "tools" or "end"
        dot_lines.append("  agent -> tools [label=\"has tool_calls\"];")
        dot_lines.append("  agent -> __end__ [label=\"no tool_calls / max iterations\"];")

        # Edge from tools back to agent (creates the loop)
        dot_lines.append("  tools -> agent [label=\"tool result\"];")

        dot_lines.append("}")

        return "\n".join(dot_lines)

    except Exception:
        # Fallback: Return a simple DOT representation
        # This ensures the function never crashes
        return """digraph AgentGraph {
  rankdir=TB;
  node [shape=box, style=rounded];

  agent [label="Agent\\n(LLM + Tools)"];
  tools [label="Tools\\n(ToolNode)"];
  __end__ [label="End", shape=ellipse];

  __start__ -> agent [label="start"];
  agent -> tools [label="has tool_calls"];
  agent -> __end__ [label="no tool_calls / max iterations"];
  tools -> agent [label="tool result"];
}
"""
