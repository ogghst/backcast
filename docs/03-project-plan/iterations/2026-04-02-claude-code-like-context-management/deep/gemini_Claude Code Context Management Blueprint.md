# **Architectural Blueprint for LLM Context Management: Comprehensive Insights from Claude Code and LangGraph Implementations**

## **Introduction to Context Rot and Attention Budgets**

As large language models transition from conversational interfaces to autonomous, long-running agentic workflows, the management of the model's active working memory—the context window—has emerged as the primary constraint on performance, reliability, and economic viability. Context engineering is the systematic curation of system prompts, tool definitions, environment data, and historical message trajectories to optimize the large language model's finite attention budget.1 While model capabilities have rapidly expanded to support context windows of up to one million tokens, the assumption that massive context windows eliminate the need for rigorous memory management is fundamentally flawed.2

The core issue lies in the critical technical distinction between context window overflow and context rot. Context window overflow is a binary, terminal failure state that occurs when the progressive token accumulation of user messages, tool execution results, and the assistant's extended reasoning blocks exceeds the model's absolute maximum supported limit.2 In stark contrast, context rot is a continuous, measurable degradation in output quality that occurs well before the capacity limit is reached.3 According to comprehensive 2025 research conducted by Chroma, which systematically evaluated eighteen frontier models including Anthropic's Claude families, performance degrades gradually as the signal-to-noise ratio within the prompt decreases.3 A model operating comfortably within a 200,000-token limit may begin to exhibit severe context rot at just 50,000 tokens, resulting in symptomatic failures such as repeating previously completed work, contradicting earlier architectural decisions, and redundantly re-reading codebase files that were already processed in the current session.3 Furthermore, the Chroma research indicates that all evaluated models degrade universally with length, that low semantic similarity between queries and actual answers exponentially accelerates this rot, and that the presence of distractor information severely compounds the degradation.3

The March 31, 2026, source code leaks of Anthropic's flagship AI coding agent, Claude Code—which exposed over 512,000 lines of highly guarded TypeScript via an inadvertently published source map file in an npm package—provide an unprecedented technical blueprint for how enterprise-grade autonomous systems mitigate context rot.5 By analyzing the leaked query.ts main execution loop, the sophisticated four-stage compaction pipeline, the "Kairos" background memory consolidation daemon, and advanced prompt caching mechanisms, a comprehensive paradigm for agentic memory management emerges.5 This report exhaustively deconstructs Claude Code's context management strategies and translates these proprietary techniques into a scalable, open-source architecture utilizing the LangGraph framework.

## **The Hybrid Context Engine: Up-front Injection versus Progressive Disclosure**

Early iterations of AI coding agents relied almost exclusively on Retrieval-Augmented Generation, mapping entire codebases into vector databases and retrieving relevant chunks based on semantic similarity when a user issued a query. However, for highly dynamic environments like active codebases, complex syntax trees and stale indexing frequently lead to misaligned context, polluting the context window with outdated or irrelevant logic.1 Claude Code completely abandons pure semantic vector retrieval in favor of a hybrid context model that carefully balances the speed of pre-computed data injection with the accuracy of Just-In-Time autonomous discovery.1

### **Up-front Context Initialization and State Markers**

Before a user even types their first query, the Claude Code system silently loads a highly curated, minimal set of static and semi-static state indicators into the context window to establish the operational baseline.4 This includes the CLAUDE.md file, which serves as a persistent, project-specific instruction layer ensuring that architectural rules survive session resets.1 Alongside this, the system loads auto-memory files, Model Context Protocol tool names, and skill descriptions.4

This up-front injection is strictly bounded to preserve the attention budget. For example, instead of loading the full API schemas for all available tools—which could consume tens of thousands of tokens before any work begins—Claude Code relies on a principle of progressive disclosure. It loads highly abbreviated tool descriptions, costing merely thirty to fifty tokens initially, and only fetches the full schema when the model explicitly determines a need to invoke that specific skill.4 To further conserve upfront tokens when dealing with massive toolsets, Anthropic utilizes a "Tool Search Tool." This meta-tool preserves over 190,000 tokens of context by deferring the loading of over fifty Model Context Protocol tools until the model dynamically searches for them using regular expressions or BM25 indexing.10

### **Autonomous Environmental Navigation**

Once the baseline up-front context is established, Claude Code relies on standard operating system primitives rather than pre-indexed semantic databases to explore the repository. Primitives such as glob and ripgrep allow the agent to autonomously navigate its environment and retrieve specific files just-in-time.1 Furthermore, it leverages fundamental bash commands like head and tail to sample large volumes of data, such as server logs or massive compiled outputs, without pulling entire objects into the context window and triggering immediate overflow.1 This hybrid approach effectively treats the local file system as the absolute, real-time source of truth, bypassing the latency, token overhead, and staleness associated with external vector stores.1

### **User-Directed Context Pruning**

To prevent unnecessary context accumulation during routine developer interactions, the system provides specific commands for one-off tasks. For example, the /btw command allows developers to ask isolated questions whose answers appear in a dismissible user interface overlay.9 By design, queries executed via /btw are never appended to the permanent conversation history array, strictly preventing tangential discussions from bloating the working memory.9 Similarly, the /rewind command allows users to manually discard failed agentic attempts. By double-tapping the Escape key or executing /rewind, developers can revert the conversation state, the codebase state, or both to a previous checkpoint.9 This effectively truncates the state array, discarding the dead-end token accumulation generated by a hallucinated or flawed implementation path.9

## **The Lifecycle of an Agentic Query: The query.ts Architecture**

To understand how context is dynamically managed, it is necessary to analyze the exact lifecycle of a request as defined in the leaked query.ts file, which spans over 1,700 lines of highly optimized TypeScript.5 The entire execution engine operates as an asynchronous generator where every event—including text chunks, tool calls, progress updates, errors, and compaction boundaries—flows through a single yield-based stream.11 This unified stream allows the terminal user interface, the software development kit, and the integrated development environment bridge to consume the exact same events while rendering them differently.11

