---
title: "agent-browser"
description: "Browser automation CLI for AI agents"
canonical_url: "https://agent-browser.dev"
---

# agent-browser

Browser automation CLI designed for AI agents. Compact text output minimizes context usage. 100% native Rust.

```bash
npm install -g agent-browser      # all platforms
brew install agent-browser        # macOS
agent-browser install             # Download Chrome (first time)

# or try without installing
npx agent-browser open example.com
```

## Features

- **Agent-first**: Compact text output uses fewer tokens than JSON, designed for AI context efficiency
- **Ref-based**: Snapshot returns accessibility tree with refs for deterministic element selection
- **Complete**: 50+ commands for navigation, forms, screenshots, network, storage, files, tabs, frames, and debugging
- **Observable**: [Video recording](/recording), [streaming](/streaming), [debugging](/debugging), [profiler](/profiler), and [diffing](/diffing) tools are built in
- **Modern apps**: [Network control](/network), [React & Web Vitals](/react), [init scripts](/init-scripts), [Next.js + Vercel](/next), and [eve Extension](/eve) workflows have first-class docs
- **Stateful**: [Sessions](/sessions), profiles, auth state, cookies, storage, proxy, and security controls support long-running agents
- **Cross-platform**: macOS, Linux, Windows with native binaries

## Works with

Claude Code, Cursor, GitHub Copilot, OpenAI Codex, Google Gemini, opencode, and any agent that can run shell commands.

## Example

```bash
# Navigate and get snapshot
agent-browser open example.com
agent-browser snapshot -i

# Output:
# - heading "Example Domain" [ref=e1]
# - link "More information..." [ref=e2]

# Interact using refs
agent-browser click @e2
agent-browser screenshot page.png
agent-browser close
```

## Why refs?

The `snapshot` command returns a compact accessibility tree where each element has a unique ref like `@e1`, `@e2`. This provides:

- **Context-efficient**: Text output uses ~200-400 tokens vs ~3000-5000 for full DOM
- **Deterministic**: Ref points to exact element from snapshot
- **Fast**: No DOM re-query needed
- **AI-friendly**: LLMs parse text output naturally

## Architecture

Client-daemon architecture for optimal performance:

1. **Rust CLI**: Parses commands, communicates with daemon
2. **Native Daemon**: Pure Rust daemon using direct CDP, manages Chrome via Chrome DevTools Protocol

The daemon starts automatically and persists between commands. By default, it saves configured restore state, closes its headless browser, and exits after one hour without commands or dashboard input. Without `--restore` or another restore key, shutdown discards transient browser state and open tabs. Headed browsers, Safari and iOS WebDriver sessions, and user-attached browsers are exempt from the default timeout; provider-owned cloud browsers are not. Use `--idle-timeout <time>` or `AGENT_BROWSER_IDLE_TIMEOUT_MS` to tune the timeout, and use `0` to disable it.

## Platforms

Native Rust binaries for macOS (ARM64, x64), Linux (ARM64, x64), and Windows (x64).


---
title: "Installation"
description: "Browser automation CLI for AI agents"
canonical_url: "https://agent-browser.dev/installation"
---

# Installation

## Global installation (recommended)

Installs the native Rust binary for maximum performance:

```bash
npm install -g agent-browser
agent-browser install  # Download Chrome from Chrome for Testing (first time)
```

This is the fastest option -- commands run through the native Rust CLI directly with sub-millisecond parsing overhead.

## Quick start (no install)

```bash
npx agent-browser install   # Download Chrome (first time only)
npx agent-browser open example.com
```

## Project installation (local dependency)

For projects that want to pin the version in `package.json`:

```bash
npm install agent-browser
npx agent-browser install  # Download Chrome (first time)
```

Then use via `npx` or `package.json` scripts.

## Homebrew (macOS)

```bash
brew install agent-browser
agent-browser install  # Download Chrome (first time)
```

## Cargo (Rust)

```bash
cargo install agent-browser
agent-browser install  # Download Chrome (first time)
```

