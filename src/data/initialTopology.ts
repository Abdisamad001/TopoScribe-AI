import { Topology } from '@/types/network';

export const initialTopology: Topology = {
    id: 'topo-001',
    name: 'Simple Office Network',
    version: 1,
    lastUpdated: new Date().toISOString(),
    nodes: [
        {
            id: 'node-1',
            type: 'router',
            name: 'R1',
            x: 100,
            y: 100,
            interfaces: [
                { id: 'if-1', name: 'Gi0/0', ipAddress: '192.168.1.1', subnetMask: '255.255.255.0' }
            ]
        },
        {
            id: 'node-2',
            type: 'switch',
            name: 'SW1',
            x: 300,
            y: 100,
            interfaces: [
                { id: 'if-2', name: 'Gi0/1' }
            ]
        },
        {
            id: 'node-3',
            type: 'host',
            name: 'PC1',
            x: 300,
            y: 300,
            interfaces: [
                { id: 'if-3', name: 'Eth0', ipAddress: '192.168.1.10', subnetMask: '255.255.255.0' }
            ]
        }
    ],
    links: [
        {
            id: 'link-1',
            sourceNodeId: 'node-1',
            targetNodeId: 'node-2',
            bandwidth: 1000
        },
        {
            id: 'link-2',
            sourceNodeId: 'node-2',
            targetNodeId: 'node-3',
            bandwidth: 1000
        }
    ],
    protocols: [
        {
            id: 'proto-1',
            type: 'static',
            enabled: true,
            settings: {}
        }
    ]
};