### **System Prompt Assembly and Snapshotting**

When a user submits a message, the system first enters the "Process Input" phase, parsing slash commands, evaluating file attachments, and processing any queued commands.11 Following this, the engine dynamically assembles the system prompt. Unlike traditional language model applications that utilize a single static string, Claude Code constructs its system prompt from approximately fifteen composable prompt sections.11 Before entering the primary query loop, the system also executes a snapshotting phase. Utilizing a Least Recently Used cache capable of holding up to one hundred files or twenty-five megabytes of data, the system records the current state of the environment to enable instantaneous undo functionality without requiring the model to generate diffs or reversal code.11

### **State Segregation in the Terminal Architecture**

A critical mechanism for preventing context window overflow is the strict segregation of system state from language model state. The leak reveals that the main terminal user interface is a massive single React component spanning 5,005 lines, containing 68 state hooks and 43 effects, with JSX nesting reaching 22 levels deep.12 While this architecture is highly complex, it serves a vital purpose: it keeps extensive telemetry, user interface state, and hidden features out of the prompt.

For instance, the leaked codebase includes an elaborate companion pet system called "Buddy," an unreleased feature complete with 18 species, rarity tiers, and statistics generated from a seeded pseudo-random number generator hashed from the user's ID.12 If the state of this Tamagotchi-like companion, or the extensive OpenTelemetry tracking data 6, were passed into the language model's context array, it would cause rapid token exhaustion. By managing this entirely within React state hooks and Zustand stores 6, the architecture guarantees that the LLM's finite attention budget is spent exclusively on the coding task.

## **The Compaction Cascade: A Four-Stage Mitigation Strategy**

The most technically revealing aspect of the Claude Code leak regarding memory management is the context pressure mitigation system defined in the main query loop within the query.ts file.5 When the progressive token accumulation approaches capacity—typically triggering when context usage hits roughly 80% to 95% of the allocated budget—the system does not simply truncate the oldest messages, which would destroy the semantic continuity of the session.4 Instead, it processes the conversational trajectory through a highly deterministic, four-stage compaction cascade designed to maximize signal retention while violently discarding noise.5

### **Stage 1: Tool Result Budgeting**

Located at query.ts:379, the first line of defense is strict, pre-emptive per-message budgeting.5 The system enforces hard token caps on the outputs of individual tool executions to prevent a single verbose command—such as an unpaginated database query, a massive compiler error log, or an uncontrolled loop output—from instantaneously overwhelming the context window and causing a catastrophic overflow.5

The readable source reveals precise exemptions to this rule. Results from specific "Read" tools bypass this budgeting phase entirely. Tools configured with the specific parameter maxResultSizeChars: Infinity are explicitly exempted from the per-message budget according to logic found in utils/toolResultStorage.ts:816.5 This critical exemption ensures that when the model intentionally requests a full file read to understand complex logic, the content is delivered completely intact. Silent truncation of requested file reads is a primary vector for model hallucinations, as the LLM may assume the truncated code does not exist and rewrite it, corrupting the file.5

### **Stage 2: Microcompaction**

If proactive budgeting is insufficient to halt the approaching overflow, the system triggers microcompaction at query.ts:413.5 Microcompaction is a highly targeted summarization and deletion protocol aimed exclusively at specific, low-value tool results.5

Microcompaction is deeply selective. Its eligibility is restricted solely to a predefined COMPACTABLE\_TOOLS set defined in the services/compact/microCompact.ts module.5 Tool results generated by Model Context Protocol tools, custom user-defined tools, and parallel agent tools are strictly excluded from microcompaction; their outputs are deemed too critical to system state and are preserved until the final autocompact stage.5 Furthermore, the system employs an internal keepRecent threshold dynamically configured to protect the most recent tool executions from being summarized.5 This ensures that the model always maintains immediate access to raw, unadulterated data for its current cognitive step before that data decays into a lossy summary.5

### **Stage 3: Context Collapse**

The third stage in the cascade, located at query.ts:440, represents an advanced, feature-flagged strategy internally codenamed "marble\_origami".5 Context collapse allows the system to compress extremely verbose tool results mid-conversation without requiring the overhead of executing a complete, expensive autocompaction cycle.11

For instance, if the model executed a comprehensive test suite twenty turns ago yielding 500 lines of standard output, context collapse can seamlessly shrink this into a short diagnostic representation indicating pass/fail status and key errors. Crucially, these collapses are not destructive in the persistent storage layer. They are saved in the session transcript as ContextCollapseCommitEntry records.11 This novel architectural choice enables the system to selectively un-compact or re-expand the original data if the model later requires exact string matching, deep debugging of a specific trace, or access to the granular details of the collapsed log.11

### **Stage 4: Autocompaction**

When context usage inevitably breaches the critical threshold despite budgeting, microcompaction, and context collapse, the final fallback is full autocompaction, triggered at query.ts:453.5 Autocompaction is inherently a lossy operation that replaces the vast majority of the conversation history with a synthesized summary containing core code patterns, file states, and key architectural decisions.4 The behavior of this stage is meticulously governed by a heavily engineered system prompt located at services/compact/prompt.ts:359.5

The autocompact prompt strictly instructs the summarization model to "pay special attention to specific user feedback" and explicitly mandates the absolute preservation of "all user messages that are not tool results".5 Once the summarization is complete, a seamless transition prompt is injected into the active session: *"Please continue the conversation from where we left it off without asking the user any further questions. Continue with the last task that you were asked to work on"*.16 This vital directive ensures the autonomous agent does not stall awaiting human confirmation post-compaction, maintaining fluid execution.16

