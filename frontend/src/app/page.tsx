import TopologyEditor from '@/components/topology/TopologyEditor';

export default function Home() {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-white dark:bg-zinc-950">
      {/* App Header */}
      <header className="flex-shrink-0 z-50 flex w-full items-center justify-between border-b border-[#3DD6B5]/20 bg-[#142338]/95 backdrop-blur-md px-6 py-3 shadow-lg shadow-black/20">
        <div className="flex items-center gap-3">
          <div className="relative w-12 h-12 shrink-0">
            {/* Using standard img for simplicity with public folder, or next/image if configured */}
            <img
              src="/icon.png"
              alt="TopoScribe AI Logo"
              className="w-full h-full object-contain drop-shadow-[0_0_8px_rgba(61,214,181,0.5)] scale-110"
            />
          </div>
          <h1 className="font-bold text-2xl md:text-3xl leading-none tracking-tight text-white pt-1">
            TopoScribe<span className="text-teal-400 font-light ml-0.5">AI</span>
          </h1>
        </div>

        <div className="flex items-center gap-4 text-sm font-medium text-slate-400">
          <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 bg-teal-500/10 text-teal-400 border border-teal-500/20 rounded-full text-xs font-semibold uppercase tracking-wider shadow-[0_0_10px_rgba(61,214,181,0.1)]">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse"></span>
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
