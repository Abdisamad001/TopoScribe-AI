import React, { useState } from 'react';
import { SpinnerIcon, PaperPlaneRightIcon } from '@phosphor-icons/react';
import { generateDesign } from '@/lib/api';

export const GENERATE_PLACEHOLDER = 'Describe your network topology...';
export const GENERATE_ACTION_LABEL = 'Generate';

interface ChatInterfaceProps {
    onTopologyGenerated: (topology: any, runtime?: any) => void;
    onRequestClarification: (prompt: string, questions: string[]) => void;
    onLoadingChange?: (loading: boolean) => void;
}

export default function ChatInterface({ onTopologyGenerated, onRequestClarification, onLoadingChange }: ChatInterfaceProps) {
    const [prompt, setPrompt] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        setLoading(true);
        onLoadingChange?.(true);
        setError(null);

        try {
            const data = await generateDesign(prompt);

            if (data.status === 'complete' && data.topology) {
                // Seed chat so reopening Ask assistant still shows this turn.
                onRequestClarification(prompt, [
                    'Design generated. Re-open Ask assistant anytime to see this chat again.',
                ]);
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
            onLoadingChange?.(false);
        }
    };

    const submitOnEnter = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing) return;
        e.preventDefault();
        e.currentTarget.form?.requestSubmit();
    };

    return (
        <div className="w-full">
            {error && (
                <div className="mb-2 text-center">
                    <span className="inline-block rounded-md border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-xs text-red-300">
                        {error}
                    </span>
                </div>
            )}
            <form onSubmit={handleSubmit} className="flex w-full flex-col gap-2">
                <textarea
                    rows={3}
                    className="w-full min-h-[72px] resize-none rounded-xl border border-white/10 bg-transparent px-3 py-2.5 text-sm text-white placeholder-zinc-600 field-sizing-content max-h-[35vh] overflow-y-auto custom-scrollbar transition-colors focus:border-white/20 focus:outline-none disabled:opacity-50"
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
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-40"
                >
                    {loading ? (
                        <>
                            <SpinnerIcon size={16} weight="regular" className="animate-spin" />
                            <span>Generating...</span>
                        </>
                    ) : (
                        <>
                            <PaperPlaneRightIcon size={14} weight="regular" />
                            <span>{GENERATE_ACTION_LABEL}</span>
                        </>
                    )}
                </button>
            </form>
        </div>
    );
}