Users also retain granular control over this process. By utilizing the /compact command, developers can manually trigger a summary focused on specific criteria by appending directives, such as /compact Focus on the API changes.9 Alternatively, developers can configure custom compaction behavior permanently within the CLAUDE.md file by adding rules like *"When compacting, always preserve the full list of modified files and any test commands"* to guarantee that domain-specific critical context survives the lossy summarization.9

| Compaction Stage | Execution Locus | Mechanism of Action | Key Exemptions & Technical Constraints |
| :---- | :---- | :---- | :---- |
| **Tool Budgeting** | query.ts:379 | Caps the character and token size of individual tool outputs to prevent sudden spikes. | Explicitly exempts tools configured with maxResultSizeChars: Infinity (e.g., direct file reads). |
| **Microcompaction** | query.ts:413 | Triggers targeted summarization of older, low-value outputs from standard tools. | Exempts MCP tools, agent tools; strictly respects dynamic keepRecent thresholds. |
| **Context Collapse** | query.ts:440 | Mid-conversation compression of verbose logs without full session summarization. | Fully reversible via ContextCollapseCommitEntry persistence in the transcript. |
| **Autocompaction** | query.ts:453 | Lossy, comprehensive summarization of the entire session history. | Strictly preserves human user messages and persistent CLAUDE.md instruction data. |

### **Security Implications: The Autocompaction Laundering Path**

The architectural reliance on the autocompaction pipeline introduces a severe, inverted threat model that fundamentally challenges traditional AI security paradigms.5 Standard security guardrails are designed assuming a hostile language model and a cooperative human user, focusing on inspecting model outputs to prevent the generation of malicious code. However, as revealed in the Claude Code leaks, the autocompact prompt's explicit mandate to faithfully preserve "user feedback" creates a highly effective laundering path for malicious context poisoning.5

If an attacker injects hostile instructions into an open-source file, an external dependency, or a localized CLAUDE.md, the model reads it during standard autonomous exploration. When the context window reaches capacity and autocompaction triggers, the summarization model dutifully interprets the hostile instructions found in the context as legitimate "user feedback" and preserves them with high priority in the condensed summary.5 Post-compaction, the primary operational model can no longer distinguish between genuine human directives and the weaponized context.5 The model remains highly cooperative, but because the context itself has been weaponized, it acts as an unwitting proxy for arbitrary code execution, generating commands that a human developer might quickly approve because the source of the malicious intent has been laundered into the system's core summary.5

### **Error Recovery and Context Resilience**

Even with a robust compaction pipeline, boundary failures occur when API limits fluctuate or token estimation calculations are slightly inaccurate. The leaked query.ts module reveals how Anthropic engineered resilience into the execution loop to survive these boundaries without crashing the user's terminal session.11

When the Anthropic API returns a prompt\_too\_long error, the system does not surface this fatal error to the user. Instead, the query.ts loop catches the exception, triggers a *reactive compaction* cycle retroactively compressing the context, and silently retries the API request with the newly reduced payload.11 Similarly, the system employs a "withhold and recover" pattern for max\_output\_tokens errors.17 If the model hits its output generation limit mid-reasoning, the streaming message is withheld from the software development kit subscribers. The system then attempts an auto-continuation to seamlessly finish the generation, allowing up to MAX\_OUTPUT\_TOKENS\_RECOVERY\_LIMIT \= 3 continuations before yielding the final merged response.17

Furthermore, the system features robust handling of rate limiting (429) and server overload (529) API errors. Upon encountering these codes, Claude Code analyzes the retry-after header.17 If the delay is beneath a specific SHORT\_RETRY\_THRESHOLD\_MS, it executes an immediate retry using the exact same model name to ensure the prompt cache remains valid.17 If the delay is extensive, the system executes a "fast mode fallback," automatically degrading to a smaller, faster model or initiating an exponential backoff sequence.17 For unattended CI/CD sessions managed by the agent, setting CLAUDE\_CODE\_UNATTENDED\_RETRY enables an infinite retry loop with a five-minute maximum backoff, emitting heartbeat signals every thirty seconds to prevent host pipelines from terminating the session due to inactivity.17

## **Prompt Caching and Speculative Prefetching**

To make the continuous evaluation of large contexts economically viable and performant during rapid agentic loops, Claude Code implements aggressive optimizations centered around the Anthropic API's prompt caching capabilities.18 Prompt caching allows the model to skip the recomputation of static context prefixes, drastically reducing inference response latency and token costs.19 However, leveraging this requires meticulous structuring of the prompt payload.

### **The Dynamic Boundary Cache System**

The system prompt in Claude Code is not a monolithic block of text; it is highly dynamic, composed of approximately fifteen distinct composable functions that define behavioral rules, tool usage guidelines, and safety constraints.11 To optimize this massive instruction set for caching, the engineering team implemented a precise split marker within the prompt structure: \_\_SYSTEM\_PROMPT\_DYNAMIC\_BOUNDARY\_\_.11

The segment of the prompt located above this boundary contains completely static, immutable instructions. To maximize cache hits globally across the entire user base, this static half is hashed using Blake2b prefix variants.11 The segment below the dynamic boundary contains session-specific, highly mutable data, such as the user's localized CLAUDE.md rules, specific environment variables, and dynamically loaded Model Context Protocol schemas.11

By organizing the prompt strictly along this axis and placing the explicit cache\_control block at the boundary, the agent reliably reuses roughly 3,000 tokens of core instructions on every single conversational turn.11 This architectural discipline is necessary because prompt caching operates on contiguous prefixes; any alteration to the prefix results in a complete cache miss, requiring full recomputation.18 The caching infrastructure imposes minimum cacheable prompt lengths depending on the underlying model: 1,024 tokens for Claude 3.7 Sonnet, 2,048 tokens for Sonnet 4.6, and 4,096 tokens for Opus 4.6 and Haiku 4.5.18 By ensuring the static block exceeds these minimums, Anthropic guarantees baseline caching efficiency regardless of which model the user routes their task to.

