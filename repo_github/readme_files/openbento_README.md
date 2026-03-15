# OpenBento

**A beautiful, open-source bento grid generator for creating stunning link-in-bio pages**

[![Deploy to GitHub Pages](https://github.com/yoanbernabeu/openbento/actions/workflows/deploy.yml/badge.svg)](https://github.com/yoanbernabeu/openbento/actions/workflows/deploy.yml)
[![Docker Build & Publish](https://github.com/yoanbernabeu/openbento/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/yoanbernabeu/openbento/actions/workflows/docker-publish.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Pulls](https://img.shields.io/docker/pulls/yoanbernabeu/openbento)](https://hub.docker.com/r/yoanbernabeu/openbento)

[Live Demo](https://yoanbernabeu.github.io/openbento/) • [Report Bug](https://github.com/yoanbernabeu/openbento/issues) • [Request Feature](https://github.com/yoanbernabeu/openbento/issues)

---

## ✨ Features

### 🧱 Block Types (7 types)

- 🔗 **Links** - Clickable links with titles & subtitles
- 🖼️ **Media** - Images & GIFs with position control
- 📺 **YouTube** - Single video, grid, or list mode
- 📝 **Text** - Notes, quotes, and bio sections
- 🌐 **Social** - 26+ platforms with branded colors
- 📍 **Map** - Interactive Google Maps embed
- ⬜ **Spacer** - Empty blocks for layout control

### 🎨 Core Features

- 🖱️ **Visual Drag & Drop** - Intuitive 9×9 grid editor. Drag, resize, and position blocks freely with real-time preview
- 🎭 **Full Customization** - Colors, gradients, custom backgrounds. Avatars with borders, shadows & multiple shapes
- 📦 **Export to React** - Download a complete Vite + React + TypeScript + Tailwind project, ready to deploy
- 🚀 **Multi-Platform Deploy** - Auto-generated configs for Vercel, Netlify, GitHub Pages, Docker, VPS & Heroku
- 🔒 **Privacy First** - No tracking, no account, no server required. All data stays in your browser localStorage
- 📁 **Multiple Bentos** - Save and manage multiple projects locally. Switch between them instantly

### 📊 Optional Analytics

Track visits with your own Supabase instance:
- Page views & unique visitors
- Referrer tracking
- Self-hosted on your Supabase project
- No third-party cookies or trackers
- Admin dashboard included

See [ANALYTICS.md](ANALYTICS.md) for setup instructions.

### 🌐 26+ Social Platforms Supported

X (Twitter), Instagram, TikTok, YouTube, GitHub, GitLab, LinkedIn, Facebook, Twitch, Dribbble, Medium, Dev.to, Reddit, Pinterest, Threads, Bluesky, Mastodon, Substack, Patreon, Ko-fi, Buy Me a Coffee, Snapchat, Discord, Telegram, WhatsApp, and custom links.

### 🛠️ Tech Stack (Exported Project)

Your exported project includes: **React**, **Vite**, **TypeScript**, **Tailwind CSS**, **Lucide Icons**, **React Icons**

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (v18 or higher)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yoanbernabeu/openbento.git
   cd openbento
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Landing Page (Optional)

By default, the app opens directly on the builder (no landing page) to make self-hosting easier.

To enable the landing page:
```bash
VITE_ENABLE_LANDING=true npm run dev
```

For production builds:
```bash
VITE_ENABLE_LANDING=true npm run build
```

### Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## 🐳 Using Docker

OpenBento is available as a multi-platform Docker image supporting both AMD64 and ARM64 architectures (Intel/AMD servers, Mac M1/M2/M3, ARM servers, Raspberry Pi 4+).

### Quick Start with Docker

Pull and run the latest image:

```bash
docker run -d -p 8080:80 yoanbernabeu/openbento:latest
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

### Multi-Platform Support

The Docker image supports multiple architectures:
- **linux/amd64** - Intel/AMD 64-bit (standard servers, PCs)
- **linux/arm64** - ARM 64-bit (Mac M1/M2/M3, AWS Graviton, Raspberry Pi 4+)

Docker automatically selects the correct image for your architecture.

### Building Your Own Image

```bash
# Build for your current platform
docker build -t openbento .

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t openbento .
```

### Docker Compose

Create a `compose.yml`:

```yaml
services:
  openbento:
    image: yoanbernabeu/openbento:latest
    ports:
      - "8080:80"
    restart: unless-stopped
```

Run with:

```bash
docker compose up -d
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting a pull request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

**Yoan Bernabeu**

- GitHub: [@yoanbernabeu](https://github.com/yoanbernabeu)
- Twitter: [@yOyO38](https://twitter.com/yOyO38)

**Anis AYARI**

- GitHub: [@anisayari](https://github.com/anisayari)
- X: [@DFintelligence](https://x.com/DFintelligence)

---

<div align="center">
Made with ❤️ by the open-source community
</div>
