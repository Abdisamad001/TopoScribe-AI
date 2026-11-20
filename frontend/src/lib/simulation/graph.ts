import { NetworkNode, Link } from '@/types/network';

export interface GraphNode {
    id: string;
    neighbors: string[];
}

export class NetworkGraph {
    private adjacencyList: Map<string, string[]>;
    private nodesMap: Map<string, NetworkNode>;

    constructor(nodes: NetworkNode[]) {
        this.adjacencyList = new Map();
        this.nodesMap = new Map(nodes.map(n => [n.id, n]));
    }

    addNode(nodeId: string) {
        if (!this.adjacencyList.has(nodeId)) {
            this.adjacencyList.set(nodeId, []);
        }
    }

    addEdge(sourceId: string, targetId: string) {
        this.adjacencyList.get(sourceId)?.push(targetId);
        this.adjacencyList.get(targetId)?.push(sourceId);
    }

    static fromTopology(nodes: NetworkNode[], links: Link[]): NetworkGraph {
        const graph = new NetworkGraph(nodes);

        nodes.forEach(node => graph.addNode(node.id));
        links.forEach(link => graph.addEdge(link.sourceNodeId, link.targetNodeId));

        return graph;
    }

    // Check for duplicate IPs 
    private validateUniqueIps(): { valid: boolean; duplicateIp?: string; nodes?: string[] } {
        const ipMap = new Map<string, string[]>();

        for (const node of this.nodesMap.values()) {
            if (node.type === 'router' || node.type === 'host') {
                for (const iface of node.interfaces) {
                    const ip = iface.ipAddress?.trim();
                    if (ip) {
                        if (!ipMap.has(ip)) {
                            ipMap.set(ip, []);
                        }
                        ipMap.get(ip)!.push(node.name);
                    }
                }
            }
        }

        for (const [ip, nodes] of ipMap.entries()) {
            if (nodes.length > 1) {
                return { valid: false, duplicateIp: ip, nodes };
            }
        }

        return { valid: true };
    }

    // Enhanced BFS for reachability with Validation
    findPath(startNodeId: string, endNodeId: string): { success: boolean; path: string[]; failureNodeId?: string; failureReason?: string } {
        // 0. Global Check: Duplicate IPs
        const ipCheck = this.validateUniqueIps();
        if (!ipCheck.valid) {
            return {
                success: false,
                path: [],
                failureReason: `Network Configuration Error: Duplicate IP Address ${ipCheck.duplicateIp} detected on devices: ${ipCheck.nodes?.join(', ')}`
            };
        }

        const queue: { path: string[] }[] = [{ path: [startNodeId] }];
        const visited = new Set<string>();
        visited.add(startNodeId);

        while (queue.length > 0) {
            const { path } = queue.shift()!;
            const currentNodeId = path[path.length - 1];
            const currentNode = this.nodesMap.get(currentNodeId);

            // --- VALIDATION LOGIC ---
            // If the node is L3 (Router/Host) it MUST have an IP address configured
            if (currentNode && (currentNode.type === 'router' || currentNode.type === 'host')) {
                const hasIp = currentNode.interfaces.some(i => i.ipAddress && i.ipAddress.trim() !== '');
                if (!hasIp) {
                    return {
                        success: false,
                        path: path, // Path up to failure
                        failureNodeId: currentNodeId,
                        failureReason: `Packet Lost at ${currentNode.name}! Missing IP Configuration.`
                    };
                }

                // Basic check for valid IP format (simplified)
                const ip = currentNode.interfaces.find(i => i.ipAddress)?.ipAddress;
                if (ip && !/^(\d{1,3}\.){3}\d{1,3}$/.test(ip)) {
                    return {
                        success: false,
                        path: path,
                        failureNodeId: currentNodeId,
                        failureReason: `Packet Lost at ${currentNode.name}! Invalid IP Format: ${ip}`
                    };
                }
            }
            // ------------------------

            if (currentNodeId === endNodeId) {
                // Check destination constraints
                return { success: true, path };
            }

            const neighbors = this.adjacencyList.get(currentNodeId) || [];
            for (const neighbor of neighbors) {
                if (!visited.has(neighbor)) {
                    visited.add(neighbor);
                    queue.push({ path: [...path, neighbor] });
                }
            }
        }

        return { success: false, path: [], failureReason: 'No physical path found.' };
    }
}