### **Explicit Resource Management and Latency Hiding**

The leak also highlights deep, systems-level architectural optimizations designed to hide local input/output latency from the user during context management. While the large language model is streaming its response chunks from the Anthropic API over the network, the Claude Code system does not passively wait.11 It simultaneously executes a "relevant memory prefetch" based on the early reasoning tokens of the incoming stream.11

To implement this safely in a concurrent environment, the engineers utilized modern TC39 explicit resource management—specifically leveraging the using keyword in TypeScript.11 This guarantees that memory prefetch operations, file handles, and database cursors are aggressively and deterministically cleaned up across all execution exit paths, preventing memory leaks in the Node.js/Bun runtime.6 By the time the model finishes streaming its extended thinking block and formally issues a tool call array, the required I/O read operations from the local disk have already been completed via the prefetch mechanism, effectively masking the file system latency entirely.11 Furthermore, the system employs speculative execution, pre-computing likely next responses, confirmations, or tool validation checks while the human user is still typing their follow-up prompt in the terminal.11

## **Skeptical Memory and the Kairos Daemon Architecture**

Beyond active session management, the leaked source code exposes an unreleased background paradigm that profoundly shifts the operational model of the large language model from a reactive, request-response tool into an autonomous, always-on daemon.8 Referenced over 150 times throughout the source repository, the "Kairos" feature flag controls a persistent system process that radically reinvents how long-term memory is managed and consolidated without destroying the active context window.8

### **The AutoDream Garbage Collector**

Within the Kairos architecture, a specialized, forked sub-agent located in the services/autoDream/ directory executes quietly during detected user idle periods.8 This process, referred to internally as memory consolidation, functions essentially as a sophisticated garbage collector for the agent's accumulated state.8

Over days of continuous use across multiple terminal sessions, the agent accumulates fragmented observations, redundant tool outputs, and potentially conflicting state data. The autoDream process analyzes append-only daily log files, merges disparate observations, aggressively removes logical contradictions across sessions, and converts vague, tentative notes into confirmed, absolute facts.8 To prevent this massive data processing load from overwhelming the developer's terminal or incurring noticeable costs, Kairos enforces a strict 15-second blocking budget, ensuring proactive actions never interrupt the human's workflow.8 Crucially, by running as a completely separate forked sub-agent, Anthropic ensures that the primary agent's active "train of thought" and highly curated working memory context are not corrupted or poisoned by its own internal maintenance and consolidation routines.22

### **The Three-Layer Skeptical Memory Philosophy**

A defining philosophical shift in Claude Code's design is its highly constrained treatment of long-term memory retrieval.15 Instead of eagerly loading vast amounts of historical data into the context window under the assumption that more context yields better results, the system employs a "skeptical" three-layer memory architecture.15

The first layer centers on a file called MEMORY.md, which acts as a lightweight index storing only short pointers and references rather than full semantic information.15 Detailed project notes reside in a completely separate second layer and are only pulled into the active context strictly on demand, while the third layer involves selective, bounded searches of past session histories rather than wholesale loading.15

The critical design directive defining this architecture is that the agent is explicitly instructed by its system prompt to treat its own retrieved memories not as absolute facts, but merely as *hints*.15 Before acting on a remembered project detail—such as the structure of an API endpoint or the dependencies of a modified class—the agent is required to verify the hint against the actual, current state of the codebase using standard tools.15 This design deeply acknowledges that active codebases mutate rapidly and unpredictably; blindly trusting an indexed semantic memory of a file from three days ago is a primary vector for inducing hallucinations. By enforcing a mandatory verification step, the system remains incredibly lean, consumes vastly fewer tokens, and drastically improves its reliability and safety.15

## **Multi-Agent Context Isolation and Coordinator Mode**

To prevent the main conversational thread from succumbing to context rot during deep investigative tasks, Claude Code relies heavily on a parallel sub-agent architecture.4 The underlying principle is that context isolation is the only reliable method to scale reasoning without exponentially scaling token costs and signal degradation.

When a user issues a command such as *"use subagents to investigate how our authentication system handles token refresh, and whether we have any existing OAuth utilities I should reuse"* 9, the primary agent instantly shifts its role to act as a supervisor.9 It spawns a parallel worker agent operating within a completely fresh, fully isolated context window.9 The sub-agent is granted the standard suite of tools necessary to navigate the repository, executing grep, reading files, and following logic chains deep into the system structure.

Because the sub-agent operates in strict isolation, the massive volume of tokens consumed by reading dozens of source files, executing search queries, and reasoning through dead ends never enters the user's primary context window.9 Upon successfully completing its investigation, the sub-agent distills its findings and returns only a highly concentrated semantic summary—along with a small metadata trailer indicating precisely which files it modified or reviewed—back to the main conversational thread.9

The source code leak indicates this capability is managed by an unreleased feature flag called "Coordinator Mode," which explicitly turns the primary instance into an orchestration engine managing parallel worker agents.12 It is worth noting that while highly effective at preserving context, Anthropic warns that utilizing experimental agent teams can drive up API costs to approximately seven times higher than standard sessions.9 To mitigate this, best practices dictate specifying lighter, cheaper models—such as model: haiku or Claude 3.7 Sonnet instead of the massive Opus models—for the worker subagents.9

## **Translating Claude Code's Paradigm to LangGraph**

The architectural patterns exposed in the Claude Code leak—specifically the multi-tier compaction cascade, the rigorous context isolation of the Coordinator mode, and the skeptical memory consolidation of the Kairos daemon—provide a flawless, highly technical template for building enterprise-grade agents using LangChain's open-source LangGraph library.25

LangGraph's foundational concept of managing state through cyclical graph nodes, combined with short-term memory persistence and middleware state reducers, allows for the precise, granular replication of Anthropic's sophisticated harness.28 The following sections detail the exact implementation strategies required to build a Claude Code-equivalent system.

