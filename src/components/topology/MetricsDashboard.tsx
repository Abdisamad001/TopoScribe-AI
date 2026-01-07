import React, { useState, useEffect } from 'react';

export default function MetricsDashboard() {
    // Mock data for demonstration - in a real app, this would be fetched from backend analytics
    const [metrics, setMetrics] = useState({
        simulationsRun: 0,
        successfulPings: 0,
        nodescreated: 0,
        manualTimeSaved: 0 // in minutes
    });

    useEffect(() => {
        // Simulate fetching metrics or aggregating from local session storage
        // For now, let's just make up some dynamic looking numbers based on session time or random
        const interval = setInterval(() => {
            setMetrics(prev => ({
                ...prev,
                simulationsRun: prev.simulationsRun + Math.floor(Math.random() * 2),
                successfulPings: prev.successfulPings + Math.floor(Math.random() * 1),
                nodescreated: 12, // Static for this demo
                manualTimeSaved: 12 * 15 // 15 mins per node approx
            }));
        }, 5000);

        return () => clearInterval(interval);
    }, []);

    const successRate = metrics.simulationsRun > 0
        ? Math.round((metrics.successfulPings / metrics.simulationsRun) * 100)
        : 100;

    return (
        <div className="absolute top-20 right-4 w-64 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-md rounded-xl shadow-lg border border-gray-200 dark:border-zinc-700 p-4 z-40 transition-all hover:w-72 group">
            <h3 className="text-xs font-bold uppercase text-gray-500 mb-3 flex items-center gap-2">
                📊 Live Metrics
            </h3>

            <div className="grid grid-cols-1 gap-3">
                <div className="bg-blue-50 dark:bg-zinc-800 p-2 rounded">
                    <div className="text-xs text-gray-500">Est. Time Saved</div>
                    <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
                        {Math.floor(metrics.manualTimeSaved / 60)}h {metrics.manualTimeSaved % 60}m
                    </div>
                    <div className="text-[10px] text-gray-400">vs. Packet Tracer manual config</div>
                </div>

                <div className="flex gap-2">
                    <div className="bg-green-50 dark:bg-zinc-800 p-2 rounded flex-1">
                        <div className="text-xs text-gray-500">Simulations</div>
                        <div className="text-lg font-bold text-green-600 dark:text-green-400">
                            {metrics.simulationsRun}
                        </div>
                    </div>
                    <div className="bg-purple-50 dark:bg-zinc-800 p-2 rounded flex-1">
                        <div className="text-xs text-gray-500">Success Rate</div>
                        <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
                            {successRate}%
                        </div>
                    </div>
                </div>

                <div className="bg-gray-50 dark:bg-zinc-800 p-2 rounded">
                    <div className="text-xs text-gray-500">Design Efficiency Score</div>
                    <div className="text-2xl font-bold text-gray-800 dark:text-gray-100 mt-1">
                        A+
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                        <div className="bg-gradient-to-r from-green-400 to-blue-500 h-1.5 rounded-full w-[95%]"></div>
                    </div>
                </div>
            </div>
        </div>
    );
}
