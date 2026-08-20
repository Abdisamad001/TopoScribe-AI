import TopologyEditor from '@/components/topology/TopologyEditor';
import { Github } from 'lucide-react';

export default function Home() {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-white dark:bg-zinc-950">
      {/* App Header */}
      <header className="flex-shrink-0 z-50 flex w-full items-center justify-between border-b border-[#14213D]/20 bg-[#212127]/95 backdrop-blur-md px-6 py-2 shadow-lg shadow-black/20">
        <div className="flex items-center gap-1.5">
          <div className="relative h-10 w-10 shrink-0">
            <img
              src="/icon.png"
              alt="TopoScribe Logo"
              className="h-full w-full object-contain"
            />
          </div>
          <h1 className="font-bold text-2xl md:text-3xl leading-none tracking-tight text-white font-[family-name:var(--font-orbitron)]">
            TopoScribe
          </h1>
        </div>

        <div className="flex items-center gap-4 text-sm font-medium text-slate-400">
          <a
            href="https://github.com/Abdisamad001/TopoScribe-AI.git"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#14213D]/10 hover:bg-[#14213D]/20 text-white border border-[#14213D]/20 rounded-full text-xs font-semibold uppercase tracking-wider shadow-[0_0_10px_rgba(20,33,61,0.1)] transition-colors"
          >
            <Github size={14} className="text-white" />
            GitHub
          </a>
          <span className="text-xs opacity-50 font-mono">v1.0.0</span>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex-grow w-full relative overflow-hidden">
        <TopologyEditor />
      </div>
    </main>
  );
}
