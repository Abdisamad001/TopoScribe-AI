import React, { useState, useRef, useEffect } from 'react';
import { PaperPlaneRightIcon, ChatIcon, WarningIcon } from '@phosphor-icons/react';

export const AI_ASSISTANT_TITLE = 'AI Assistant';
export const AI_ASSISTANT_SUBTITLE = 'Design & Clarification';
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
        <div className="flex min-h-0 flex-col font-sans">
            {/* Chat Area */}
            <div className="min-h-0 overflow-y-auto px-6 py-5 space-y-5 custom-scrollbar">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center text-center space-y-1.5 py-1">
                        <div className="rounded-lg bg-chrome-navy/30 p-2.5">
                            <ChatIcon size={48} weight="regular" className="text-white" />
                        </div>
                        <div className="space-y-1">
                            <p className="text-sm font-semibold text-white">Ready to help!</p>
                            <p className="text-xs font-normal text-slate-400 max-w-[250px]">
                                I can clarify requirements and refine your network design.
                            </p>
                        </div>
                    </div>
                ) : (
                    messages.map((msg, i) => {
                        const isError = msg.role === 'assistant' && isTechnicalErrorMessage(msg.content);
                        const display = isError ? getDisplayContent(msg.content) : msg.content;
                        return (
                            <div
                                key={i}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div
                                    className={`
                                        max-w-[85%] rounded-2xl px-5 py-4 leading-relaxed shadow-lg
                                        break-words [overflow-wrap:anywhere] max-h-64 overflow-y-auto
                                        ${msg.role === 'user'
                                            ? 'bg-[#14213D] text-white text-sm font-medium rounded-tr-sm'
                                            : isError
                                                ? 'bg-[#2C2C34] text-rose-200/90 text-xs border border-rose-400/20 border-l-2 border-l-rose-400/80 rounded-tl-sm'
                                                : 'bg-[#2C2C34] text-slate-200 text-sm border border-[#14213D]/10 rounded-tl-sm'}
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
                    })
                )}
                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-[#2C2C34] rounded-2xl rounded-tl-sm px-6 py-4 border border-[#14213D]/10 flex gap-2 items-center">
                            <span className="w-2 h-2 bg-white rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="w-2 h-2 bg-white rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="w-2 h-2 bg-white rounded-full animate-bounce"></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {showComposer && (
            <div className="shrink-0 bg-[#212127] px-6 py-5">
                <form onSubmit={handleSubmit} className="relative">
                    <textarea
                        rows={1}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={submitOnEnter}
                        placeholder={REPLY_PLACEHOLDER}
                        aria-label={REPLY_PLACEHOLDER}
                        disabled={loading}
                        className="w-full bg-[#0F0F11] border border-[#14213D]/20 rounded-xl py-4 pl-5 pr-14 text-white placeholder-[#6B7A8F] focus:outline-none focus:border-chrome-navy focus:ring-2 focus:ring-chrome-navy/40 focus:shadow-lg focus:shadow-chrome-navy/25 transition-all duration-300 disabled:opacity-50 field-sizing-content resize-none max-h-[35vh] overflow-y-auto custom-scrollbar"
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || loading}
                        className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 bg-[#14213D] hover:bg-[#14213D] text-white border border-white/20 rounded-lg transition-all disabled:opacity-0 disabled:scale-90"
                    >
                        <PaperPlaneRightIcon size={18} weight="regular" />
                    </button>
                </form>
            </div>
            )}
        </div>
    );
}