Compiles from source (~2-3 min). Requires Node.js 24+, pnpm 11+, and the Rust toolchain ([rustup.rs](https://rustup.rs)).

## From source

```bash
git clone https://github.com/vercel-labs/agent-browser
cd agent-browser
pnpm install
pnpm build
pnpm build:native
./bin/agent-browser install
pnpm link --global
```

## Windows browser sessions

Headless Chrome runs on a private Windows desktop. This prevents hidden browser windows from leaving visible rectangles on your desktop, including with affected Chrome 150 builds. It applies to bundled and custom Chrome executables and to windows created later in the session. Automation, screenshots, and GPU rendering continue through CDP.

Use `--headed` to show Chrome on the interactive desktop. Sessions with extensions also use the interactive desktop. Agent-browser owns the Chrome processes it launches: Windows terminates the entire Chrome tree when its daemon exits or is forcibly killed. Browsers attached with `--cdp` or `--auto-connect` remain externally owned.

## Linux dependencies

On Linux, install system dependencies:

```bash
agent-browser install --with-deps
```

This exits nonzero if the package manager cannot install every required browser library.

## Updating

Upgrade to the latest version:

```bash
agent-browser upgrade
```

Detects your installation method (npm, Homebrew, or Cargo) and runs the appropriate update command automatically. Displays the version change on success, or informs you if you are already on the latest version.

## Doctor

`doctor` diagnoses your install and auto-cleans stale daemon files. Run it whenever something stops working unexpectedly, or after upgrades:

```bash
agent-browser doctor                     # Full diagnosis
agent-browser doctor --offline --quick   # Local-only, fastest (~<1s)
agent-browser doctor --fix               # Also run destructive repairs
agent-browser doctor --webgpu            # Also run a live WebGPU render probe
agent-browser doctor --json              # Structured output
```

It checks:

<table>
<thead>
<tr><th>Category</th><th>What it checks</th></tr>
</thead>
<tbody>
<tr><td>Environment</td><td>CLI version, platform, home directory, state and socket dirs, free disk space</td></tr>
<tr><td>Chrome</td><td>Chrome install path and version, cache dir, Puppeteer fallback, user-data dir and profile count, optional <code>lightpanda</code> engine</td></tr>
<tr><td>Daemons</td><td>Running daemons per session, stale <code>.sock</code> / <code>.pid</code> / <code>.version</code> / <code>.stream</code> files (auto-cleaned), version mismatch with the CLI, dashboard process liveness</td></tr>
<tr><td>Config</td><td><code>~/.agent-browser/config.json</code>, <code>./agent-browser.json</code>, and any file at <code>AGENT_BROWSER_CONFIG</code> parse as valid JSON</td></tr>
<tr><td>Security</td><td>Encryption key env var or <code>~/.agent-browser/.encryption-key</code> (with 0600 permissions on unix), state file count and age vs <code>AGENT_BROWSER_STATE_EXPIRE_DAYS</code>, action policy file</td></tr>
<tr><td>Providers</td><td>Env vars for Browserless, Browserbase, Browser Use, Kernel, AgentCore (AWS creds), Appium (for <code>--provider ios</code>), and <code>AI_GATEWAY_API_KEY</code> for chat</td></tr>
<tr><td>Network</td><td>Reachability of the Chrome for Testing CDN, AI Gateway (if configured), and any currently selected provider endpoint (skipped under <code>--offline</code>)</td></tr>
<tr><td>Launch test</td><td>Spawns a scratch session, launches headless Chrome, navigates to <code>about:blank</code>, then closes. Measures wall time (skipped under <code>--quick</code>)</td></tr>
<tr><td>WebGPU probe</td><td>Opt-in via <code>--webgpu</code>: launches a scratch session with the <a href="/webgpu">WebGPU preset</a>, renders through a real WebGPU pass, and pixel-checks both an offscreen readback and a decoded screenshot. Add <code>--headed</code> to validate the headed/Xvfb capture path</td></tr>
</tbody>
</table>

Stale sidecar files are always cleaned. Destructive actions are opt-in via `--fix`:

<table>
<thead>
<tr><th>Check</th><th>What <code>--fix</code> does</th></tr>
</thead>
<tbody>
<tr><td>Chrome missing</td><td>Runs <code>agent-browser install</code></td></tr>
<tr><td>Version-mismatched daemons</td><td>Sends <code>close</code> to each and cleans files</td></tr>
<tr><td>Old state files</td><td>Deletes state files older than <code>AGENT_BROWSER_STATE_EXPIRE_DAYS</code> (default 30)</td></tr>
<tr><td>Missing encryption key</td><td>Generates a new key at <code>~/.agent-browser/.encryption-key</code> (0600, unix); never overwrites an existing key</td></tr>
</tbody>
</table>

Exit code is `0` if all checks pass (warnings are fine), `1` if any fail.

## Custom browser

Use a custom browser executable instead of bundled Chromium:

- **Serverless** - Use `@sparticuz/chromium` (~50MB vs ~684MB)
- **System browser** - Use existing Chrome installation
- **Custom builds** - Use modified browser builds

```bash
# Via flag
agent-browser --executable-path /path/to/chromium open example.com

# Via environment variable
AGENT_BROWSER_EXECUTABLE_PATH=/path/to/chromium agent-browser open example.com
```

### Serverless example

Use `@sparticuz/chromium` or similar to obtain a Chromium executable path, then pass it via `--executable-path` or `AGENT_BROWSER_EXECUTABLE_PATH`.

## AI agent setup

agent-browser works with any AI agent out of the box. For richer context:

### AI coding assistants (recommended)

Install the skill for your AI coding assistant:

```bash
npx skills add vercel-labs/agent-browser
```

This works with Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, Goose, OpenCode, and Windsurf. The skill is fetched from the repository and stays up to date automatically.

> **Do not** copy `SKILL.md` from `node_modules` -- it will become stale as new features are added. Always use `npx skills add` or reference the repository version.

### AGENTS.md / CLAUDE.md

Add to your instructions file:

```markdown
## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:
1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs (@e1, @e2)
3. `agent-browser click @e1` / `fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes
```



---
title: "Quick Start"
description: "Browser automation CLI for AI agents"
canonical_url: "https://agent-browser.dev/quick-start"
---

# Quick Start

## Core workflow

Every browser automation follows this pattern:

```bash
# 1. Navigate
agent-browser open example.com

# 2. Snapshot to get element refs
agent-browser snapshot -i
# Output:
# @e1 [heading] "Example Domain"
# @e2 [link] "More information..."

# 3. Interact using refs
agent-browser click @e2

# 4. Re-snapshot after page changes
agent-browser snapshot -i
```

## Common commands

```bash
agent-browser open example.com
agent-browser snapshot -i                # Get interactive elements with refs
agent-browser click @e2                  # Click by ref
agent-browser fill @e3 "test@example.com" # Fill input by ref
agent-browser get text @e1               # Get text content
agent-browser screenshot                 # Save to temp directory
agent-browser screenshot page.png        # Save to specific path
agent-browser close
```

## Traditional selectors

CSS selectors and semantic locators also supported:

```bash
agent-browser click "#submit"
agent-browser fill "#email" "test@example.com"
agent-browser find role button click --name "Submit"
```

## Headed mode

Show browser window for debugging:

```bash
agent-browser open example.com --headed
```

## Wait for content

```bash
agent-browser wait @e1                   # Wait for element
agent-browser wait --text "Welcome"      # Wait for expected text
agent-browser wait --url "**/dashboard"  # Wait for URL pattern
agent-browser wait --fn "window.appReady === true" # Wait for JS condition
agent-browser wait --load domcontentloaded # Wait for the DOM lifecycle event
```

After a page change, prefer the condition that represents the result you need. Use `load` or `domcontentloaded` only when the lifecycle event is the milestone. `networkidle` remains available for pages known to become quiet, but SSE, WebSockets, polling, and long-polling can keep it from resolving.

## Command chaining

Chain commands with `&&` in a single shell call. The browser persists via a background daemon, so chaining is safe and efficient:

```bash
# Open, wait, and snapshot in one call
agent-browser open example.com && agent-browser wait --load domcontentloaded && agent-browser snapshot -i

# Chain multiple interactions
agent-browser fill @e1 "user@example.com" && agent-browser fill @e2 "pass" && agent-browser click @e3

# Navigate and capture
agent-browser open example.com && agent-browser wait --load load && agent-browser screenshot page.png
```

Use `&&` when you don't need intermediate output. Run commands separately when you need to parse output first (e.g., snapshot to discover refs before interacting).

## JSON output

For programmatic parsing in scripts:

```bash
agent-browser snapshot --json
agent-browser get text @e1 --json
```

Note: The default text output is more compact and preferred for AI agents.


---
title: "Plugins"
description: "Browser automation CLI for AI agents"
canonical_url: "https://agent-browser.dev/plugins"
---

# Plugins

Plugins let agent-browser integrate with external tools without adding those tools to core. A plugin is a local executable that reads one JSON request from stdin and writes one JSON response to stdout.

Use plugins for vault-backed login, custom browser providers, local launch customization, and domain-specific commands such as CAPTCHA solving.

## When to write a plugin

Write a plugin when the integration needs vendor SDKs, local CLIs, credentials, paid APIs, or behavior that should not become an agent-browser dependency.

Good plugin fits:

- Resolve login credentials from an external vault
- Launch a browser through a hosted provider and return a CDP WebSocket URL
- Add local Chrome launch arguments, extensions, or init scripts
- Run a namespaced command such as `captcha.solve`

Keep browser automation itself in agent-browser. A plugin should provide data or launch configuration, then let agent-browser continue driving the browser.

## What to build as a plugin

These are good places for plugin authors to start:

- **New cloud browser providers**: Hosted browser platforms are good models for `browser.provider`. Existing built-ins can stay in core for compatibility, but new providers should usually start as plugins.
- **Vault integrations**: Password managers, secret stores, and enterprise SSO helpers fit `credential.read`. Keep the local encrypted auth vault in core, but put vendor-specific vault access in plugins.
- **Stealth and anti-detection**: These techniques change quickly and can be risky to support in core. They fit `launch.mutate` plugins that append launch args, extensions, init scripts, or user-agent overrides.
- **CAPTCHA solvers**: CAPTCHA integrations are plugin territory because they involve third-party APIs, credentials, policy concerns, and fast vendor churn. They can use `command.run` or a custom capability such as `captcha.solve`.
- **Vendor-specific auth helpers**: Login helpers for a specific app, IdP, or enterprise flow should live outside core unless they become generic browser automation primitives.

## Add a plugin someone else built

Use `plugin add` with the package or repository name:

```bash
agent-browser plugin add agent-browser-plugin-captcha
agent-browser plugin add @company/agent-browser-plugin-vault --name vault
agent-browser plugin add org/agent-browser-plugin-cloud-browser
```

agent-browser chooses the source from the reference:

<table>
  <thead>
    <tr><th>Reference</th><th>Source</th><th>Example</th></tr>
  </thead>
  <tbody>
    <tr><td><code>name</code></td><td>npm package</td><td><code>agent-browser-plugin-captcha</code></td></tr>
    <tr><td><code>@scope/name</code></td><td>scoped npm package</td><td><code>@company/agent-browser-plugin-vault</code></td></tr>
    <tr><td><code>owner/repo</code></td><td>GitHub repository</td><td><code>org/agent-browser-plugin-cloud-browser</code></td></tr>
  </tbody>
</table>

`plugin add` writes `./agent-browser.json` by default. Use `--global` to write `~/.agent-browser/config.json` instead.

During add, agent-browser runs the package once and asks for `plugin.manifest`. A plugin manifest declares the plugin name and capabilities. If a plugin does not support manifests yet, use the capabilities from the plugin README:

```bash
agent-browser plugin add agent-browser-plugin-captcha --capability command.run --capability captcha.solve --no-manifest
```

Verify the plugin is configured:

```bash
agent-browser plugin list
agent-browser plugin show captcha
```

Then use it through the command path for its capability:

```bash
agent-browser auth login my-app --credential-provider vault --item "My App"
agent-browser auth login my-app --credential-provider vault --item "My App" --no-navigate --url https://identity.example.com/login
agent-browser --provider cloud-browser open https://example.com
agent-browser open https://example.com
agent-browser plugin run captcha captcha.solve --payload '{"siteKey":"abc","url":"https://example.com"}'
```

`launch.mutate` plugins run automatically for local launches such as `agent-browser open`.

## Configure a plugin

`plugin add` creates this config for you. You can also edit the `plugins` array manually:

```json
{
  "plugins": [
    {
      "name": "vault",
      "command": "agent-browser-plugin-vault",
      "args": [],
      "capabilities": ["credential.read"]
    },
    {
      "name": "captcha",
      "command": "agent-browser-plugin-captcha",
      "capabilities": ["command.run", "captcha.solve"]
    }
  ]
}
```

Inspect the registry:

```bash
agent-browser plugin list
agent-browser plugin show vault
```

`AGENT_BROWSER_PLUGINS` can replace config discovery with a JSON array using the same shape.

Do not put API tokens, vault tokens, or passwords in plugin `args`. Use the vendor's own CLI login, keychain, environment, or session mechanism outside agent-browser config.

## Protocol

agent-browser starts the executable, writes this envelope to stdin, waits for stdout, and parses stdout as JSON:

```json
{
  "protocol": "agent-browser.plugin.v1",
  "type": "credential.resolve",
  "capability": "credential.read",
  "request": {}
}
```

Every successful response must include the same protocol and `success: true`:

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "data": {}
}
```

Only stdout is parsed. Write no logs to stdout. agent-browser suppresses plugin stderr for core integrations, so use files or your own debug mode when developing.

Core integrations suppress plugin-provided error text in user-facing errors to reduce accidental secret exposure. Generic `plugin run` keeps plugin error text because it is a developer-facing command.

## Plugin manifest

Support `plugin.manifest` so users can add your plugin without manually entering capabilities:

```json
{
  "protocol": "agent-browser.plugin.v1",
  "type": "plugin.manifest",
  "capability": "plugin.manifest",
  "request": {}
}
```

Return the plugin name and capabilities:

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "manifest": {
    "name": "captcha",
    "capabilities": ["command.run", "captcha.solve"],
    "description": "Solve CAPTCHA challenges through Example CAPTCHA"
  }
}
```

With a manifest, users can run:

```bash
agent-browser plugin add agent-browser-plugin-captcha
```

Without a manifest, users must pass `--capability` flags during add.

## Capabilities

<table>
  <thead>
    <tr><th>Capability</th><th>Request type</th><th>How users invoke it</th><th>Response field</th></tr>
  </thead>
  <tbody>
    <tr><td><code>credential.read</code></td><td><code>credential.resolve</code></td><td><code>auth login --credential-provider &lt;name&gt;</code></td><td><code>credential</code></td></tr>
    <tr><td><code>browser.provider</code></td><td><code>browser.launch</code>, <code>browser.close</code></td><td><code>--provider &lt;name&gt;</code></td><td><code>browser</code></td></tr>
    <tr><td><code>launch.mutate</code></td><td><code>launch.mutate</code></td><td>Any local launch</td><td><code>launch</code></td></tr>
    <tr><td><code>command.run</code></td><td>Custom request type</td><td><code>plugin run &lt;name&gt; &lt;type&gt;</code></td><td><code>data</code></td></tr>
  </tbody>
</table>

Plugins may declare custom capabilities such as `captcha.solve`. `plugin run` can invoke `command.run` and custom capabilities, but it cannot invoke core capabilities or protocol request types directly. Use the dedicated command path for `credential.read`, `browser.provider`, and `launch.mutate`.

## Minimal plugin

This plugin implements `captcha.solve` and returns a fake token:

```js
#!/usr/bin/env node

const chunks = [];
for await (const chunk of process.stdin) {
  chunks.push(chunk);
}

const input = JSON.parse(Buffer.concat(chunks).toString("utf8"));

function reply(body) {
  process.stdout.write(
    JSON.stringify({
      protocol: "agent-browser.plugin.v1",
      success: true,
      ...body,
    })
  );
}

if (input.protocol !== "agent-browser.plugin.v1") {
  process.stdout.write(
    JSON.stringify({
      protocol: "agent-browser.plugin.v1",
      success: false,
      error: "unsupported protocol",
    })
  );
  process.exit(0);
}

if (input.type === "plugin.manifest") {
  reply({
    manifest: {
      name: "captcha",
      capabilities: ["command.run", "captcha.solve"],
      description: "Example CAPTCHA plugin",
    },
  });
  process.exit(0);
}

if (input.type === "captcha.solve") {
  reply({
    data: {
      token: "example-token",
      siteKey: input.request.siteKey,
      url: input.request.url,
    },
  });
  process.exit(0);
}

process.stdout.write(
  JSON.stringify({
    protocol: "agent-browser.plugin.v1",
    success: false,
    error: `unsupported request type: ${input.type}`,
  })
);
```

Make it executable and configure it:

```bash
chmod +x ./agent-browser-plugin-captcha
```

```json
{
  "plugins": [
    {
      "name": "captcha",
      "command": "./agent-browser-plugin-captcha",
      "capabilities": ["command.run", "captcha.solve"]
    }
  ]
}
```

Run it:

```bash
agent-browser plugin run captcha captcha.solve --payload '{"siteKey":"abc","url":"https://example.com"}'
```

## Credential plugin

A credential plugin receives:

```json
{
  "protocol": "agent-browser.plugin.v1",
  "type": "credential.resolve",
  "capability": "credential.read",
  "request": {
    "profileName": "my-app",
    "itemRef": "My App",
    "url": "https://app.example.com/login"
  }
}
```

Return `credential`:

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "credential": {
    "username": "alice@example.com",
    "password": "secret",
    "url": "https://app.example.com/login",
    "usernameSelector": "#username",
    "passwordSelector": "#password",
    "submitSelector": "input[type=submit]"
  }
}
```

Use it for one login:

```bash
agent-browser auth login my-app --credential-provider vault --item "My App"
```

For a login form reached through stateful in-page setup, add `--no-navigate`. The active top-level page must have the same scheme, host, and effective port as the effective credential URL. Command-level `--url` overrides provider URL metadata and supplies this expected origin without navigating. The provider secret remains outside generated process arguments and normal output:

```bash
agent-browser auth login my-app --credential-provider vault --item "My App" --no-navigate --url https://identity.example.com/login
```

For external vaults, prefer calling the vendor CLI from the plugin and relying on its existing local session. Do not pass vault tokens in `agent-browser.json`.

## Browser provider plugin

A browser provider plugin receives `browser.launch` and returns a CDP URL:

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "browser": {
    "cdpUrl": "ws://127.0.0.1:9222/devtools/browser/session",
    "directPage": false,
    "metadata": {
      "sessionId": "provider-session-id"
    },
    "cleanup": {
      "sessionId": "provider-session-id"
    }
  }
}
```

Then users launch through the plugin name:

```bash
agent-browser --provider cloud-browser open https://example.com
```

If `cleanup` is returned and connection fails, agent-browser later sends it back as the request body for `browser.close`.

## Launch mutator plugin

A launch mutator receives local launch options before Chrome starts and can append arguments, extensions, init scripts, or a user agent:

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "launch": {
    "args": ["--disable-blink-features=AutomationControlled"],
    "extensions": ["/absolute/path/to/extension"],
    "initScripts": [
      "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    ],
    "userAgent": "my-agent/1.0"
  }
}
```

