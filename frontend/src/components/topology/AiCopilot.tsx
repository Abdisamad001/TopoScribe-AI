'use client';

import React from 'react';
import { SparkleIcon, XIcon } from '@phosphor-icons/react';
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

    const handleTopologyGenerated = (topology: any, runtime?: any) => {
        onTopologyGenerated(topology, runtime);
        onClose();
    };

    return (
        <div className="pointer-events-none absolute inset-0 z-50">
            <div className="absolute bottom-6 right-6 left-6 flex flex-col items-end gap-3 sm:left-auto sm:w-full sm:max-w-sm">
                {isOpen && (
                    <div
                        role="dialog"
                        aria-label={AI_ASSISTANT_TITLE}
                        className="pointer-events-auto flex max-h-[70vh] w-full origin-bottom-right flex-col overflow-hidden rounded-2xl border border-chrome-navy/20 bg-chrome-surface/95 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-300"
                    >
                        <div className="flex shrink-0 items-center justify-between bg-chrome-elevated/40 px-6 py-5">
                            <div className="flex items-center gap-3">
                                <div className="rounded-lg bg-gradient-to-br from-chrome-navy to-chrome-navy p-2 shadow-lg shadow-chrome-navy/20">
                                    <SparkleIcon size={20} weight="regular" className="text-white" />
                                </div>
                                <div>
                                    <h2 className="font-[family-name:var(--font-orbitron)] text-lg font-bold tracking-wide text-white">
                                        {AI_ASSISTANT_TITLE}
                                    </h2>
                                    <p className="text-xs text-chrome-subtitle">{AI_ASSISTANT_SUBTITLE}</p>
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={onClose}
                                aria-label="Close"
                                className="rounded-lg p-2 text-chrome-muted transition-all hover:bg-white/10 hover:text-white"
                            >
                                <XIcon size={20} weight="regular" />
                            </button>
                        </div>

                        <ImmersiveChatPanel
                            isOpen={isOpen}
                            onClose={onClose}
                            messages={messages}
                            onSendMessage={onSendMessage}
                            loading={loading}
                            showComposer={isReplyMode}
                        />

                        {!isReplyMode && (
                            <div className="shrink-0 bg-chrome-elevated/80 px-6 py-5">
                                <ChatInterface
                                    onTopologyGenerated={handleTopologyGenerated}
                                    onRequestClarification={onRequestClarification}
                                />
                            </div>
                        )}
                    </div>
                )}

                {!isOpen && (
                    <button
                        type="button"
                        onClick={onOpen}
                        aria-label={AI_ASSISTANT_TITLE}
                        title={AI_ASSISTANT_TITLE}
                        className="pointer-events-auto flex size-14 items-center justify-center rounded-full border border-white/20 bg-chrome-navy text-white shadow-xl transition-all duration-300 hover:bg-chrome-navy-hover hover:brightness-110 active:scale-95"
                    >
                        <SparkleIcon size={22} weight="regular" />
                    </button>
                )}
            </div>
        </div>
    );
}
