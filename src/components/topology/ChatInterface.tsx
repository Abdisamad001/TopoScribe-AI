import React, { useState } from 'react';

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
            <form onSubmit={handleSubmit} className="relative shadow-2xl rounded-xl bg-white/90 dark:bg-zinc-900/90 backdrop-blur-md border border-gray-200 dark:border-zinc-700 p-2 flex gap-2">
                <input
                    type="text"
                    className="flex-grow bg-transparent border-none outline-none p-3 text-sm text-gray-800 dark:text-gray-100 placeholder-gray-400"
                    placeholder="Describe your network... (e.g., '2 routers connected to a switch with 3 PCs')"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    disabled={loading}
                />
                <button
                    type="submit"
                    disabled={loading || !prompt}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-2"
                >
                    {loading ? (
                        <>
                            <span className="animate-spin">⏳</span> Generating...
                        </>
                    ) : (
                        <>
                            <span>✨</span> Generate
                        </>
                    )}
                </button>
            </form>
            {error && (
                <div className="absolute bottom-full mb-2 left-0 w-full text-center">
                    <span className="bg-red-100 text-red-800 text-xs px-3 py-1 rounded-full border border-red-200 shadow-sm">
                        {error}
                    </span>
                </div>
            )}
        </div>
    );
}
