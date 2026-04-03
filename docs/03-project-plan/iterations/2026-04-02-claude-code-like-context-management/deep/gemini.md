Claude Code appears to use a **layered context-management stack** rather than a single “summarize when full” trick: persistent instruction files and auto-memory for stable long-term state, selective loading for relevance, pruning/clearing of bulky transient context, and compaction/summarization when the active transcript gets too large. Anthropic’s official docs explicitly describe server-side context editing, SDK compaction, startup memory loading, path-scoped rules, and re-injection of `CLAUDE.md` after compaction, while public reporting on the leak and derivative analyses point to additional implementation patterns such as transcript pruning of old tool output and protecting a recent token band from pruning. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

## Architecture

At the official product level, Anthropic describes Claude Code as an “agentic harness” around the model that provides tools, context management, and execution environment, which strongly suggests context is managed by the runtime, not left to the model prompt alone. Each session starts with a fresh context window, and durable knowledge is brought back through two memory systems: user-authored `CLAUDE.md` files and Claude-written auto memory, both injected as context at session start rather than enforced as hard configuration. [code.claude](https://code.claude.com/docs/en/how-claude-code-works)

A key design point is that not all context is treated equally: project instructions, user preferences, and organization policy live in structured files, while transcript history and tool outputs are transient and therefore candidates for pruning or summarization. This separation is exactly the kind of anti-context-rot architecture you would want in LangGraph, because stable rules are externalized from the conversation stream and can be reloaded cleanly after compression events. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

## Persistent memory

`CLAUDE.md` is the main persistent instruction substrate. Claude Code loads `CLAUDE.md` from multiple scopes, including managed policy, project, and user locations, with more specific files taking precedence, and ancestor `CLAUDE.md` files above the working directory are loaded fully at launch. Claude also supports imports via `@path`, recursive expansion up to five hops, and `.claude/rules/` files so instructions can be modularized rather than stuffed into a single massive prompt. [code.claude](https://code.claude.com/docs/en/how-claude-code-works)

The important context-rot prevention mechanism here is **scoping**. Rules in `.claude/rules/` can be path-specific via YAML frontmatter, and those conditional rules load only when Claude is working with matching files, which reduces irrelevant instruction noise and keeps the active prompt semantically local to the files being touched. Anthropic also recommends keeping each `CLAUDE.md` under about 200 lines because larger instruction files consume context and reduce adherence, which is an explicit acknowledgement that excess static context degrades model behavior even before hard window overflow occurs. [code.claude](https://code.claude.com/docs/en/how-claude-code-works)

Auto memory is the second persistent layer. Claude stores project-specific memory under `~/.claude/projects/<project>/memory/`, with `MEMORY.md` as a compact index and optional topic files for detailed notes. Only the first 200 lines or first 25KB of `MEMORY.md` are loaded at startup, while deeper topic files are read on demand, which is effectively a hierarchical memory design with a hot index and cold storage. [code.claude](https://code.claude.com/docs/en/how-claude-code-works)

That hot/cold split matters technically. It prevents the system from carrying the full long-term memory corpus into every turn, while still making prior knowledge retrievable when needed through normal file reads. In LangGraph terms, this maps well to a short always-on memory summary node plus lazy retrieval nodes for detailed memory documents. [code.claude](https://code.claude.com/docs/en/how-claude-code-works)

## Transcript control

Anthropic’s official API docs now expose two major transcript-management strategies: server-side context editing and client-side compaction. For server-side editing, `clear_tool_uses_20250919` removes older tool results once input crosses a configured threshold, preserving only a recent number of tool interactions and optionally clearing tool inputs too; the API replaces removed content with placeholders so the model knows something existed but no longer has the payload. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

That placeholder pattern is significant. It preserves **structural continuity** without preserving full token mass, which is a strong defense against context rot because the model retains the shape of prior activity without being distracted by obsolete file dumps or search outputs. The docs also support exclusions for specific tools and a `clear_at_least` threshold so cache invalidation is only incurred when enough context is actually reclaimed, which shows the system is balancing context hygiene with prompt-cache economics. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

For thinking traces, `clear_thinking_20251015` keeps only the last \(N\) assistant turns with thinking by default, or all if you want to prioritize cache preservation. This implies Claude’s runtime distinguishes between user-visible conversational state, tool state, and internal reasoning state, and applies different retention rules to each category rather than compressing everything uniformly. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

Client-side compaction, available in the SDK tool runner, is the heavier fallback. Once token usage passes a threshold, the SDK injects a summary request, gets a structured summary wrapped in `<summary>` tags, and replaces the full history with that summary so work can continue from a compact state. Anthropic’s default summary schema includes task overview, current state, important discoveries, next steps, and preserved context, which is effectively a task-oriented continuation state machine rather than a generic prose recap. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

Official docs also state that `CLAUDE.md` survives `/compact` because it is re-read from disk and re-injected fresh after compaction. That is a subtle but crucial anti-rot mechanism: compaction does not have to faithfully preserve global rules in the summary, because stable rules are reconstructed from source-of-truth files after the transcript is reduced. [code.claude](https://code.claude.com/docs/en/how-claude-code-works)

## Leak-derived patterns

Public reporting on the March 2026 source-map exposure says the leaked Claude Code package revealed internal TypeScript sources including a large query engine responsible for streaming responses, token counting, retry logic, and recursive tool-call loops. While secondary reporting is not as authoritative as vendor docs, multiple public summaries derived from leak analysis describe an additional pruning layer separate from full compaction, where older tool outputs are replaced with placeholders while a recent protected region is kept intact. [lockllm](https://www.lockllm.com/blog/claude-code-leaks)

The recurring claim across those derivative analyses is a backward scan through tool outputs, with protection for roughly the most recent 40K tokens of tool content and pruning only when enough older material is reclaimable. Even if you treat exact constants cautiously, the design pattern is plausible and technically sound: keep a **recency-protected band** for near-term coherence, aggressively prune stale bulky tool payloads outside that band, and reserve summarization for when pruning alone is insufficient. [gist.github](https://gist.github.com/badlogic/cd2ef65b0697c4dbe2d13fbecb0a0a5f)

Another leak-aligned pattern appears in official SDK limitations: server-side tools can distort token accounting because `cache_read_input_tokens` may reflect internal tool-related API calls rather than true live context size. That suggests Claude Code likely needs its own internal notion of “effective context occupancy” rather than blindly trusting one token number, especially when deciding when to compact or prune. For a LangGraph replica, this argues for maintaining separate metrics for raw transcript tokens, retained visible tokens, tool-payload tokens, and cached or virtual tokens. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

A useful inference from the leak commentary plus official memory docs is that Claude Code treats transcript, tool results, and file-backed memory as **distinct storage classes** with different retention policies. That division is one of the main reasons it can avoid both context rot and overflow better than naïve “append every message forever” agent designs. [lockllm](https://www.lockllm.com/blog/claude-code-leaks)

## LangGraph design

A similar LangGraph system should have at least five state layers:

- **System/policy layer**: immutable orchestration prompt plus org/user/project instructions loaded from files each turn.
- **Working memory layer**: compact task state, goals, plan, decisions, open issues, and invariants.
- **Transient transcript layer**: recent conversational turns and tool-call skeletons.
- **Artifact layer**: large file reads, search results, diffs, logs, and command outputs stored outside the prompt.
- **Long-term memory layer**: indexed memory documents, summaries, and per-project notes retrievable on demand.

This design mirrors Claude Code’s documented separation between startup memory, rules, auto memory, tool results, and compacted transcript. In LangGraph, you would store bulky artifacts in an external store keyed by tool-call IDs, keep only short placeholders in graph state, and materialize full artifacts into prompt context only when a relevance policy says they are needed. [code.claude](https://code.claude.com/docs/en/how-claude-code-works)

A practical control loop would look like this:

1. Build prompt from system prompt, scoped rules, hot memory index, current task summary, and recent transcript.
2. Before each model call, estimate token load by category.
3. If tool payload budget is high, prune old tool results first, retaining placeholders.
4. If reasoning blocks are retained, trim them separately from user-visible transcript.
5. If total context still exceeds threshold, run task-state compaction into a structured continuation summary.
6. Rehydrate durable instructions from files after compaction, not from the summary alone.

That ordering closely follows Anthropic’s public prioritization of server-side clearing before client-side compaction, and its distinction between clearing tool results versus summarizing the whole conversation. It also preserves the most important anti-rot property: summaries capture operational state, while durable instructions are reloaded from authoritative sources. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

For the summary schema, copy Anthropic’s structure almost directly: task overview, current state, important discoveries, next steps, and context to preserve. In LangGraph, store that as structured JSON rather than plain markdown so downstream nodes can selectively inject only relevant fields, for example open blockers during debugging or architecture decisions during refactors. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

A good pruning policy would be:

- Always keep the last few user/assistant turns verbatim.
- Keep tool-call metadata longer than tool payloads.
- Keep recent tool payloads within a protected token band.
- Replace older payloads with typed placeholders such as `TOOL_RESULT_PRUNED(file_read, path=..., lines=...)`.
- Write durable insights to long-term memory before pruning.
- Compact only when pruning cannot recover enough space.

That policy is strongly supported by the official context-editing model for tool results, memory handoff before clearing, and summary-based continuation. It is also consistent with public leak-derived descriptions of separate pruning and compaction stages. [gist.github](https://gist.github.com/rmk40/cde7a98c1c90614a27478216cc01551f)

One final implementation detail from the docs is especially important: context management should be **observable**. Anthropic’s API returns `applied_edits` and counts of cleared tokens or turns, and the token-counting endpoint can preview post-edit token usage. In LangGraph, expose the same telemetry in state: current token load by bucket, pruning actions taken, memory writes performed, and compaction count per session. Without that instrumentation, you will not be able to tune thresholds or diagnose context rot reliably. [platform.claude](https://platform.claude.com/docs/en/build-with-claude/context-editing)

Would you like a concrete LangGraph architecture next, with nodes, state schema, reducers, and pseudocode for prune/compact/reload?