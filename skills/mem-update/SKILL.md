---
name: mem-update
description: Memory Bank Update Workflow — v6.12 compliant with project-repo awareness. Use when the user invokes $mem-update or asks for this workflow by name.
---

# mem-update (Sage Adaptation)

This skill is adapted from Deepak's Codex skill at `~/.agents/skills/mem-update/`. Key changes for Sage:
- **Step 0 added:** Project-repo awareness (check timesarrow/code repos before workspace)
- **Paths updated:** Point to `${MB_CORE_PATH}/` instead of Windsurf paths
- **Approval relaxed:** Location verification instead of explicit user approval
- **Cross-repo checks:** Prevents duplicate tasks across workspace and project repos

## Memory Bank Update Workflow (Enhanced v6.12 Compliance — Sage Adapted)

### Step 0: Identify Correct Memory Bank Location
- **Check if working on a project:** Before touching ANY memory-bank files, determine:
  - Is there an active project with its own memory-bank? (e.g., `timesarrow/memory-bank/`)
  - Is this workspace/infrastructure work? (e.g., `~/.openclaw/workspace/memory-bank/`)
- **Rule:** Project tasks → project memory-bank. Workspace tasks → workspace memory-bank.
- **Scan locations:**
  - `~/.openclaw/workspace/code/*/memory-bank/` (project repos)
  - `~/.openclaw/workspace/memory-bank/` (workspace)
  - `${MB_CORE_PATH}/` (mb-core repo for reference)

### Step 1: Read Memory Bank Update Protocol
- **First Action:** Read the memory bank update protocol from `${MB_CORE_PATH}/integrated-rules-v6.12.md` (Sections 1.5, 1.6, and 6.5)
- **Alternative:** If mb-core doesn't have it, check `memory-bank/integrated-rules-v6.12.md` in the target repo
- **Purpose:** Understand strict compliance requirements, file operation standards, and approval protocols
- **Critical:** Must read this before making any file modifications

### Step 2: Deep Memory Bank Scan
- **Comprehensive Scan:** Perform deep scan of ENTIRE memory bank structure across ALL relevant repos
- **Identify Related Content:**
  - All existing tasks in `memory-bank/tasks/` related to current work (check ALL project repos)
  - All sub-tasks and implementation details in `memory-bank/implementation-details/`
  - Relevant session files and cache entries
  - Current active context and task registry
- **Critical:** If a task exists in a project repo (e.g., timesarrow), DO NOT create it in workspace memory-bank
- **Analysis:** Determine relationships and dependencies between existing documentation

### Step 3: Verify Location Before Creating
- **Assessment:** Based on deep scan, determine if new tasks, sub-tasks, or implementation docs are needed
- **Location Check:** Before creating ANY new file, verify:
  1. Does this task already exist in another repo's memory-bank?
  2. Is this project work or workspace infrastructure work?
  3. What is the CORRECT memory-bank location?
- **If unsure:** Ask user for confirmation of correct location
- **Prevention:** Never create duplicate tasks across workspace and project repos

### Step 4: Initialize Context (Time & Timezone)
- **Get Current Time:** Determine current system time and timezone (IST format: `YYYY-MM-DD HH:MM:SS TZ`)
- **Verify Timestamp Standards:** Ensure compliance with v6.12 timestamp requirements
- **Prepare for Updates:** Have accurate timestamps ready for all file updates

### Step 5: Update Specific Files (Task/Implementation)
- **Template Compliance:** All file updates MUST follow the exact formats given in `${MB_CORE_PATH}/memory-bank/templates/` folder
- **Available Templates:** 
  - `task-template.md` for new task files
  - `tasks.md` for task registry
  - `session_cache.md` for session cache
  - `edit_history.md` for edit history
  - `activeContext.md` for active context
  - And other specialized templates as needed
- **Targeted Updates:** Update only the specific task files and implementation docs identified in Steps 0-2
- **Strict Rule:** Use `edit_block` (or equivalent) for updates. **Never** overwrite whole files unless creating new ones
- **Schema Compliance:** Follow v6.12 requirements AND template formats exactly
- **Cross-repo awareness:** When updating, check if linked files exist in the same repo. Don't link to files in other repos unless intentional.

### Step 6: Update Registries (Strict Schema Enforced)
- **`tasks.md`:** Update status/timestamps
  - *Constraint:* Must match `| ID | Title | Status | Priority | Started | Dependencies | Details |`
  - *Constraint:* Status must be `🔄`, `✅`, `⏸️`, or `❌`
  - *Constraint:* Details must be `[Details](tasks/Txx.md)`
- **`session_cache.md`:** Update active tasks/history

### Step 7: Update Session Log
- **Check for `sessions/YYYY-MM-DD-PERIOD.md`** in the target repo
- **If exists:** Update while **PRESERVING EXISTING CONTENT**. Append new work items
- **If new:** Create with standard header following v6.12 template

### Step 8: Update History (Strict Regex Compliance)
- **`edit_history.md`:** Prepend new entry
  - *Header:* `#### HH:MM:SS IST - TaskID: Description`
  - *Bullet:* `- Action `relative/path` - Description`
  - *Action:* `Created`, `Modified`, `Updated`, `Deleted`

### Step 9: Finalize
- **Generate Commit Message:** Create commit message per v6.12 format
- **Verify Compliance:** Ensure all updates follow strict v6.12 requirements
- **Document Completion:** Note workflow completion in appropriate logs
