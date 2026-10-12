/**
 * Core Data Models for TopoScribe AI
 * Defines the schema for Network Nodes, Links, Protocols, and Topology.
 */

export type NodeType = 'router' | 'switch' | 'host' | 'firewall';
export type ProtocolType = 'ospf' | 'bgp' | 'static' | 'vlan';

export interface NetworkInterface {
  id: string;
  name: string; // e.g., "GigabitEthernet0/1"
  ipAddress?: string; // e.g., "192.168.1.1"
  subnetMask?: string; // e.g., "255.255.255.0"
  connectedLinkId?: string;
}

export interface NetworkNode {
  id: string;
  type: NodeType;
  name: string; // Hostname
  x: number; // Visualization coordinate
  y: number; // Visualization coordinate
  interfaces: NetworkInterface[];
  config?: Record<string, any>; // Device specific config (arbitrary for now)
}

export interface Link {
  id: string;
  sourceNodeId: string;
  targetNodeId: string;
  sourceInterfaceId?: string;
  targetInterfaceId?: string;
  bandwidth?: number; // Mbps
  latency?: number; // ms
  type?: 'ethernet' | 'fiber' | 'serial';
}

export interface ProtocolConfig {
  id: string;
  type: ProtocolType;
  enabled: boolean;
  settings: Record<string, any>; // Protocol specific settings (e.g. Area ID for OSPF)
}

/** Optional data from backend / topology agent (VLAN catalog, etc.) */
export interface TopologyMetadata {
  vlans?: Array<{ id: number; name: string }>;
  /** Per-VLAN default gateway + mask (aligned with config_agent subnet allocation). */
  vlan_gateways?: Array<{
    vlan_id: number;
    gateway: string;
    mask: string;
    network?: string;
    prefix_len?: number;
    users?: number;
  }>;
  cabling?: Array<{
    link_id: string;
    a_id: string;
    a_port: string;
    b_id: string;
    b_port: string;
    cable: string;
  }>;
  configurations?: Record<string, any>;
  cisco_configs?: Record<string, string>;
  host_addresses?: Array<{
    id: string;
    label: string;
    interface: string;
    ip?: string | null;
    mask?: string | null;
    gateway?: string | null;
    vlan_id?: number | null;
  }>;
}

export interface GenerationRuntime {
  started_at_utc?: string;
  elapsed_ms?: number;
  elapsed_seconds?: number;
}

export interface Topology {
  id: string;
  name: string;
  nodes: NetworkNode[];
  links: Link[];
  protocols: ProtocolConfig[];
  version: number;
  lastUpdated: string; // ISO Date
  metadata?: TopologyMetadata;
  runtime?: GenerationRuntime;
}
