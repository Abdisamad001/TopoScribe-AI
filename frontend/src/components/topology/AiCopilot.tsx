'use client';

import React from 'react';
import { RobotIcon, XIcon } from '@phosphor-icons/react';
import ChatInterface from './ChatInterface';
import ImmersiveChatPanel, {
    AI_ASSISTANT_SUBTITLE,
    AI_ASSISTANT_TITLE,
} from './ImmersiveChatPanel';

interface AiCopilotProps {
    isOpen: boolean;
    onOpen: () => void;
    onClose: () => void;
    messages: { role: 'user' | 'assistant'; content: string }[];
    onSendMessage: (message: string) => void;
    loading?: boolean;
    onTopologyGenerated: (topology: any, runtime?: any) => void;
    onRequestClarification: (prompt: string, questions: string[]) => void;
}

export default function AiCopilot({
    isOpen,
    onOpen,
    onClose,
    messages,
    onSendMessage,
    loading,
    onTopologyGenerated,
    onRequestClarification,
}: AiCopilotProps) {
    const isReplyMode = messages.length > 0;
    const [generating, setGenerating] = React.useState(false);

    React.useEffect(() => {
        if (!isOpen) return;
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [isOpen, onClose]);

    const handleTopologyGenerated = (topology: any, runtime?: any) => {
        onTopologyGenerated(topology, runtime);
        onClose();
    };

    return (
        <>
            {isOpen && (
                <div
                    role="dialog"
                    aria-label={AI_ASSISTANT_TITLE}
                    className="absolute inset-y-0 right-0 z-50 flex w-[min(22rem,100%)] flex-col border-l border-white/10 bg-[#111] font-sans shadow-2xl"
                >
                    <div className="flex shrink-0 items-center justify-between border-b border-white/10 px-4 py-3">
                        <div className="flex min-w-0 items-center gap-2.5">
                            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5">
                                <RobotIcon size={15} weight="regular" className="text-zinc-200" />
                            </span>
                            <div className="min-w-0">
                                <h2 className="text-sm font-semibold text-white">
                                    {AI_ASSISTANT_TITLE}
                                </h2>
                                <p className="text-[11px] leading-none text-zinc-500">{AI_ASSISTANT_SUBTITLE}</p>
                            </div>
                        </div>
                        <button
                            type="button"
                            onClick={onClose}
                            aria-label="Close"
                            className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
                        >
                            <XIcon size={16} weight="regular" />
                        </button>
                    </div>

                    <ImmersiveChatPanel
                        isOpen={isOpen}
                        onClose={onClose}
                        messages={messages}
                        onSendMessage={onSendMessage}
                        loading={loading || generating}
                        showComposer={isReplyMode}
                    />

                    {!isReplyMode && (
                        <div className="shrink-0 border-t border-white/10 px-3 py-3">
                            <ChatInterface
                                onTopologyGenerated={handleTopologyGenerated}
                                onRequestClarification={onRequestClarification}
                                onLoadingChange={setGenerating}
                            />
                        </div>
                    )}
                </div>
            )}

            {!isOpen && (
                <button
                    type="button"
                    onClick={onOpen}
                    aria-label="Ask assistant"
                    title="Ask assistant"
                    className="absolute bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-lg border border-white/15 bg-[#111]/90 px-3 py-2 text-xs font-medium text-zinc-300 shadow-lg backdrop-blur-md transition-colors hover:border-white/25 hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20"
                >
                    <RobotIcon size={14} weight="regular" />
                    Ask assistant
                </button>
            )}
        </>
    );
}
