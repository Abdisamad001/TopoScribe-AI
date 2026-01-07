import { NextRequest, NextResponse } from 'next/server';
import { NetworkGraph } from '@/lib/simulation/graph';
import { NetworkNode, Link } from '@/types/network';

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const { nodes, links, sourceId, targetId } = body;

        if (!nodes || !links || !sourceId || !targetId) {
            return NextResponse.json({ error: 'Missing required parameters' }, { status: 400 });
        }

        const graph = NetworkGraph.fromTopology(nodes as NetworkNode[], links as Link[]);
        const result = graph.findPath(sourceId, targetId);

        return NextResponse.json(result);
    } catch (error) {
        console.error('Simulation error:', error);
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}