Configure it with `launch.mutate`, then use any local launch command:

```bash
agent-browser open https://example.com
```

Launch mutators do not run for CDP connections or remote browser providers because those browsers are already running outside the local launch path.

## Policy and confirmation

Plugin access is exposed as capability-scoped policy actions:

```bash
agent-browser --confirm-actions plugin:vault:credential.read auth login my-app --credential-provider vault --item "My App"
agent-browser --confirm-actions plugin:cloud-browser:browser.provider --provider cloud-browser open https://example.com
agent-browser --confirm-actions plugin:stealth:launch.mutate open https://example.com
```

The action string is `plugin:<name>:<capability>`.

## Packaging guidance

For npm packages, expose a `bin` command with no required stdout logs:

```json
{
  "name": "agent-browser-plugin-example",
  "bin": {
    "agent-browser-plugin-example": "./bin/plugin.js"
  }
}
```

Keep the plugin small and explicit:

- Declare only the capabilities it actually supports
- Read exactly one request from stdin
- Write exactly one JSON response to stdout
- Keep secrets out of command-line arguments
- Let agent-browser handle navigation, selectors, screenshots, state, and policy






---
title: "Skills"
description: "Browser automation CLI for AI agents"
canonical_url: "https://agent-browser.dev/skills"
---

# Skills

