import React, { useState, useRef, useEffect } from 'react';
import { PaperPlaneRightIcon, WarningIcon } from '@phosphor-icons/react';

export const AI_ASSISTANT_TITLE = 'AI Assistant';
export const AI_ASSISTANT_SUBTITLE = 'Network design assistant';
export const REPLY_PLACEHOLDER = 'Type your reply...';

const FRIENDLY_ERROR_COPY =
    'Something went wrong generating your design. Please try again in a moment.';

function isTechnicalErrorMessage(content: string): boolean {
    const text = (content || '').trim();
    if (!text) return false;
    if (/^I encountered an error/i.test(text)) return true;
    if (/Error code:/i.test(text)) return true;
    if (/OpenAI call failed/i.test(text)) return true;
    if (/^\s*[\{\[]/.test(text) && /["']error["']/i.test(text)) return true;
    return false;
}

function getDisplayContent(content: string): string {
    if (isTechnicalErrorMessage(content)) return FRIENDLY_ERROR_COPY;
    return content;
}

interface ImmersiveChatPanelProps {
    isOpen: boolean;
    onClose?: () => void;
    messages: { role: 'user' | 'assistant', content: string }[];
    onSendMessage: (message: string) => void;
    loading?: boolean;
    showComposer?: boolean;
}

export default function ImmersiveChatPanel({ isOpen, messages, onSendMessage, loading, showComposer = true }: ImmersiveChatPanelProps) {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;
        onSendMessage(input);
        setInput('');
    };

    const submitOnEnter = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing) return;
        e.preventDefault();
        e.currentTarget.form?.requestSubmit();
    };

    if (!isOpen) return null;

    return (
        <div className="flex min-h-0 flex-1 flex-col font-sans">
            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4 custom-scrollbar">
                {messages.length === 0 && !loading ? (
                    <div className="flex flex-1 flex-col items-center justify-center px-4 text-center">
                        <img
                            src="/assitant-welcoming-image.svg"
                            alt=""
                            width={96}
                            height={96}
                            className="h-24 w-24 object-contain"
                        />
                        <p className="mt-3 text-sm font-medium text-white">Ready to help!</p>
                        <p className="mt-1 max-w-[200px] text-xs leading-relaxed text-zinc-500">
                            I can clarify requirements and refine your network design.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-3">
                    {messages.map((msg, i) => {
                        const isError = msg.role === 'assistant' && isTechnicalErrorMessage(msg.content);
                        const display = isError ? getDisplayContent(msg.content) : msg.content;
                        return (
                            <div
                                key={i}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div
                                    className={`
                                        max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed
                                        break-words [overflow-wrap:anywhere] max-h-64 overflow-y-auto
                                        ${msg.role === 'user'
                                            ? 'bg-zinc-200 text-zinc-900'
                                            : isError
                                                ? 'bg-white/5 text-rose-200/90 border border-rose-400/20'
                                                : 'bg-white/10 text-zinc-100'}
                                    `}
                                >
                                    {isError ? (
                                        <span className="flex items-start gap-2">
                                            <WarningIcon size={14} weight="regular" className="text-rose-400 mt-0.5 shrink-0" />
                                            <span>{display}</span>
                                        </span>
                                    ) : (
                                        display
                                    )}
                                </div>
                            </div>
                        );
                    })}
                    </div>
                )}
                {loading && (
                    <div className="flex justify-start">
                        <div className="flex items-center gap-1.5 rounded-xl border border-white/5 bg-white/5 px-4 py-2.5">
                            <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce"></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {showComposer && (
            <div className="shrink-0 border-t border-white/10 px-3 py-3">
                <form onSubmit={handleSubmit} className="flex flex-col gap-2">
                    <textarea
                        rows={3}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={submitOnEnter}
                        placeholder={REPLY_PLACEHOLDER}
                        aria-label={REPLY_PLACEHOLDER}
                        disabled={loading}
                        className="w-full resize-none rounded-xl border border-white/10 bg-transparent px-3 py-2.5 text-sm text-white placeholder-zinc-600 field-sizing-content min-h-[72px] max-h-[35vh] overflow-y-auto custom-scrollbar transition-colors focus:border-white/20 focus:outline-none disabled:opacity-50"
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || loading}
                        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                        <PaperPlaneRightIcon size={14} weight="regular" />
                        Send message
                    </button>
                </form>
            </div>
            )}
        </div>
    );
}
