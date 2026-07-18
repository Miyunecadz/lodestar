# MCP Templates

Starter `.mcp.json` files for common workspace types. Lodestar ships the **server list**;
you supply your **own credentials**. MCP per-folder config is native to Claude Code —
Lodestar just provides templates (see `ARCHITECTURE.md` §5).

## Templates here

| File | Servers | Use for |
|---|---|---|
| `atlassian.mcp.json` | Atlassian (Rovo) | Jira + Bitbucket / Confluence workspaces |
| `github-asana.mcp.json` | GitHub, Asana | GitHub + Asana workspaces |

## How to use

1. **Copy ONE template** to your workspace root as `.mcp.json` (this is **project scope** —
   the folder's own server set, safe to commit/share):

   ```bash
   cp templates/mcp/atlassian.mcp.json .mcp.json
   # or
   cp templates/mcp/github-asana.mcp.json .mcp.json
   ```

2. **Authenticate.** Run `/mcp` inside Claude Code and complete each server's OAuth flow.
   Config can be automated; the interactive OAuth cannot — you do this once per machine.

## What's in the file — and what isn't

- The file holds **only server names and URLs**. **No secrets.** That's why it's safe to
  commit and share with the team.
- **Tokens are per-user, via local scope.** Each person authenticates with `/mcp`; their
  credentials are stored locally (in `~/.claude.json`, keyed by folder), never in `.mcp.json`.
- **Scope precedence:** local > project > user > plugin > claude.ai connectors. The shared
  `.mcp.json` is project scope; your personal tokens live in local scope and take precedence.

## Verify current endpoints

> **Endpoints change.** Before relying on a template, VERIFY each URL against the provider's
> current MCP docs.
>
> - **Atlassian:** use `https://mcp.atlassian.com/v1/mcp/authv2`. The older `/v1/sse`
>   endpoint was **retired after 2026-06-30** in favor of `/v1/mcp/authv2`.
> - **GitHub / Asana:** the URLs in `github-asana.mcp.json` are **placeholders** — confirm
>   the current host, path, and transport (`http` vs `sse`) with each provider before use.
