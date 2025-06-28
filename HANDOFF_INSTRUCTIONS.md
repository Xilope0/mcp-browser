# Claude Memory (cmem) Handoff System Guide

## Overview

The `cmem` (Claude Memory) handoff system enables seamless AI assistant transitions by providing persistent memory and context across sessions. This is critical for long-running projects where different AI instances need to understand previous work and continue development effectively.

## Core Concepts

### 1. Session-Based Memory
- **Sessions**: Each AI work session is tracked with timestamps and outcomes
- **Auto-rotation**: Sessions automatically rotate after 4 hours to maintain context freshness
- **Session Names**: Descriptive names like "Morning Development", "Late Night Development"

### 2. Structured Knowledge Types
- **Tasks**: Open, in-progress, and completed work items with priorities and assignees
- **Decisions**: Important choices with reasoning and alternatives considered
- **Patterns**: Recurring insights or learnings with effectiveness tracking
- **Knowledge**: Categorized information storage for facts and discoveries

### 3. Handoff Context
The handoff system provides incoming AIs with:
- Current session status and duration
- Active/pending tasks requiring attention  
- Recent decisions that affect current work
- High-priority patterns that influence approach
- Project intelligence metrics

## Using the Handoff System

### For Incoming AI Assistants

**Step 1: Get Handoff Summary**
```bash
cmem handoff
```
This provides a markdown summary optimized for AI consumption with:
- Current session context
- Active tasks requiring attention  
- Recent decisions influencing work
- Key patterns to apply
- Project statistics

**Step 2: Get Detailed Context** 
```bash
cmem context
```
This provides JSON data with complete structured information:
- Full task details with IDs and metadata
- Complete decision history with alternatives
- Pattern effectiveness and frequency data
- Session tracking information

**Step 3: Continue or Start New Session**
Based on handoff information:
- If session < 4 hours old: Continue current session
- If session > 4 hours old: Auto-rotation will start new session
- Use `cmem session start "New Session Name"` for manual session creation

### For Outgoing AI Assistants

**Before Ending Work:**
1. **Complete Tasks**: Update any finished work
   ```bash
   cmem task complete <task-id>
   ```

2. **Record Decisions**: Document important choices made
   ```bash
   cmem decision "Decision" "Reasoning" "Alternative1,Alternative2"
   ```

3. **Add Patterns**: Capture learnings for future AIs
   ```bash
   cmem pattern add "Pattern Name" "Description" --priority high
   ```

4. **Update Knowledge**: Store important discoveries
   ```bash
   cmem knowledge add "key" "value" --category "category"
   ```

5. **End Session** (optional):
   ```bash
   cmem session end "Outcome description"
   ```

## Integration with MCP Browser

The MCP Browser memory server automatically syncs with cmem when available:

### Automatic Sync
- **Task Operations**: Adding, updating, completing tasks sync to cmem
- **Pattern Creation**: New patterns are automatically added to cmem  
- **Decision Recording**: Decisions made through MCP are stored in cmem
- **Identity-Based Storage**: Each identity gets separate memory space

### Identity System
```bash
# Use onboarding tool with identity-specific instructions
onboarding identity="ProjectName" instructions="Focus on code quality"

# Memory server uses identity for separate storage
# cmem integration syncs under that identity context
```

### Bidirectional Flow
1. **MCP → cmem**: Tool operations automatically sync to persistent storage
2. **cmem → MCP**: Memory server can read cmem data for context
3. **Cross-Session**: Patterns and decisions persist across AI instances

## Handoff Data Structure

### Session Information
```json
{
  "session": {
    "id": "2025-06-28-morning-development",
    "name": "Morning Development", 
    "startTime": "2025-06-28T09:31:17.858Z",
    "status": "active"
  }
}
```

### Task Structure
```json
{
  "id": "43801be2",
  "description": "Task description",
  "priority": "high|medium|low",
  "status": "open|in_progress|completed",
  "assignee": "assignee_name",
  "createdAt": "2025-06-26T02:59:51.654Z"
}
```

### Decision Structure  
```json
{
  "id": "793cbd6e",
  "decision": "Decision made",
  "reasoning": "Why this was chosen",
  "alternatives": ["Alt 1", "Alt 2"],
  "timestamp": "2025-06-26T14:48:36.187Z"
}
```

### Pattern Structure
```json
{
  "id": "03c8e07c", 
  "pattern": "Pattern Name",
  "description": "Detailed description",
  "priority": "high|medium|low",
  "effectiveness": 0.8,
  "frequency": 5
}
```

## Best Practices for AI Handoffs

### 1. **Read Before Acting**
Always check handoff information before starting work:
```bash
# Quick check
cmem handoff

# Detailed context for complex work
cmem context
```

### 2. **Maintain Context Continuity**
- Continue existing sessions when < 4 hours old
- Reference previous decisions in new work
- Apply high-priority patterns to current tasks
- Use established assignee names for consistency

### 3. **Document Decisions**
Record ANY significant choice:
- Technology selections
- Architecture decisions  
- Approach changes
- Problem-solving strategies

### 4. **Pattern Recognition**
Capture insights that will help future AIs:
- Recurring problems and solutions
- Effective approaches
- Things to avoid
- Meta-patterns about the development process

### 5. **Task Management**
- Break large work into trackable tasks
- Update status as work progresses
- Complete tasks when finished
- Create new tasks for discovered work

## Example Handoff Workflow

### Incoming AI Workflow
```bash
# 1. Get handoff summary
cmem handoff

# 2. Check specific task details
cmem task list

# 3. Review recent patterns
cmem pattern list --priority high

# 4. Start work based on active tasks
# ... do work ...

# 5. Update progress
cmem task update <task-id> in_progress
```

### Outgoing AI Workflow  
```bash
# 1. Complete finished tasks
cmem task complete <task-id>

# 2. Document decisions made
cmem decision "Use Docker for Firecrawl" "Simpler deployment" "Native install,VM"

# 3. Add learning patterns
cmem pattern add "Test all new features" "Always add tests before committing" --priority high

# 4. Create tasks for remaining work
cmem task add "Fix failing tests" --priority high --assignee next-ai

# 5. End session with outcome
cmem session end "Completed MCP browser enhancements with tests"
```

## Integration with Development Workflow

### Pre-Commit Checklist
- [ ] All tasks updated with current status
- [ ] New decisions documented with reasoning  
- [ ] Patterns captured from development process
- [ ] Knowledge updated with discoveries
- [ ] Next tasks created for continuation

### Session Management
- **Short sessions (< 1 hour)**: Continue existing session
- **Medium sessions (1-4 hours)**: Continue or start new based on context
- **Long sessions (> 4 hours)**: Auto-rotation creates new session

### Cross-Project Context
- Use identity parameter for project-specific contexts
- Different projects maintain separate memory spaces
- Patterns can be shared across projects when relevant

## Error Handling

### When cmem is Unavailable
- MCP memory server gracefully degrades to local storage
- Sync attempts fail silently without breaking functionality
- Manual sync possible when cmem becomes available

### Memory Conflicts
- Sessions auto-rotate to prevent conflicts
- Task IDs are unique across sessions
- Patterns merge based on similarity detection

This handoff system ensures smooth AI transitions and maintains project continuity across multiple development sessions.