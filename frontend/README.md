# TopoScribe AI - Agentic Network Design System

## 🚀 Overview
**TopoScribe AI** is an intelligent, web-based platform that allows network architects to design, simulate, and document network topologies using natural language and interactive visual tools.

It combines a **React Flow** frontend with a **Next.js** backend, powered by **Groq LLaMA 3** for AI orchestration.

## ✨ Key Features

### 🧠 AI-Powered Design
- **Natural Language Input**: "Create a redundancy network with 2 routers and OSPF."
- **Auto-Layout**: Intelligently places routers, switches, and hosts.
- **Smart Configuration**: Automatically assigns IP schemas and subnets.

### 🎨 Visual Topology Editor
- **Drag & Drop**: Manually refine designs with custom nodes.
- **Interactive**: Click to configure node properties (Hostname, IP).
- **Responsive**: Smooth zooming and panning with MiniMap controls.

### ⚡ Logical Simulation Engine
- **Reachability Testing**: Real-time graph-based ping simulation.
- **Visual Feedback**: Success/Failure paths are highlighted on the canvas (Green/Red).
- **Path Visualization**: See the exact hop-by-hop path taken by packets.

### 📄 Documentation Generator
- **Auto-Reports**: Generates professional Markdown PDF-ready reports.
- **Cisco CLI**: Automatically generates `IOS` configuration blocks for all devices.
- **Export**: Copy to clipboard or download as `.md` files.

### 📊 Metrics Dashboard
- **Live Analytics**: Tracks time saved vs manual configuration.
- **Efficiency Score**: Real-time feedback on design complexity.

## 🛠 Technology Stack
- **Frontend**: Next.js 14, React, Tailwind CSS, React Flow
- **Backend**: Next.js API Routes (Serverless)
- **AI**: Groq SDK (LLaMA 3-70b)
- **Language**: TypeScript

## 🏁 Getting Started

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Run Development Server**
   ```bash
   npm run dev
   ```

3. **Build for Production**
   ```bash
   npm run build
   npm start
   ```

## 📝 License
MIT
