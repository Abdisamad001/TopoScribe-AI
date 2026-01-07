import { NetworkNode, Link } from '@/types/network';

export interface GraphNode {
    id: string;
    neighbors: string[];
}

export class NetworkGraph {
    private adjacencyList: Map<string, string[]>;

    constructor() {
        this.adjacencyList = new Map();
    }

    addNode(nodeId: string) {
        if (!this.adjacencyList.has(nodeId)) {
            this.adjacencyList.set(nodeId, []);
        }
    }

    addEdge(sourceId: string, targetId: string) {
        this.adjacencyList.get(sourceId)?.push(targetId);
        this.adjacencyList.get(targetId)?.push(sourceId); // Undirected for physical link, though routing is directed. 
        // For simple L2/L3 reachability we assume bidirectional links for now.
    }

    // Build graph from topology data
    static fromTopology(nodes: NetworkNode[], links: Link[]): NetworkGraph {
        const graph = new NetworkGraph();

        nodes.forEach(node => graph.addNode(node.id));
        links.forEach(link => graph.addEdge(link.sourceNodeId, link.targetNodeId));

        return graph;
    }

    // Simple BFS for reachability
    findPath(startNodeId: string, endNodeId: string): string[] | null {
        const queue: string[][] = [[startNodeId]];
        const visited = new Set<string>();

        visited.add(startNodeId);

        while (queue.length > 0) {
            const path = queue.shift()!;
            const node = path[path.length - 1];

            if (node === endNodeId) {
                return path;
            }

            const neighbors = this.adjacencyList.get(node) || [];
            for (const neighbor of neighbors) {
                if (!visited.has(neighbor)) {
                    visited.add(neighbor);
                    const newPath = [...path, neighbor];
                    queue.push(newPath);
                }
            }
        }

        return null;
    }
}
