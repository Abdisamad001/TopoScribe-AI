'use client';

import { ChatCircleIcon, TrashIcon } from '@phosphor-icons/react';
import type { SavedChat } from '@/lib/api';
import { formatDateTime } from '@/lib/formatDate';

export default function ChatsView({
    chats,
    onOpen,
    onDelete,
    searchQuery = '',
}: {
    chats: SavedChat[];
    onOpen: (chat: SavedChat) => void;
    onDelete: (id: string) => void;
    searchQuery?: string;
}) {
    const query = searchQuery.trim().toLowerCase();
    const filtered = query
        ? chats.filter(
              (chat) =>
                  chat.title.toLowerCase().includes(query) ||
                  (chat.design_name || '').toLowerCase().includes(query),
          )
        : chats;

    return (
        <div className="app-page">
            <div className="app-page__inner">
                <div className="app-page__header">
                    <h2 className="app-page__title">Chats</h2>
                    <p className="app-page__subtitle">
                        Ask-assistant conversations. Deleting a chat does not delete the design.
                    </p>
                </div>

                {filtered.length === 0 ? (
                    <div className="ui-empty">
                        <img src="/assitant-welcoming-image.svg" alt="" className="ui-empty__art" />
                        <p className="ui-empty__title">
                            {query ? 'No matching chats' : 'No chats yet'}
                        </p>
                        <p className="ui-empty__text">
                            Ask assistant on the canvas — chats show up here.
                        </p>
                    </div>
                ) : (
                    <div className="flex flex-col gap-2">
                        {filtered.map((chat) => (
                            <button
                                key={chat.id}
                                type="button"
                                onClick={() => onOpen(chat)}
                                className="group ui-card ui-card--row w-full"
                            >
                                <div className="ui-icon-box">
                                    <ChatCircleIcon size={16} weight="regular" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p className="truncate text-sm font-semibold text-white">{chat.title}</p>
                                    <p className="truncate text-xs text-zinc-500">
                                        {chat.design_name || 'No linked design'} · {formatDateTime(chat.updated_at)}
                                    </p>
                                </div>
                                <span
                                    role="button"
                                    tabIndex={0}
                                    aria-label="Delete chat"
                                    title="Delete chat (design stays)"
                                    onClick={(event) => {
                                        event.stopPropagation();
                                        onDelete(chat.id);
                                    }}
                                    onKeyDown={(event) => {
                                        if (event.key !== 'Enter' && event.key !== ' ') return;
                                        event.preventDefault();
                                        event.stopPropagation();
                                        onDelete(chat.id);
                                    }}
                                    className="ui-icon-btn ui-icon-btn--danger ui-icon-btn--fade"
                                >
                                    <TrashIcon size={14} weight="regular" />
                                </span>
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
