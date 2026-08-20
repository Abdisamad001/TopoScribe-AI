import React, { useState } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { generateDesign } from '@/lib/api';

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

    return (
        <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 w-full max-w-2xl px-4 z-50">
            <div className="relative rounded-2xl bg-[#2C2C34]/90 backdrop-blur-md border border-[#14213D]/15 p-5 shadow-[0_-4px_24px_rgba(0,0,0,0.3)]">
                <form onSubmit={handleSubmit} className="relative w-full">
                    <input
                        type="text"
                        className="w-full bg-[#212127] border border-[#14213D]/20 rounded-xl py-3.5 pl-4 pr-[184px] text-sm text-white placeholder-[#6B7A8F] focus:outline-none focus:border-[#14213D] focus:ring-[3px] focus:ring-[#14213D]/15 transition-all duration-300 min-h-[48px]"
                        placeholder="Describe your network... (e.g., 2 routers connected to a switch with 3 PCs)"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        disabled={loading}
                    />

                    <button
                        type="submit"
                        disabled={loading || !prompt}
                        className={`absolute right-1.5 top-1/2 transform -translate-y-1/2 bg-gradient-to-br from-[#14213D] to-[#14213D] text-white font-semibold text-sm px-5 py-2.5 rounded-lg flex items-center justify-center gap-2 min-w-[168px] transition-all duration-300 hover:-translate-y-[calc(50%+2px)] hover:shadow-[0_8px_20px_rgba(20,33,61,0.4)] hover:brightness-110 active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:translate-y-[-50%] disabled:hover:shadow-none`}
                    >
                        {loading ? (
                            <>
                                <Loader2 size={18} className="animate-spin" />
                                <span>Generating...</span>
                            </>
                        ) : (
                            <>
                                <Sparkles size={18} />
                                <span>Generate</span>
                            </>
                        )}
                    </button>
                </form>
            </div>

            {error && (
                <div className="absolute bottom-full mb-4 left-0 w-full text-center">
                    <span className="bg-red-500/10 text-red-300 text-xs px-4 py-2 rounded-full border border-red-500/20 shadow-lg backdrop-blur-sm">
                        {error}
                    </span>
                </div>
            )}
        </div>
    );
}
