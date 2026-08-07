# OpenClaw Tools

A public, shareable repository of OpenClaw skills, scripts, benchmarks, and utilities that any AI agent workspace can adopt.

## What This Is

- **Skills**: Sanitized, reusable OpenClaw skills (SKILL.md + scripts)
- **Scripts**: Generic shell/Python scripts for AI agent workspaces
- **Tests**: Benchmarks and test harnesses for OpenClaw capabilities
- **Docs**: Documentation on how to use, contribute, and extend

## What This Is NOT

- NOT a personal workspace (that's your private workspace)
- NOT a place for secrets, API keys, or personal configuration
- NOT a project-specific repo (physics, etc. stay elsewhere)

## Skills Index

### Memory & Knowledge Management
| Skill | Description |
|-------|-------------|
| `beads` | Dolt-powered issue tracker for AI coding workflows |
| `bookmarks` | Save, list, search, and manage message bookmarks |
| `graph-memory` | Query the agent's knowledge graph for entities and relationships |
| `knowledge` *(ClawHub)* | Unified knowledge capture and retrieval for URLs, extracts, posts, research |
| `mb-init` | Initialize a memory bank for a new project |
| `mb-text-workflow` | Update memory bank via markdown editing |
| `mb-db-workflow` | Update memory bank via SQLite + markdown regeneration |
| `mulch` *(ClawHub)* | Memory compaction and indexing |
| `self-improving-agent` *(ClawHub)* | Captures learnings, errors, and corrections |

### Utilities & Tools
| Skill | Description |
|-------|-------------|
| `cloakbrowser-stealth` | Stealth browser automation using CloakBrowser |
| `image-handoff` | Detect image generation requests and route them to an artist agent |
| `mcp-client` | Spawn and interact with MCP (Model Context Protocol) servers |
| `openclaw-backup` | Backup and restore OpenClaw data with automatic rotation |
| `openclaw-backup-optimized` | Full snapshots with workspace splitting and change summaries |
| `pass-secrets` | GPG-encrypted secrets storage via `pass` |
| `pdf-extract` | Extract text, tables, and structured content from PDF files |
| `time-awareness` | Current date/time rules |
| `timer-build-monitor` | Build monitoring and timing |
| `token-usage` | Track, aggregate, and report OpenClaw token usage and costs |

### Security & Safety
| Skill | Description |
|-------|-------------|
| `red-team` | Red-team protocol for validating numerical claims |
| `worker-safety` | Hard safety limits for AI agent operations |

### Network & System
| Skill | Description |
|-------|-------------|
| `disk-manager` | VPS disk audit and cleanup with persistent operation logging |
| `netstatus` | Combined network + gateway status with VPN info |
| `protonvpn-openvpn` | Manage ProtonVPN OpenVPN connections |

## Scripts

*(Coming soon — see [memory-bank/tasks.md](memory-bank/tasks.md) T4)*

## Tests

| Test Suite | Description |
|------------|-------------|
| `model-benchmarks` | Cross-model capability benchmarks |
| `subagent-tests` | Subagent test harness and JSON test specs |

## Contributing

1. Sanitize: No personal references, no specific paths, no secrets
2. Document: Every skill/script has a README or SKILL.md
3. Test: Scripts work out of the box (with sensible defaults)
4. Version: Skills have versions, changelogs

See [memory-bank/implementation-details/repo-reorganization.md](memory-bank/implementation-details/repo-reorganization.md) for sanitization checklist.

## License

MIT — see individual skill directories for details.
