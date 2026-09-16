import React, { useState } from 'react';
import { SparkleIcon, SpinnerIcon } from '@phosphor-icons/react';
import { generateDesign } from '@/lib/api';

export const GENERATE_PLACEHOLDER =
    'Describe your network... (e.g., 2 routers connected to a switch with 3 PCs)';
export const GENERATE_ACTION_LABEL = 'Generate';

interface ChatInterfaceProps {
    onTopologyGenerated: (topology: any, runtime?: any) => void;
    onRequestClarification: (prompt: string, questions: string[]) => void;
}

export default function ChatInterface({ onTopologyGenerated, onRequestClarification }: ChatInterfaceProps) {
    const [prompt, setPrompt] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        setLoading(true);
        setError(null);

        try {
            const data = await generateDesign(prompt);

            if (data.status === 'complete' && data.topology) {
                onTopologyGenerated(data.topology, data.runtime);
                setPrompt(''); // Clear input on success
            } else if (data.status === 'needs_clarification') {
                onRequestClarification(prompt, data.questions || []);
                setPrompt('');
            } else if (data.status === 'generation_failed') {
                setError(
                    typeof data.message === 'string'
                        ? data.message
                        : 'Topology generation did not complete. Try again.'
                );
            } else {
                setError('Failed to generate topology');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Network error occurred.');
        } finally {
            setLoading(false);
        }
    };

    const submitOnEnter = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing) return;
        e.preventDefault();
        e.currentTarget.form?.requestSubmit();
    };

    return (
        <div className="w-full rounded-xl border border-chrome-navy/40 bg-chrome-charcoal p-3 shadow-lg shadow-black/40">
            {error && (
                <div className="mb-3 text-center">
                    <span className="bg-red-500/10 text-red-300 text-xs px-4 py-2 rounded-full border border-red-500/20 shadow-lg backdrop-blur-sm">
                        {error}
                    </span>
                </div>
            )}
            <form onSubmit={handleSubmit} className="flex w-full flex-col gap-2">
                <textarea
                    rows={1}
                    className="w-full bg-[#212127] border border-chrome-navy/40 rounded-xl py-3.5 px-4 text-sm text-white placeholder-[#6B7A8F] focus:outline-none focus:border-chrome-navy focus:ring-2 focus:ring-chrome-navy/40 focus:shadow-lg focus:shadow-chrome-navy/25 transition-all duration-300 min-h-[48px] field-sizing-content resize-none max-h-[35vh] overflow-y-auto custom-scrollbar"
                    placeholder={GENERATE_PLACEHOLDER}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={submitOnEnter}
                    disabled={loading}
                    aria-label={GENERATE_PLACEHOLDER}
                />

                <button
                    type="submit"
                    disabled={loading || !prompt}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-br from-[#14213D] to-[#14213D] px-5 py-2.5 text-sm font-semibold text-white transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_8px_20px_rgba(20,33,61,0.4)] hover:brightness-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:translate-y-0 disabled:hover:shadow-none"
                >
                    {loading ? (
                        <>
                            <SpinnerIcon size={18} weight="regular" className="animate-spin" />
                            <span>Generating...</span>
                        </>
                    ) : (
                        <>
                            <SparkleIcon size={18} weight="regular" />
                            <span>{GENERATE_ACTION_LABEL}</span>
                        </>
                    )}
                </button>
            </form>
        </div>
    );
}
