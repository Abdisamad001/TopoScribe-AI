'use client';

import { useState } from 'react';
import { FolderIcon, PlusIcon, TrashIcon } from '@phosphor-icons/react';
import type { Design, Project } from '@/lib/api';

export default function ProjectsView({
    projects,
    designs,
    onCreate,
    onDelete,
    onAddDesign,
    onRemoveDesign,
    onOpenDesign,
    searchQuery = '',
}: {
    projects: Project[];
    designs: Design[];
    onCreate: (name: string) => void;
    onDelete: (id: string) => void;
    onAddDesign: (projectId: string, designId: string) => void;
    onRemoveDesign: (projectId: string, designId: string) => void;
    onOpenDesign: (id: string) => void;
    searchQuery?: string;
}) {
    const [newName, setNewName] = useState('');
    const [openId, setOpenId] = useState<string | null>(null);

    const query = searchQuery.trim().toLowerCase();
    const filtered = query
        ? projects.filter((project) => project.name.toLowerCase().includes(query))
        : projects;

    const designById = new Map(designs.map((design) => [design.id, design]));

    const submitCreate = () => {
        const name = newName.trim();
        if (!name) return;
        onCreate(name);
        setNewName('');
    };

    return (
        <div className="app-page">
            <div className="app-page__inner">
                <div className="app-page__header">
                    <h2 className="app-page__title">Projects</h2>
                    <p className="app-page__subtitle">
                        Folders of designs. Removing a project does not delete the designs.
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <input
                        value={newName}
                        onChange={(event) => setNewName(event.target.value)}
                        onKeyDown={(event) => {
                            if (event.key === 'Enter') submitCreate();
                        }}
                        placeholder="New project name"
                        aria-label="New project name"
                        className="ui-input"
                    />
                    <button type="button" onClick={submitCreate} className="ui-btn-primary">
                        <PlusIcon size={14} weight="regular" />
                        Create
                    </button>
                </div>

                {filtered.length === 0 ? (
                    <div className="ui-empty">
                        <img src="/no-folder-icon.svg" alt="" className="ui-empty__art" />
                        <p className="ui-empty__title">
                            {query ? 'No matching projects' : 'No projects yet'}
                        </p>
                        <p className="ui-empty__text">
                            Create a project, then add designs from Home into it.
                        </p>
                    </div>
                ) : (
                    <div className="flex flex-col gap-2">
                        {filtered.map((project) => {
                            const isOpen = openId === project.id;
                            const members = project.design_ids
                                .map((id) => designById.get(id))
                                .filter(Boolean) as Design[];
                            const available = designs.filter((d) => !project.design_ids.includes(d.id));

                            return (
                                <div key={project.id} className="ui-card">
                                    <div className="flex items-center gap-2 px-4 py-3">
                                        <button
                                            type="button"
                                            onClick={() => setOpenId(isOpen ? null : project.id)}
                                            className="flex min-w-0 flex-1 items-center gap-3 text-left"
                                        >
                                            <div className="ui-icon-box">
                                                <FolderIcon size={16} weight="regular" />
                                            </div>
                                            <div className="min-w-0">
                                                <p className="truncate text-sm font-semibold text-white">{project.name}</p>
                                                <p className="text-xs text-zinc-500">
                                                    {project.design_ids.length} design{project.design_ids.length === 1 ? '' : 's'}
                                                </p>
                                            </div>
                                        </button>
                                        <button
                                            type="button"
                                            aria-label="Delete project"
                                            title="Delete project (designs stay)"
                                            onClick={() => onDelete(project.id)}
                                            className="ui-icon-btn ui-icon-btn--danger"
                                        >
                                            <TrashIcon size={14} weight="regular" />
                                        </button>
                                    </div>

                                    {isOpen && (
                                        <div className="border-t border-white/10 px-4 py-3">
                                            {members.length === 0 ? (
                                                <p className="text-xs text-zinc-500">No designs in this project yet.</p>
                                            ) : (
                                                <ul className="flex flex-col gap-1">
                                                    {members.map((design) => (
                                                        <li
                                                            key={design.id}
                                                            className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-white/5"
                                                        >
                                                            <button
                                                                type="button"
                                                                onClick={() => onOpenDesign(design.id)}
                                                                className="truncate text-left text-sm text-zinc-200 hover:text-white"
                                                            >
                                                                {design.name}
                                                            </button>
                                                            <button
                                                                type="button"
                                                                onClick={() => onRemoveDesign(project.id, design.id)}
                                                                className="shrink-0 text-[11px] text-zinc-500 hover:text-red-400"
                                                            >
                                                                Remove
                                                            </button>
                                                        </li>
                                                    ))}
                                                </ul>
                                            )}

                                            {available.length > 0 && (
                                                <select
                                                    className="ui-select"
                                                    defaultValue=""
                                                    onChange={(event) => {
                                                        const designId = event.target.value;
                                                        if (!designId) return;
                                                        onAddDesign(project.id, designId);
                                                        event.target.value = '';
                                                    }}
                                                >
                                                    <option value="" disabled>
                                                        Add a design…
                                                    </option>
                                                    {available.map((design) => (
                                                        <option key={design.id} value={design.id}>
                                                            {design.name}
                                                        </option>
                                                    ))}
                                                </select>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
