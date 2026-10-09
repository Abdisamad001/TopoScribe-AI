'use client';

import { useEffect, useRef, useState } from 'react';
import AppWorkspace from '@/components/app/AppWorkspace';
import type { AppView } from '@/components/topology/Sidebar';
import { updateDesign } from '@/lib/api';
import { Search, CircleHelp, Bell, User } from 'lucide-react';

export default function Home() {
  const [view, setView] = useState<AppView>('home');
  const [searchQuery, setSearchQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const [activeDesign, setActiveDesign] = useState<{ id: string | null; name: string }>({
    id: null,
    name: 'Untitled Design',
  });

  const saveTitle = (rawName: string) => {
    const name = rawName.trim();
    if (!name || name === activeDesign.name) return;
    setActiveDesign((current) => ({ ...current, name }));
    if (activeDesign.id) {
      updateDesign(activeDesign.id, { name }).catch(() => {});
    }
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  return (
    <main className="flex h-screen flex-col overflow-hidden bg-[#0a0a0a]">
      <header className="relative z-50 flex h-12 shrink-0 items-center justify-between border-b border-white/10 bg-[#0a0a0a] px-4">
        <div className="flex items-center gap-2">
          <img src="/icon.png" alt="" className="h-6 w-6 object-contain" />
          <h1 className="text-sm font-semibold tracking-tight text-white">TopoScribe</h1>
        </div>

        <div className="absolute left-1/2 top-1/2 hidden w-[min(28rem,40vw)] -translate-x-1/2 -translate-y-1/2 md:flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1.5 focus-within:border-white/20">
          <Search size={14} className="shrink-0 text-zinc-500" />
          <input
            ref={searchRef}
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search projects or designs"
            aria-label="Search projects"
            className="ml-2 w-full bg-transparent text-sm text-white placeholder-zinc-500 focus:outline-none"
          />
          <kbd className="ml-2 hidden shrink-0 rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[10px] text-zinc-500 sm:inline">⌘K</kbd>
        </div>

        <div className="flex items-center gap-0.5">
          <button
            type="button"
            aria-label="Support"
            className="rounded-md p-2 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            <CircleHelp size={16} />
          </button>
          <button
            type="button"
            aria-label="Notifications"
            className="rounded-md p-2 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            <Bell size={16} />
          </button>
          <a
            href="https://github.com/Abdisamad001/TopoScribe-AI.git"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
            title="GitHub"
            className="hidden rounded-md p-2 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white md:inline-flex"
          >
            <img src="/github-mark.png" alt="" className="h-4 w-4 invert opacity-70" />
          </a>
          <button
            type="button"
            aria-label="Account"
            className="rounded-md p-2 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            <User size={16} />
          </button>
        </div>
      </header>

      <div className="relative min-h-0 w-full flex-grow overflow-hidden">
        <AppWorkspace
          view={view}
          onViewChange={setView}
          activeDesign={activeDesign}
          onActiveDesignChange={setActiveDesign}
          onRenameDesign={saveTitle}
          searchQuery={searchQuery}
        />
      </div>
    </main>
  );
}