### **1\. Defining the Core State and Memory Saver**

In LangGraph, context is dynamically maintained within a typed State object that flows deterministically between nodes.27 To replicate the sophisticated state management of Claude Code, the state must track not only the standard conversation history but also persistent environmental instructions (the CLAUDE.md equivalent), execution tracking metrics (like the keepRecent threshold for microcompaction), and the user's granular preferences.28

Python

from typing import Annotated, TypedDict, List, Dict, Any, Optional  
from langchain\_core.messages import BaseMessage  
from langgraph.graph.message import add\_messages  
from pydantic import BaseModel, Field

class AgentState(TypedDict):  
    \# The add\_messages reducer strictly handles appending new messages to the history array  
    \# while allowing removal via RemoveMessage commands.  
    messages: Annotated, add\_messages\]  
      
    \# Persistent project instructions loaded upfront (replicating CLAUDE.md)  
    system\_directives: str   
      
    \# Tracking tool execution budgets to prevent overflow  
    tool\_budgets: Dict\[str, int\]  
      
    \# Tracking the dynamic window size for targeted microcompaction  
    window\_size: int  
      
    \# Summary of older collapsed context (replicating marble\_origami)  
    context\_summary: Optional\[str\]  
      
    \# Tracking user preferences (e.g., fast mode fallbacks, selected models)  
    preferences: Dict\[str, Any\]

To ensure session persistence and allow for functionalities identical to Claude Code's /rewind checkpointing 9, an InMemorySaver or a persistent database-backed checkpointer must be attached to the compiled graph.28 Every node execution step automatically creates an immutable state checkpoint, allowing developers to safely restore the conversation or code state to any previous node dynamically.29

### **2\. Implementing the Compaction Pipeline**

The LangGraph implementation of the query.ts cascade requires custom nodes and middleware functions to mathematically evaluate and intercept the state before it is passed to the language model.28

#### **Stage 1 & 2: Token Budgeting and Microcompaction**

LangGraph provides robust utilities to trim messages based strictly on token limits utilizing middleware with a beforeModel hook.28 To accurately replicate the microcompaction logic and the COMPACTABLE\_TOOLS array, we can utilize the RemoveMessage utility to excise specific, low-value tool results while vigilantly preserving human messages and recent tool outputs.28

Python

from langchain\_core.messages import RemoveMessage, ToolMessage, HumanMessage  
import tiktoken

def micro\_compact\_node(state: AgentState) \-\> AgentState:  
    messages \= state\["messages"\]  
    window\_size \= state.get("window\_size", 5)  
      
    \# Identify messages to remove: old tool results that are NOT in the exempt list.  
    \# This precisely replicates the COMPACTABLE\_TOOLS logic from services/compact/microCompact.ts  
    exempt\_tools \= \["mcp\_execute", "agent\_handoff", "read\_file\_infinity"\]  
    messages\_to\_remove \=  
      
    \# Only evaluate messages strictly older than the keepRecent window  
    historical\_messages \= messages\[:-window\_size\]  
      
    for msg in historical\_messages:  
        \# Check if the message is a tool result and not explicitly protected  
        if isinstance(msg, ToolMessage) and msg.name not in exempt\_tools:  
            \# Issue a RemoveMessage command for this specific ID.   
            \# This does not delete the object here; it instructs the state reducer to drop it.  
            messages\_to\_remove.append(RemoveMessage(id\=msg.id))  
              
    \# Returning RemoveMessage objects tells the add\_messages reducer to finalize deletion  
    return {"messages": messages\_to\_remove}

#### **Stage 4: Autocompaction**

When the total token count approaches the model's predefined limit, a dedicated summarization node is triggered.31 This node utilizes a secondary, lightweight LLM call to compress the history, adhering rigorously to the strict guidelines observed in the leaked services/compact/prompt.ts.5

Python

from langchain\_core.messages import SystemMessage, AIMessage

def autocompact\_node(state: AgentState, llm) \-\> AgentState:  
    messages \= state\["messages"\]  
      
    \# Extract only the conversation history, strictly preserving the newest N messages  
    history\_to\_compress \= messages\[:-10\]   
    recent\_messages \= messages\[-10:\]  
      
    \# Replicate the Claude Code prompt rules exactly to prevent context laundering failures  
    compaction\_prompt \= """  
    You are an internal system routine optimizing context.  
    Summarize the following interaction history.   
    CRITICAL INSTRUCTIONS:  
    1\. Preserve all architectural decisions and exact code patterns.  
    2\. Pay special attention to and explicitly preserve specific user feedback.  
    3\. Do not summarize HumanMessages; extract their core intent faithfully.  
    """  
      
    \# Call the LLM to generate the dense summary  
    summary\_response \= llm.invoke()  
      
    \# Create the collapsed state. We instruct the reducer to remove all old messages  
    delete\_commands \=  
      
    \# Inject the continuity directive identical to Claude Code  
    new\_summary\_msg \= SystemMessage(  
        content=f"PREVIOUS CONTEXT SUMMARY:\\n{summary\_response.content}\\n\\n"  
                f"SYSTEM DIRECTIVE: Please continue the conversation from where we "  
                f"left it off without asking the user any further questions."  
    )  
      
    return {  
        "messages": delete\_commands \+ \[new\_summary\_msg\],  
        "context\_summary": summary\_response.content  
    }

### **3\. Subagent Handoff and Coordinator Mode**

To replicate Claude Code's "Coordinator Mode" and its heavy reliance on subagents for deep investigative tasks 9, we implement the LangGraph Supervisor pattern.33 In this advanced architecture, the primary agent does not execute high-token file searches directly. Instead, it utilizes a conditional tool to hand off the task to a specialized research graph.33

