<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://assets.rs-roadmap.realsimplesolutions.app/Real-Simple-Roadmap-Logo-Light.png">
  <source media="(prefers-color-scheme: light)" srcset="https://assets.rs-roadmap.realsimplesolutions.app/Real-Simple-Roadmap-Logo-Dark.png">
  <img alt="Real Simple Roadmap" src="https://assets.rs-roadmap.realsimplesolutions.app/Real-Simple-Roadmap-Logo-Dark.png" width="400">
</picture>

# create-real-simple-roadmap

Add a visual feature roadmap to any project. Think Storybook, but for planning instead of components.

## Quick Start

```bash
cd /your/existing/project
npm create real-simple-roadmap@latest
npm run rs-roadmap
```

Opens at `http://localhost:5173` - that's it.

## Updating

To update to the latest version while preserving your roadmap data:

```bash
cd /your/existing/project
npm create real-simple-roadmap@latest -- --update
```

**What gets preserved:**
- ✅ All your features (completed, in-dev, planned, blocked)
- ✅ Project metadata (title, subtitle, version)
- ✅ All custom data and notes

**What gets updated:**
- ✅ React frontend code
- ✅ MCP server code
- ✅ Dependencies
- ✅ Bug fixes and new features

## What You Get

A complete roadmap system installed into your project:

```
your-project/
├── real-simple-roadmap/
│   ├── rs-server/       # Express API + MCP server
│   └── rs-roadmap/      # React frontend
└── package.json         # Updated with rs-roadmap script + workspaces
```

Run `npm run rs-roadmap` to start both server and frontend simultaneously.

## Why This Exists

Most roadmaps live in Notion, Linear, or Google Sheets - separate from your codebase. This puts your roadmap where your code lives:

- **Git-tracked** - Feature plans version alongside code
- **Local-first** - No account required, works offline
- **AI-integrated** - MCP server for Claude Desktop/Windsurf/Cursor
- **Developer-friendly** - JSON files, not databases

## Core Features

### 📊 4-Stage Roadmap
- **Completed** → **In Development** → **Planned** → **Blocked**
- Drag-and-drop positioning within sections
- Move features between stages with dropdown selector
- Live statistics dashboard

### 🔧 Rich Feature Tracking
- **Functions list** - Document feature specs with nested sub-items
- **Image attachments** - Screenshots, mockups, wireframes with lightbox viewer
- **Progress tracking** - Completion percentage with visual indicators
- **Time estimates** - Track estimated vs actual hours
- **Tags & phases** - Organize features by category and development phase
- **Status tracking** - In Review, Testing, Ready to Deploy, Deployed, On Hold
- **Notes field** - Internal context that stays with the feature

### 🔍 Search & Bulk Operations
- **Global search** - Search titles, descriptions, notes, tags, functions
- **Advanced filters** - Filter by priority, category, status, phase, tags
- **Bulk actions** - Select multiple features to move or delete at once
- **Keyboard shortcuts** - `/` to search, `?` for help

### 🤖 AI Integration (MCP)
MCP server lets AI assistants read and modify your roadmap:

```json
// Claude Desktop, Windsurf, or Cursor
{
  "mcpServers": {
    "roadmap": {
      "command": "node",
      "args": ["real-simple-roadmap/rs-server/mcp-server.js"]
    }
  }
}
```

Ask Claude: *"Add a feature for user authentication to the roadmap"* - it just works.

### 🎨 Modern UI
- Dark mode with theme toggle
- Responsive design (desktop + mobile)
- Smooth animations and hover effects
- Color-coded categories and priorities

## Installation Details

The CLI wizard handles everything:

- ✅ Detects your package manager (npm/yarn/pnpm)
- ✅ Creates nested directory structure
- ✅ Configures workspaces in your `package.json`
- ✅ Installs dependencies automatically
- ✅ Sets up MCP server config examples
- ✅ Dynamic port detection (3001, 3002, etc.)
- ✅ Git initialization (optional)

## Data Storage

Features live in `real-simple-roadmap/rs-roadmap/src/data/features.json`:

```json
{
  "metadata": {
    "projectTitle": "Your Project",
    "projectSubtitle": "Feature Roadmap",
    "version": "1.0.0",
    "logoUrl": ""  // Optional - shows default logo if empty
  },
  "completedFeatures": [...],
  "inDevFeatures": [...],
  "plannedFeatures": [...],
  "blockedFeatures": [...]
}
```

Plain JSON = easy to read, easy to edit, git-friendly diffs.

## Screenshots

### Claude Desktop MCP Integration

Claude can browse, create, and update features directly through conversation.

![Claude Desktop Feature Planning](https://assets.rs-roadmap.realsimplesolutions.app/rs-roadmap-Claude-Desktop-Feature-Planning.jpg)

![Claude Desktop Adding a Feature](https://assets.rs-roadmap.realsimplesolutions.app/rs-roadmap-Claude-Desktop-Feature-Added.jpg)

![Claude Desktop Updating a Feature](https://assets.rs-roadmap.realsimplesolutions.app/rs-roadmap-Claude-Desktop-Edit-Feature.jpg)

### Roadmap Interface

Four-stage pipeline with search, filters, and bulk operations.

![Feature UI](https://assets.rs-roadmap.realsimplesolutions.app/rs-roadmap-Feature-UI.jpg)

### Feature Editing

Rich metadata with functions, images, tags, progress tracking, and time estimates.

![Feature Editing Modal](https://assets.rs-roadmap.realsimplesolutions.app/rs-roadmap-Edit-Feature.jpg)

### MCP Setup

Simple copy-paste configuration for Claude Desktop, Windsurf, or Cursor.

![MCP Integration Setup](https://assets.rs-roadmap.realsimplesolutions.app/rs-roadmap-copy-and-paste-mcp-integration.png)


## Tech Stack

- **Frontend**: React 19, Vite, Tailwind CSS, Headless UI
- **Backend**: Express.js with JSON file storage  
- **MCP Server**: Model Context Protocol integration
- **Icons**: Lucide React

## Uninstalling

If you need to completely remove Real Simple Roadmap:

```bash
# 1. Remove the roadmap directory
rm -rf real-simple-roadmap

# 2. Clean up package.json (or do it manually)
# Remove these workspaces:
#   "real-simple-roadmap/rs-server"
#   "real-simple-roadmap/rs-roadmap"
# Remove this script:
#   "rs-roadmap"
# Remove devDependency (if not used elsewhere):
#   "concurrently"

# 3. Reinstall dependencies
npm install
```

**Note:** To reinstall later, just run `npm create real-simple-roadmap@latest` again.

## Requirements

- Node.js >= 18.0.0
- npm, yarn, or pnpm

## Security Note

⚠️ **Internal use only** - Includes deployment protection to prevent accidental public hosting. Your roadmap contains unreleased features and internal timelines.

## Links

- **GitHub**: https://github.com/TPGLLC-US/create-real-simple-roadmap
- **Issues**: https://github.com/TPGLLC-US/create-real-simple-roadmap/issues
- **NPM**: https://www.npmjs.com/package/create-real-simple-roadmap

## License

**Elastic License 2.0**

You're free to:
- ✅ Use it for commercial or non-commercial purposes
- ✅ Modify and customize it
- ✅ Self-host for your company/team
- ❌ Cannot resell it as a product
- ❌ Cannot offer it as a hosted/managed service to others

See [LICENSE](LICENSE) for full details.
