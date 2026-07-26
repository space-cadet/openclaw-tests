---
name: mb-init
description: Initialize a memory bank for a new or existing project following the v6.12 protocol. Use when starting work on a project that lacks memory-bank documentation, or when creating a new project that needs task tracking. Creates the full memory-bank directory structure, initial files, and optionally a task file for the first piece of work.
---

# Memory Bank Initialization Skill (v6.12)

## Overview

This skill bootstraps a complete memory-bank documentation system for any project. It creates the directory structure, initial files, and optionally a first task file — everything needed to start tracking work with the mb-text-workflow or mb-db-workflow skills.

## When to Use

- Starting a **new project** that needs task tracking
- Adopting memory-bank documentation on an **existing project** that lacks it
- Creating a **fork/adaptation** of the memory-bank system for a specific project type

## Prerequisites

1. Determine the **project root directory** (absolute path)
2. Determine the **project name** and **purpose**
3. Decide if this project uses **text-based** (markdown) or **DB-native** workflow
4. Know the current time and timezone
5. Ensure `mb-cli` is installed (run `mb --version` to check)

## Workflow

### Step 1: Initialize with `mb-cli` (Recommended)

The `mb-cli` tool creates the entire memory-bank scaffold — files, templates, and database structure — in one command.

```bash
cd <project-root>
mb init
```

This creates:
- Core files (`tasks.md`, `session_cache.md`, `activeContext.md`, etc.)
- Template files in `memory-bank/templates/`
- SQLite database (for DB-native workflow)
- Directory structure (`tasks/`, `sessions/`, `edits/`, `implementation-details/`)

Options:
- `mb init --dry-run` — Preview what would be created
- `mb init --core` — Only core files (skip templates, DB, viewer)
- `mb init --full` — Reinitialize everything (overwrite existing)
- `mb init --interactive` — Step-by-step interactive setup

### Step 2: Manual Verification (If `mb-cli` is unavailable)

If `mb-cli` is not installed, create the structure manually:

#### Create Directory Structure
```bash
cd <project-root>
mkdir -p memory-bank/{tasks,sessions,edits/$(date +%Y-%m-%d),implementation-details}
```

#### Create Core Files

##### memory-bank/tasks.md
```markdown
# Memory Bank — <Project Name>

*Created: YYYY-MM-DD HH:MM:SS TZ*
*Last Updated: YYYY-MM-DD HH:MM:SS TZ*

## Overview

[Brief description of the project and what this memory bank tracks]

## Active Tasks

| ID | Title | Status | Priority | Started | Dependencies | Details |
|----|-------|--------|----------|---------|--------------|---------|

## Completed Tasks

| ID | Title | Status | Priority | Started | Completed | Dependencies | Details |
|----|-------|--------|----------|---------|-----------|--------------|---------|

## Status Summary

- **Active**: 0
- **Completed**: 0
- **Paused**: 0
- **Total**: 0
```

#### memory-bank/session_cache.md
```markdown
# Session Cache

*Created: YYYY-MM-DD HH:MM:SS TZ*
*Last Updated: YYYY-MM-DD HH:MM:SS TZ*

## Current Session
**Started**: YYYY-MM-DD HH:MM:SS TZ
**Focus Task**: None
**Session File**: None
**Status**: 🔄 No active session

## Overview
- Active: 0 | Paused: 0 | Completed: 0
- Last Session: -
- Current Period: <morning|afternoon|evening|night>

## Task Registry

## Active Tasks

## Session History (Last 5)

## System Status
- **Memory Bank**: 🔄 Initialized, no tasks yet
- **Project**: 🔄 Ready for work
```

#### memory-bank/activeContext.md
```markdown
# Active Context

*Last Updated: YYYY-MM-DD HH:MM:SS TZ*

## Current Tasks

## Completed Tasks (Recent)

## Next Steps

## System Status
```

#### memory-bank/edit_history.md
```markdown
# Edit History

*Created: YYYY-MM-DD HH:MM:SS TZ*
*Last Updated: YYYY-MM-DD HH:MM:SS TZ*

---

## YYYY-MM-DD

#### HH:MM:SS TZ - INIT: Memory bank initialized
- Created `memory-bank/tasks.md` - Task registry
- Created `memory-bank/session_cache.md` - Session tracking
- Created `memory-bank/activeContext.md` - Current context
- Created `memory-bank/edit_history.md` - Edit history (this file)
- Created `memory-bank/implementation-details/` - Knowledge layer directory
```

### Step 3: Create Optional Knowledge Layer Files

If the project has existing architecture or context worth capturing:

- `memory-bank/techContext.md` — Stack, dependencies, build system
- `memory-bank/productContext.md` — Goals, user stories, features
- `memory-bank/systemPatterns.md` — Conventions, patterns, standards
- `memory-bank/changelog.md` — Feature/release tracking
- `memory-bank/errorLog.md` — Known issues and fixes

### Step 4: Create First Task (Optional)

If there's immediate work to track:

```bash
# Create task file
cat > memory-bank/tasks/T1.md << 'EOF'
# T1: [Title]

*Created: YYYY-MM-DD HH:MM:SS TZ*
*Last Updated: YYYY-MM-DD HH:MM:SS TZ*

**Status**: 🔄 **IN PROGRESS**
**Priority**: HIGH

## Details
[Brief description]

## Progress
1. 🔄 [Current item]
2. ⬜ [Next item]

## Files
EOF

# Update tasks.md registry
# (prepend T1 to Active Tasks table)
```

### Step 5: Commit Initialization

```bash
git add memory-bank/
git commit -m "(docs)INIT: Initialize memory bank — v6.12 protocol, task tracking ready"
```

## Post-Initialization

After initialization, use **mb-cli** for updates whenever possible:

- `mb update` — Record work and regenerate markdown files (DB-native workflow)
- `mb workflow` — Session work recording with automatic regeneration
- `mb task` — Task management (create, update, close tasks)
- `mb session` — Session management

For text-based projects without the database, use **mb-text-workflow** or create edit chunks manually:

1. Create edit chunks in `memory-bank/edits/YYYY-MM-DD/`
2. Update task files in `memory-bank/tasks/`
3. Regenerate `memory-bank/edit_history.md`
4. Commit with format: `(type)TID: Headline - Details`

## Project-Specific Adaptations

For different project types, customize:

**Research projects:**
- Add `papers/` directory in implementation-details
- Track literature review progress in tasks

**Web/apps:**
- Add `api-endpoints.md`, `ui-components.md`
- Track feature phases (MVP, v2, etc.)

**DevOps/infrastructure:**
- Add `deployment.md`, `monitoring.md`
- Track environment parity

## Anti-Patterns

- NEVER initialize a memory bank inside another project's memory-bank directory
- NEVER use relative paths or tildes in file references
- NEVER skip the edit_history.md — it's the audit trail
- NEVER commit generated views (edit_history.md) without their source chunks

## References

- [mb-text-workflow](SKILL.md) — For text-based projects
- [mb-db-workflow](SKILL.md) — For DB-native projects
- [v6.12 Full Rules](references/integrated-rules-v6.12.md)