The critical engineering challenge here is preventing state loss and ensuring that the subagent's internal reasoning and massive file-reading trajectories do not pollute the parent state upon return.34 This requires a meticulous mapping of state updates via the Command structure.

Python

from langgraph.prebuilt import create\_react\_agent  
from langchain\_core.messages import Command

\# Define the specialized subagent with its own fully isolated AgentState  
research\_agent \= create\_react\_agent(  
    model=llm\_haiku, \# Utilizing a cheaper model as per Claude Code best practices  
    tools=\[file\_search, read\_file, grep\_codebase\],  
    state\_modifier="You are a research subagent. Investigate the codebase deeply and return a concise summary of your specific findings."  
)

\# Define the orchestration tool the supervisor uses to spawn the subagent  
def delegate\_to\_researcher(state: AgentState, query: str) \-\> Command:  
    \# The subagent executes sequentially in its own completely isolated context environment  
    subagent\_result \= research\_agent.invoke({"messages": \[HumanMessage(content=query)\]})  
      
    \# Extract ONLY the final summary payload from the subagent's execution trajectory  
    final\_summary \= subagent\_result\["messages"\]\[-1\].content  
      
    \# Return the summary securely to the supervisor's state, strictly isolating the parent  
    \# from the tens of thousands of tokens consumed during the research phase.  
    return Command(  
        update={  
            "messages":\[-1\].tool\_calls\["id"\]  
                )  
            \]  
        }  
    )

This precise implementation mirrors Anthropic's multi-agent methodology exactly: the subagent expands dynamically to consume heavy context loads in total isolation and then collapses back into a dense, low-token summary for the parent supervisor.4

### **4\. Background Memory Consolidation (The Kairos / AutoDream Pattern)**

To build a system analogous to the unreleased Kairos daemon and its autoDream memory consolidation pipeline 8, LangGraph's architecture must be extended beyond simple synchronous user requests. This involves establishing a separate, chron-triggered LangGraph workflow that operates entirely out-of-band but accesses the exact same persistent Checkpointer used by the main application.29

When the system metrics detect extended user idle time, this background graph is invoked.8 It extracts the raw AgentState from the checkpointer across multiple recent threads, executes time-based pruning 36, scans for logical contradictions or unverified assumptions across multiple session trajectories, and synthesizes them into a structured MEMORY.md file or a dedicated vector index.8

Crucially, in strict adherence to the "skeptical memory" philosophy 15, the system prompt dynamically injected into the primary agent when it finally resumes must define this specific memory store not as absolute ground truth, but merely as an index of contextual hints requiring real-time verification before execution.20 By utilizing time-based pruning algorithms—such as current\_time \- timedelta(days=7) to drop heavily outdated state artifacts 36—the daemon ensures the active agent is never burdened by historic bloat.

## **Error Handling and API Boundaries Implementation**

To ensure the LangGraph application survives the same API turbulence that Claude Code manages through its withhold and recover patterns 17, engineers must wrap the LLM execution nodes in robust retry logic.

If the LangChain invocation throws a max\_tokens error, indicating the reasoning block exceeded limits, the error handling node must not terminate the graph. Instead, it must capture the partial string output, append it to the context, and recursively invoke the LLM to continue generation—up to a defined MAX\_OUTPUT\_TOKENS\_RECOVERY\_LIMIT, precisely replicating Anthropic's strategy to protect the user's session.17 Similarly, encountering a prompt\_too\_long error must trigger a conditional graph edge that forcibly routes the state to the autocompact\_node prior to attempting any retries.17

## **Strategic Synthesis and Architectural Directives**

The inadvertent exposure of Claude Code's inner workings via the npm source map leak provides an authoritative, unprecedented map of the current frontier in enterprise AI agent engineering.6 The transition from basic conversational wrappers to highly reliable, autonomous systems is defined not merely by the raw reasoning power of the underlying large language model, but almost entirely by the sophistication of the orchestrating harness that manages it.11 The leak unequivocally reveals that mitigating context rot and managing window overflow requires a total departure from naive Retrieval-Augmented Generation and passive memory accumulation.1

The fundamental insights drawn from this architecture dictate three primary, critical recommendations for the design of future multi-agent systems:

1. **Tiered and Deterministic Compaction Systems:** Context management cannot be left to simplistic token truncation or blind string splicing. Systems must implement a highly deterministic cascade of interventions—strictly budgeting tool outputs at the character level 5, selectively microcompacting low-value execution data while respecting dynamic thresholds 5, collapsing mid-conversation verbosity into reversible artifacts 11, and finally relying on carefully prompted, multi-shot autocompaction.5 However, security engineers must remain perpetually vigilant against the inverted threat models introduced by autocompaction, where cooperative summarization models inadvertently launder weaponized context and execute poisoned directives.5  
2. **Strict Context Isolation via Subagents:** Long-running investigative, analytical, or operational tasks fundamentally conflict with maintaining a clean, highly focused reasoning state. The primary conversational agent must act exclusively as a high-level supervisor, aggressively offloading token-heavy file operations to fully isolated worker subagents that return only highly compressed, metadata-rich semantic summaries.9  
3. **Skeptical, Asynchronous Memory:** The shift toward always-on daemon modes (Kairos) necessitates sophisticated background garbage collection (autoDream) to manage the immense data exhaust generated by continuous operation.8 However, the most critical design pattern revealed is the adoption of skeptical memory architectures.21 By strictly enforcing that an agent treats its own historical data as a mere hint requiring active, real-time verification against the live environment 15, the system drastically minimizes hallucination rates and maintains structural resilience in rapidly mutating codebases.

By strategically leveraging the LangGraph framework to rigorously implement these principles—utilizing custom state reducers, dynamically routed parallel subagents, precise token-budgeting middleware, and out-of-band background consolidation—organizations can successfully construct robust, highly autonomous AI agents that operate reliably over extended, continuous sessions without succumbing to the inevitable, progressive degradation of context rot.

