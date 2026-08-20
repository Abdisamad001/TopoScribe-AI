import TopologyEditor from '@/components/topology/TopologyEditor';

export default function Home() {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-white dark:bg-zinc-950">
      {/* App Header */}
      <header className="flex-shrink-0 z-50 flex w-full items-center justify-between border-b border-[#E05216]/20 bg-[#212127]/95 backdrop-blur-md px-6 py-2 shadow-lg shadow-black/20">
        <div className="flex items-center gap-3">
          <div className="relative h-20 w-auto shrink-0">
            {/* Using standard img for simplicity with public folder, or next/image if configured */}
            <img
              src="/logo.png"
              alt="TopoScribe Logo"
              className="h-full w-auto object-contain"
            />
          </div>
        </div>

        <div className="flex items-center gap-4 text-sm font-medium text-slate-400">
          <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#E05216]/10 text-[#E05216] border border-[#E05216]/20 rounded-full text-xs font-semibold uppercase tracking-wider shadow-[0_0_10px_rgba(224,82,22,0.1)]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#E05216] animate-pulse"></span>
            Simulating...
          </span>
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
