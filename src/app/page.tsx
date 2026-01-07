import TopologyEditor from '@/components/topology/TopologyEditor';

export default function Home() {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-white dark:bg-zinc-950">
      {/* App Header */}
      <header className="flex-shrink-0 z-50 flex w-full items-center justify-between border-b border-gray-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-xl">
            T
          </div>
          <h1 className="font-bold text-xl tracking-tight text-gray-900 dark:text-white">
            TopoScribe <span className="text-blue-600 font-light">AI</span>
          </h1>
        </div>

        <div className="flex items-center gap-4 text-sm font-medium text-gray-500 dark:text-gray-400">
          <span className="hidden md:inline-block px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-xs uppercase tracking-wider">
            System Online
          </span>
          <span className="text-xs opacity-50">v1.0.0</span>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex-grow w-full relative overflow-hidden">
        <TopologyEditor />
      </div>
    </main>
  );
}
