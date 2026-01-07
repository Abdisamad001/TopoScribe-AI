import React, { useState } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';

interface ChatInterfaceProps {
    onTopologyGenerated: (topology: any) => void;
}

export default function ChatInterface({ onTopologyGenerated }: ChatInterfaceProps) {
    const [prompt, setPrompt] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        setLoading(true);
        setError(null);

        try {
            const res = await fetch('/api/ai/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });

            const data = await res.json();

            if (data.success) {
                onTopologyGenerated(data.topology);
                setPrompt(''); // Clear input on success
            } else {
                setError(data.error || 'Failed to generate topology');
            }
        } catch (err) {
            setError('Network error occurred.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 w-full max-w-2xl px-4 z-50">
            <div className="relative rounded-2xl bg-[#1C2F45]/90 backdrop-blur-md border border-[#3DD6B5]/15 p-5 shadow-[0_-4px_24px_rgba(0,0,0,0.3)]">
                <form onSubmit={handleSubmit} className="relative w-full">
                    <input
                        type="text"
                        className="w-full bg-[#142338] border border-[#3DD6B5]/20 rounded-xl py-3.5 pl-4 pr-[140px] text-sm text-white placeholder-[#6B7A8F] focus:outline-none focus:border-[#3DD6B5] focus:ring-[3px] focus:ring-[#3DD6B5]/15 transition-all duration-300 min-h-[48px]"
                        placeholder="Describe your network... (e.g., 2 routers connected to a switch with 3 PCs)"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        disabled={loading}
                    />

                    <button
                        type="submit"
                        disabled={loading || !prompt}
                        className={`absolute right-1.5 top-1/2 transform -translate-y-1/2 bg-gradient-to-br from-[#3DD6B5] to-[#2BC4A3] text-white font-semibold text-sm px-5 py-2.5 rounded-lg flex items-center gap-2 transition-all duration-300 hover:-translate-y-[calc(50%+2px)] hover:shadow-[0_8px_20px_rgba(61,214,181,0.4)] hover:brightness-110 active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:translate-y-[-50%] disabled:hover:shadow-none`}
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
