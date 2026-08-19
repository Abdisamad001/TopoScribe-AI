import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Sparkles, MessageSquare, Maximize2, Minimize2, PanelRightOpen, PanelRightClose, AlertTriangle } from 'lucide-react';

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
    onClose: () => void;
    messages: { role: 'user' | 'assistant', content: string }[];
    onSendMessage: (message: string) => void;
    loading?: boolean;
}

export default function ImmersiveChatPanel({ isOpen, onClose, messages, onSendMessage, loading }: ImmersiveChatPanelProps) {
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

    if (!isOpen) return null;

    return (
        <div className="absolute right-0 top-0 h-full w-[450px] bg-[#0F1824]/95 backdrop-blur-xl border-l border-[#3DD6B5]/20 shadow-[-20px_0_50px_rgba(0,0,0,0.5)] z-50 flex flex-col transition-all duration-300 transform translate-x-0 animate-in slide-in-from-right">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-[#3DD6B5]/10 bg-[#142338]/50">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-br from-[#3DD6B5] to-[#2BC4A3] rounded-lg shadow-lg shadow-teal-500/20">
                        <Sparkles size={20} className="text-white" />
                    </div>
                    <div>
                        <h2 className="text-white font-bold text-lg tracking-wide">AI Assistant</h2>
                        <p className="text-[#94A8C0] text-xs">Design & Clarification</p>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    className="text-[#6B7A8F] hover:text-white hover:bg-white/10 p-2 rounded-lg transition-all"
                >
                    <X size={20} />
                </button>
            </div>

            {/* Chat Area */}
            <div className="flex-grow overflow-y-auto px-6 py-6 space-y-6 custom-scrollbar">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-50">
                        <MessageSquare size={48} className="text-[#3DD6B5]" />
                        <div className="space-y-2">
                            <p className="text-white font-medium">Ready to help!</p>
                            <p className="text-[#94A8C0] text-sm max-w-[250px]">
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
                                            ? 'bg-[#3DD6B5] text-[#0F1824] text-sm font-medium rounded-tr-sm'
                                            : isError
                                                ? 'bg-[#1C2F45] text-rose-200/90 text-xs border border-rose-400/20 border-l-2 border-l-rose-400/80 rounded-tl-sm'
                                                : 'bg-[#1C2F45] text-slate-200 text-sm border border-[#3DD6B5]/10 rounded-tl-sm'}
                                    `}
                                >
                                    {isError ? (
                                        <span className="flex items-start gap-2">
                                            <AlertTriangle size={14} className="text-rose-400 mt-0.5 shrink-0" />
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
                        <div className="bg-[#1C2F45] rounded-2xl rounded-tl-sm px-6 py-4 border border-[#3DD6B5]/10 flex gap-2 items-center">
                            <span className="w-2 h-2 bg-[#3DD6B5] rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="w-2 h-2 bg-[#3DD6B5] rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="w-2 h-2 bg-[#3DD6B5] rounded-full animate-bounce"></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-6 bg-[#142338] border-t border-[#3DD6B5]/10">
                <form onSubmit={handleSubmit} className="relative">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type your reply..."
                        disabled={loading}
                        className="w-full bg-[#0A0F1A] border border-[#3DD6B5]/20 rounded-xl py-4 pl-5 pr-14 text-white placeholder-[#6B7A8F] focus:outline-none focus:border-[#3DD6B5] focus:ring-1 focus:ring-[#3DD6B5] transition-all disabled:opacity-50"
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || loading}
                        className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 bg-[#3DD6B5] hover:bg-[#2BC4A3] text-[#0F1824] rounded-lg transition-all disabled:opacity-0 disabled:scale-90"
                    >
                        <Send size={18} />
                    </button>
                </form>
            </div>
        </div>
    );
}