agent-browser ships with skills that teach AI coding agents how to use it for specific workflows. Install a skill and your agent in Cursor, Claude Code, or Codex can automate browser tasks without manual guidance.

## Installation

```bash
npx skills add vercel-labs/agent-browser
```

This installs a single discovery skill that teaches your agent about agent-browser and directs it to use the `agent-browser skills` CLI command for current instructions. The discovery skill contains trigger words so agents prefer agent-browser over built-in browser tools.

## CLI Command

Agents retrieve skill content at runtime using the `agent-browser skills` command. This always serves content matching the installed CLI version, so instructions never go stale.

<table>
  <thead>
    <tr>
      <th>Command</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>agent-browser skills</code></td>
      <td>List all available skills (same as <code>skills list</code>)</td>
    </tr>
    <tr>
      <td><code>agent-browser skills list</code></td>
      <td>List all available skills with names and descriptions</td>
    </tr>
    <tr>
      <td><code>agent-browser skills get &lt;name&gt;</code></td>
      <td>Output a skill's full content</td>
    </tr>
    <tr>
      <td><code>agent-browser skills get &lt;name&gt; --full</code></td>
      <td>Include references and templates alongside the skill</td>
    </tr>
    <tr>
      <td><code>agent-browser skills get --all</code></td>
      <td>Output every skill</td>
    </tr>
    <tr>
      <td><code>agent-browser skills path [name]</code></td>
      <td>Print the filesystem path to a skill directory</td>
    </tr>
  </tbody>
