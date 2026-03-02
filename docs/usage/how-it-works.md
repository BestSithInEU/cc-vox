# How It Works

cc-vox is a Claude Code plugin that uses the **hook system** to inject voice feedback into every conversation turn. The entire pipeline is hands-free — once installed, Claude automatically includes voice summaries.

## The Pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant C as Claude Code
    participant H1 as UserPromptSubmit Hook
    participant H2 as PostToolUse Hook
    participant H3 as Stop Hook
    participant S as scripts/say
    participant T as TTS Backend

    U->>C: Types a message
    C->>H1: Hook fires
    H1-->>C: Injects 📢 reminder into system prompt
    C->>C: Claude generates response
    Note over C: Includes 📢 summary at end

    opt If tools are used
        C->>H2: After each tool call
        H2-->>C: Brief reminder to keep 📢 in mind
    end

    C->>H3: Response complete (Stop event)
    H3->>H3: Extract 📢 marker from response

    alt 📢 marker found
        H3->>S: Speak marker text
    else Response is short
        H3->>S: Speak response directly
    else Long response, no marker
        H3->>H3: Call headless Claude for summary
        H3->>S: Speak generated summary
    else Last resort
        H3->>S: Speak truncated response
    end

    S->>S: Select backend & acquire lock
    S->>T: Generate audio
    T-->>S: WAV audio data
    S->>S: Play audio
```

## The Three Hooks

### 1. UserPromptSubmit — Inject Reminder

**When:** Every time the user sends a message.

The hook reads `~/.claude/cc-vox.toml` and injects a system message telling Claude to include a `📢` voice summary at the end of its response. This reminder includes:

- The max word limit for summaries
- Style instructions (match user's tone, avoid technical identifiers)
- Any custom personality prompt

### 2. PostToolUse — Brief Nudge

**When:** After each tool call (file reads, edits, bash commands, etc.).

In long tool-heavy responses, Claude can lose track of the voice summary instruction. This hook injects a brief reminder to keep the `📢` summary in mind.

### 3. Stop — Extract & Speak

**When:** Claude finishes its response.

This hook runs the 4-strategy summarization cascade:

| Strategy | Speed | When |
|:---------|:------|:-----|
| **1. Extract `📢` marker** | Instant | Claude included a `📢` line |
| **2. Speak directly** | Instant | Response is short enough (<=`max_words`) |
| **3. Headless Claude** | ~3--5s | Calls `claude -p` to generate a summary |
| **4. Truncate** | Instant | Last resort — truncate the response |

The summary is passed to `scripts/say`, which selects a TTS backend, generates audio, and plays it.

## Audio Playback

The `say` script handles:

1. **Backend selection** — auto-detect or forced, with fallback
2. **Playback locking** — file-based mutex prevents overlapping audio
3. **Audio player detection** — prefers `ffplay` (streaming), falls back to `aplay`, `paplay`, or `afplay`
4. **Session state** — sentinel files in `/tmp/` so the stop hook knows TTS status
