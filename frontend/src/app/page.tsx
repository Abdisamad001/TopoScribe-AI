import AppWorkspace from '@/components/app/AppWorkspace';
import { MagnifyingGlassIcon, QuestionIcon, BellIcon, UserCircleIcon } from '@phosphor-icons/react/ssr';

export default function Home() {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-white dark:bg-zinc-950">
      {/* App Header */}
      <header className="relative flex-shrink-0 z-50 flex w-full items-center justify-between border-b border-chrome-navy/40 bg-[#212127]/95 backdrop-blur-md px-6 py-2 shadow-lg shadow-black/20">
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

        <div className="absolute left-1/2 top-1/2 hidden w-[min(28rem,36vw)] -translate-x-1/2 -translate-y-1/2 md:flex items-center rounded-full border border-white/15 bg-[#14213D]/20 px-3 py-1.5">
          <MagnifyingGlassIcon size={16} weight="regular" className="shrink-0 text-slate-400" />
          <input
            type="text"
            placeholder="Search or ask anything"
            className="ml-2 w-full bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-4 text-sm font-medium text-slate-400">
          <div className="flex items-center gap-0.5">
          <button
            type="button"
            aria-label="Support"
            className="p-2 rounded-lg text-white hover:bg-white/10 transition-colors"
          >
            <QuestionIcon size={20} weight="regular" />
          </button>
          <button
            type="button"
            aria-label="Notifications"
            className="p-2 rounded-lg text-white hover:bg-white/10 transition-colors"
          >
            <BellIcon size={20} weight="regular" />
          </button>
          <a
            href="https://github.com/Abdisamad001/TopoScribe-AI.git"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
            title="GitHub"
            className="hidden md:inline-flex p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <img
              src="/github-mark.png"
              alt=""
              className="h-[18px] w-[18px] invert"
            />
          </a>
          </div>
          <button
            type="button"
            aria-label="Account"
            className="p-2 rounded-lg text-white hover:bg-white/10 transition-colors"
          >
            <UserCircleIcon size={20} weight="regular" />
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex-grow w-full relative overflow-hidden">
        <AppWorkspace />
      </div>
    </main>
  );
}