</table>

All commands support `--json` for structured output.

Set the `AGENT_BROWSER_SKILLS_DIR` environment variable to override the skills directory path.

## How It Works

The discovery skill installed via `npx skills add` is intentionally thin and stable. It makes agents aware of agent-browser, provides trigger words for activation, and points to the `agent-browser skills` command. Actual usage instructions, command references, workflows, and specialized knowledge all live in the CLI-served skills.

This design solves the version drift problem: the installed SKILL.md rarely changes, while the CLI always serves content matching its own version.

## Available Skills

- **core** — Core browser automation: navigation, snapshots, forms, screenshots, data extraction, sessions, authentication, diffing, and the full command reference. Start here for most browser tasks.
- **dogfood** — Systematic exploratory testing. Navigates an app like a real user, finds bugs and UX issues, and produces a structured report with screenshots and repro videos.
- **derive-client** — Reverse-engineer a site's internal API. Records network traffic into a HAR (with response bodies embedded), identifies the real endpoints, and generates a standalone client or CLI that skips the browser entirely.
- **electron** — Automate any Electron app (VS Code, Slack, Discord, Figma, etc.) by connecting to its built-in Chrome DevTools Protocol port.
- **slack** — Browser-based Slack automation. Check unreads, navigate channels, search conversations, send messages, and extract data.
- **vercel-sandbox** — Run agent-browser + headless Chrome inside ephemeral Vercel Sandbox microVMs.
- **protected-vercel-deployments** — Access and test Vercel deployments behind Vercel Authentication, SSO, or Deployment Protection with short-lived Trusted Sources OIDC tokens.
- **agentcore** — Run agent-browser on AWS Bedrock AgentCore cloud browsers.

Use `agent-browser skills list` to see all available skills, then `agent-browser skills get <name>` to load one. `agent-browser skills get core --full` is the recommended starting point for most browser tasks.

## eve agents

For eve agents, mount the [`@agent-browser/eve`](/eve) extension instead of writing browser tools by hand. It gives the agent namespaced browser tools backed by agent-browser inside the eve sandbox.

## Source

All skill files are in the [`skills/`](https://github.com/vercel-labs/agent-browser/tree/main/skills) and [`skill-data/`](https://github.com/vercel-labs/agent-browser/tree/main/skill-data) directories of the repository. The `skills/` directory holds the discovery stub that `npx skills add` installs; the `skill-data/` directory holds the runtime skill content served by the CLI.