#### **Bibliografia**

1. Effective context engineering for AI agents \\ Anthropic, accesso eseguito il giorno aprile 2, 2026, [https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)  
2. Context windows \- Claude API Docs, accesso eseguito il giorno aprile 2, 2026, [https://platform.claude.com/docs/en/build-with-claude/context-windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)  
3. Context Rot: Why LLMs Degrade as Context Grows (Complete Guide) \- Morph, accesso eseguito il giorno aprile 2, 2026, [https://morphllm.com/context-rot](https://morphllm.com/context-rot)  
4. Context Rot in Claude Code: How to Fix It With Automatic, accesso eseguito il giorno aprile 2, 2026, [https://vincentvandeth.nl/blog/context-rot-claude-code-automatic-rotation](https://vincentvandeth.nl/blog/context-rot-claude-code-automatic-rotation)  
5. Claude Code Source Leak: With Great Agency Comes Great Responsibility \- Straiker, accesso eseguito il giorno aprile 2, 2026, [https://www.straiker.ai/blog/claude-code-source-leak-with-great-agency-comes-great-responsibility](https://www.straiker.ai/blog/claude-code-source-leak-with-great-agency-comes-great-responsibility)  
6. Claude Code Source Deep Dive (Part 1): Architecture & Startup Flow : r/ClaudeAI \- Reddit, accesso eseguito il giorno aprile 2, 2026, [https://www.reddit.com/r/ClaudeAI/comments/1sa6ih3/claude\_code\_source\_deep\_dive\_part\_1\_architecture/](https://www.reddit.com/r/ClaudeAI/comments/1sa6ih3/claude_code_source_deep_dive_part_1_architecture/)  
7. Claude Code's Entire Source Code Got Leaked via a Sourcemap in npm, Let's Talk About it, accesso eseguito il giorno aprile 2, 2026, [https://kuber.studio/blog/AI/Claude-Code's-Entire-Source-Code-Got-Leaked-via-a-Sourcemap-in-npm,-Let's-Talk-About-it](https://kuber.studio/blog/AI/Claude-Code's-Entire-Source-Code-Got-Leaked-via-a-Sourcemap-in-npm,-Let's-Talk-About-it)  
8. Inside Claude Code's leaked source: swarms, daemons, and 44 features Anthropic kept behind flags, accesso eseguito il giorno aprile 2, 2026, [https://thenewstack.io/claude-code-source-leak/](https://thenewstack.io/claude-code-source-leak/)  
9. Best Practices for Claude Code \- Claude Code Docs, accesso eseguito il giorno aprile 2, 2026, [https://code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)  
10. Introducing advanced tool use on the Claude Developer Platform \- Anthropic, accesso eseguito il giorno aprile 2, 2026, [https://www.anthropic.com/engineering/advanced-tool-use](https://www.anthropic.com/engineering/advanced-tool-use)  
11. Inside the Claude Code source · GitHub, accesso eseguito il giorno aprile 2, 2026, [https://gist.github.com/Haseeb-Qureshi/d0dc36844c19d26303ce09b42e7188c1](https://gist.github.com/Haseeb-Qureshi/d0dc36844c19d26303ce09b42e7188c1)  
12. $340 billion Anthropic that wiped trillions from stock market worldwide has source code of its most-important tool leaked on internet, accesso eseguito il giorno aprile 2, 2026, [https://timesofindia.indiatimes.com/technology/tech-news/340-billion-anthropic-that-wiped-trillions-from-stock-market-worldwide-has-source-code-of-its-most-important-tool-leaked-on-internet/articleshow/129925824.cms](https://timesofindia.indiatimes.com/technology/tech-news/340-billion-anthropic-that-wiped-trillions-from-stock-market-worldwide-has-source-code-of-its-most-important-tool-leaked-on-internet/articleshow/129925824.cms)  
13. Found the hidden pet system in the Claude Code leak — it's a full gacha with shinies : r/ClaudeAI \- Reddit, accesso eseguito il giorno aprile 2, 2026, [https://www.reddit.com/r/ClaudeAI/comments/1s9hqu3/found\_the\_hidden\_pet\_system\_in\_the\_claude\_code/](https://www.reddit.com/r/ClaudeAI/comments/1s9hqu3/found_the_hidden_pet_system_in_the_claude_code/)  
14. openclaw-grafana-lens 0.3.0 on npm \- Libraries.io \- security & maintenance data for open source software, accesso eseguito il giorno aprile 2, 2026, [https://libraries.io/npm/openclaw-grafana-lens](https://libraries.io/npm/openclaw-grafana-lens)  
15. What Claude Code's Source Leak Actually Reveals | by Marc Bara | Mar, 2026 | Medium, accesso eseguito il giorno aprile 2, 2026, [https://medium.com/@marc.bara.iniesta/what-claude-codes-source-leak-actually-reveals-e571188ecb81](https://medium.com/@marc.bara.iniesta/what-claude-codes-source-leak-actually-reveals-e571188ecb81)  
16. Beware of this system prompt that is automatically injected into Claude Code after every compaction: "Please continue the conversation from where we left it off without asking the user any further questions. Continue with the last task that you were asked to work on." : r/ClaudeAI \- Reddit, accesso eseguito il giorno aprile 2, 2026, [https://www.reddit.com/r/ClaudeAI/comments/1piny6t/beware\_of\_this\_system\_prompt\_that\_is/](https://www.reddit.com/r/ClaudeAI/comments/1piny6t/beware_of_this_system_prompt_that_is/)  
17. ByteBurst \#8: Three Agents, Three Philosophies | by Yuri Trukhin | Mar, 2026 \- Medium, accesso eseguito il giorno aprile 2, 2026, [https://medium.com/trukhinyuri/byteburst-8-three-agents-three-philosophies-1d88af1882b7](https://medium.com/trukhinyuri/byteburst-8-three-agents-three-philosophies-1d88af1882b7)  
18. Prompt caching \- Claude API Docs, accesso eseguito il giorno aprile 2, 2026, [https://platform.claude.com/docs/en/build-with-claude/prompt-caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)  
19. Prompt caching for faster model inference \- Amazon Bedrock \- AWS Documentation, accesso eseguito il giorno aprile 2, 2026, [https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)  
20. Anthropic accidentally leaks Claude Code, accesso eseguito il giorno aprile 2, 2026, [https://securityaffairs.com/190229/data-breach/anthropic-accidentally-leaks-claude-code.html](https://securityaffairs.com/190229/data-breach/anthropic-accidentally-leaks-claude-code.html)  
21. The Claude Code leak accidentally published the first complete blueprint for production AI agents. Here's what it tells us about where this is all going. : r/artificial \- Reddit, accesso eseguito il giorno aprile 2, 2026, [https://www.reddit.com/r/artificial/comments/1s9jprb/the\_claude\_code\_leak\_accidentally\_published\_the/](https://www.reddit.com/r/artificial/comments/1s9jprb/the_claude_code_leak_accidentally_published_the/)  
22. Claude Code's source code appears to have leaked: here's what we know | VentureBeat, accesso eseguito il giorno aprile 2, 2026, [https://venturebeat.com/technology/claude-codes-source-code-appears-to-have-leaked-heres-what-we-know](https://venturebeat.com/technology/claude-codes-source-code-appears-to-have-leaked-heres-what-we-know)  
23. How Claude Code works \- Claude Code Docs, accesso eseguito il giorno aprile 2, 2026, [https://code.claude.com/docs/en/how-claude-code-works](https://code.claude.com/docs/en/how-claude-code-works)  
24. The Claude Code Leak Exposed 44 Features Nobody Was Supposed to See \- YouTube, accesso eseguito il giorno aprile 2, 2026, [https://m.youtube.com/watch?v=y2cr1bRTcgc](https://m.youtube.com/watch?v=y2cr1bRTcgc)  
25. LangGraph Multi-Agent Systems: Complete Tutorial & Examples \- Latenode Blog, accesso eseguito il giorno aprile 2, 2026, [https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-systems-complete-tutorial-examples](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-systems-complete-tutorial-examples)  
26. Workflows and agents \- Docs by LangChain, accesso eseguito il giorno aprile 2, 2026, [https://docs.langchain.com/oss/python/langgraph/workflows-agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)  
27. Building multi-agent systems with LangGraph \- CWAN, accesso eseguito il giorno aprile 2, 2026, [https://cwan.com/resources/blog/building-multi-agent-systems-with-langgraph/](https://cwan.com/resources/blog/building-multi-agent-systems-with-langgraph/)  
28. Short-term memory \- Docs by LangChain, accesso eseguito il giorno aprile 2, 2026, [https://docs.langchain.com/oss/javascript/langchain/short-term-memory](https://docs.langchain.com/oss/javascript/langchain/short-term-memory)  
29. Short-term memory \- Docs by LangChain, accesso eseguito il giorno aprile 2, 2026, [https://docs.langchain.com/oss/python/langchain/short-term-memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)  
30. LangGraph Tutorial: Message History Management with Sliding Windows \- Unit 1.2 Exercise 3 \- AI Product Engineer, accesso eseguito il giorno aprile 2, 2026, [https://aiproduct.engineer/tutorials/langgraph-tutorial-message-history-management-with-sliding-windows-unit-12-exercise-3](https://aiproduct.engineer/tutorials/langgraph-tutorial-message-history-management-with-sliding-windows-unit-12-exercise-3)  
31. Langgraph memory or chat history summarisation. : r/AI\_Agents \- Reddit, accesso eseguito il giorno aprile 2, 2026, [https://www.reddit.com/r/AI\_Agents/comments/1q2m0iw/langgraph\_memory\_or\_chat\_history\_summarisation/](https://www.reddit.com/r/AI_Agents/comments/1q2m0iw/langgraph_memory_or_chat_history_summarisation/)  
32. Context Engineering \- LangChain Blog, accesso eseguito il giorno aprile 2, 2026, [https://blog.langchain.com/context-engineering-for-agents/](https://blog.langchain.com/context-engineering-for-agents/)  
33. Hierarchical multi-agent systems with LangGraph \- YouTube, accesso eseguito il giorno aprile 2, 2026, [https://www.youtube.com/watch?v=B\_0TNuYi56w](https://www.youtube.com/watch?v=B_0TNuYi56w)  
34. Multi-Agent Conversational Graph Designs : r/LangChain \- Reddit, accesso eseguito il giorno aprile 2, 2026, [https://www.reddit.com/r/LangChain/comments/1dogdy8/multiagent\_conversational\_graph\_designs/](https://www.reddit.com/r/LangChain/comments/1dogdy8/multiagent_conversational_graph_designs/)  
35. State Loss in Hierarchical Multi-Agent System with Deep Agents and Custom AgentState \- LangGraph \- LangChain Forum, accesso eseguito il giorno aprile 2, 2026, [https://forum.langchain.com/t/state-loss-in-hierarchical-multi-agent-system-with-deep-agents-and-custom-agentstate/2592](https://forum.langchain.com/t/state-loss-in-hierarchical-multi-agent-system-with-deep-agents-and-custom-agentstate/2592)  
36. Advanced Techniques in LangGraph: Tips for Using Message Deletion in Graph Structure Applications \- DEV Community, accesso eseguito il giorno aprile 2, 2026, [https://dev.to/jamesli/advanced-techniques-in-langgraph-tips-for-using-message-deletion-in-graph-structure-applications-43b6](https://dev.to/jamesli/advanced-techniques-in-langgraph-tips-for-using-message-deletion-in-graph-structure-applications-43b6)