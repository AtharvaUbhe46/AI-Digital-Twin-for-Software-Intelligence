import React, { useCallback, useMemo, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Handle,
  NodeProps,
  Node,
  Edge,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import {
  FileCode,
  Boxes,
  Code2,
  Package,
  Globe,
  Folder,
  FolderGit2,
  Variable,
  Layers,
  Database,
} from 'lucide-react';
import { GraphNode as APIGraphNode, GraphEdge as APIGraphEdge } from '../../types';
import { useTheme } from '../../context/ThemeContext';

interface GraphCanvasProps {
  nodes: APIGraphNode[];
  edges: APIGraphEdge[];
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
  direction?: 'TB' | 'LR';
}

// ─── Custom Node Component ───────────────────────────────────────────────────

const getNodeIcon = (type: string) => {
  switch (type) {
    case 'file':
      return <FileCode className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />;
    case 'class':
      return <Boxes className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />;
    case 'function':
    case 'method':
      return <Code2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />;
    case 'package':
      return <Package className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />;
    case 'api_endpoint':
    case 'endpoint':
      return <Globe className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />;
    case 'database_entity':
    case 'db':
      return <Database className="w-3.5 h-3.5 text-pink-600 dark:text-pink-400" />;
    case 'directory':
    case 'module':
      return <Folder className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />;
    case 'repository':
      return <FolderGit2 className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />;
    case 'variable':
      return <Variable className="w-3.5 h-3.5 text-pink-600 dark:text-pink-400" />;
    default:
      return <Layers className="w-3.5 h-3.5 text-slate-500 dark:text-gray-400" />;
  }
};

const getNodeTypeBadge = (type: string) => {
  switch (type) {
    case 'file':
      return 'bg-cyan-50 text-cyan-700 border-cyan-200 dark:bg-cyan-950/80 dark:text-cyan-300 dark:border-cyan-800/80';
    case 'class':
      return 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/80 dark:text-purple-300 dark:border-purple-800/80';
    case 'function':
    case 'method':
      return 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/80 dark:text-blue-300 dark:border-blue-800/80';
    case 'package':
      return 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/80 dark:text-amber-300 dark:border-amber-800/80';
    case 'api_endpoint':
    case 'endpoint':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/80 dark:text-emerald-300 dark:border-emerald-800/80';
    case 'database_entity':
    case 'db':
      return 'bg-pink-50 text-pink-700 border-pink-200 dark:bg-pink-950/80 dark:text-pink-300 dark:border-pink-800/80';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700';
  }
};

const getMethodColor = (method: string) => {
  switch (method?.toUpperCase()) {
    case 'GET':
      return 'bg-blue-500 text-white';
    case 'POST':
      return 'bg-emerald-500 text-white';
    case 'PUT':
      return 'bg-amber-500 text-white';
    case 'DELETE':
      return 'bg-rose-500 text-white';
    case 'PATCH':
      return 'bg-purple-500 text-white';
    default:
      return 'bg-slate-500 text-white';
  }
};

const CustomEntityNode: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeType = (data.node_type as string) || 'file';
  const badgeClass = getNodeTypeBadge(nodeType);
  const metadata = (data.node_metadata as Record<string, any>) || {};
  const isEndpoint = nodeType === 'api_endpoint' || nodeType === 'endpoint';
  const httpMethod = metadata.http_method || (isEndpoint && String(data.label).split(' ')[0]) || '';

  return (
    <div
      className={`px-3 py-2.5 rounded-xl bg-white dark:bg-[#111827]/95 border transition-all duration-150 select-none shadow-md min-w-[170px] max-w-[260px] ${
        selected
          ? 'border-cyan-500 ring-2 ring-cyan-500/40 shadow-cyan-500/25'
          : 'border-slate-200 dark:border-gray-800 hover:border-slate-300 dark:hover:border-gray-700 hover:bg-slate-50 dark:hover:bg-[#162032]'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-cyan-500 !border-slate-200 dark:!border-gray-900" />
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-cyan-500 !border-slate-200 dark:!border-gray-900" />

      <div className="flex items-center justify-between mb-1.5 gap-2">
        <div className="flex items-center space-x-1.5 overflow-hidden">
          {getNodeIcon(nodeType)}
          <span className="font-semibold text-xs text-slate-900 dark:text-gray-100 truncate tracking-tight">
            {data.label as string}
          </span>
        </div>
        {isEndpoint && httpMethod ? (
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ${getMethodColor(httpMethod)}`}>
            {httpMethod}
          </span>
        ) : (
          <span className={`text-[9px] px-1.5 py-0.5 rounded border uppercase font-mono font-medium shrink-0 ${badgeClass}`}>
            {nodeType.replace('_', ' ')}
          </span>
        )}
      </div>

      {Boolean(data.file_path) && (
        <p className="text-[10px] text-slate-500 dark:text-gray-400 truncate font-mono">
          {String(data.file_path)}
        </p>
      )}

      {Boolean(data.subtext) && (
        <p className="text-[10px] text-slate-500 dark:text-gray-400 mt-1 truncate">
          {String(data.subtext)}
        </p>
      )}

      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-blue-500 !border-slate-200 dark:!border-gray-900" />
      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-blue-500 !border-slate-200 dark:!border-gray-900" />
    </div>
  );
};

// ─── Automated Dagre Layout Engine ───────────────────────────────────────────

const nodeWidth = 200;
const nodeHeight = 65;

const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 35, ranksep: 55 });

  const validNodeIds = new Set(nodes.map((n) => n.id));
  const validEdges = edges.filter(
    (e) => validNodeIds.has(e.source) && validNodeIds.has(e.target)
  );

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  validEdges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const posX = nodeWithPosition?.x ?? 0;
    const posY = nodeWithPosition?.y ?? 0;
    return {
      ...node,
      targetPosition: direction === 'TB' ? Position.Top : Position.Left,
      sourcePosition: direction === 'TB' ? Position.Bottom : Position.Right,
      position: {
        x: posX - nodeWidth / 2,
        y: posY - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges: validEdges };
};

// ─── Edge Relationship Colors ────────────────────────────────────────────────

const getEdgeColor = (relType: string, isDark: boolean) => {
  switch (relType) {
    case 'IMPORTS':
      return isDark ? '#38BDF8' : '#0284C7'; // Cyan
    case 'CALLS':
      return isDark ? '#60A5FA' : '#2563EB'; // Blue
    case 'EXTENDS':
      return isDark ? '#C084FC' : '#9333EA'; // Purple
    case 'DEPENDS_ON':
      return isDark ? '#FBBF24' : '#D97706'; // Amber
    case 'ROUTES_TO':
    case 'HANDLED_BY':
      return isDark ? '#34D399' : '#059669'; // Emerald
    case 'ACCESSES':
      return isDark ? '#F472B6' : '#DB2777'; // Pink
    case 'BELONGS_TO':
      return isDark ? '#818CF8' : '#4F46E5'; // Indigo
    case 'EXPOSES':
      return isDark ? '#2DD4BF' : '#0D9488'; // Teal
    case 'CONTAINS':
      return isDark ? '#64748B' : '#94A3B8'; // Slate
    default:
      return isDark ? '#94A3B8' : '#64748B'; // Gray
  }
};

// ─── Main Graph Canvas ───────────────────────────────────────────────────────

export const InteractiveGraphCanvas: React.FC<GraphCanvasProps> = ({
  nodes: rawNodes,
  edges: rawEdges,
  selectedNodeId,
  onSelectNode,
  direction = 'TB',
}) => {
  const { isDark } = useTheme();
  const nodeTypes = useMemo(() => ({ customEntity: CustomEntityNode }), []);

  // Compute Dagre layout ONLY when nodes, edges, or direction change.
  // CRITICAL: Do NOT include selectedNodeId here to prevent layout recalculations on click!
  const layoutedElements = useMemo(() => {
    if (!rawNodes || rawNodes.length === 0) {
      return { nodes: [] as Node[], edges: [] as Edge[] };
    }

    const baseNodes: Node[] = rawNodes.map((n) => {
      let subtext = '';
      if (n.node_metadata?.http_method && n.node_metadata?.path) {
        subtext = `${n.node_metadata.http_method} ${n.node_metadata.path}`;
      } else if (n.node_metadata?.http_method) {
        subtext = `${n.node_metadata.http_method}`;
      } else if (n.line_number) {
        subtext = `Line ${n.line_number}`;
      } else if (n.node_metadata?.version) {
        subtext = `v${n.node_metadata.version}`;
      }

      return {
        id: n.id,
        type: 'customEntity',
        data: {
          label: n.name,
          node_type: n.node_type,
          file_path: n.file_path,
          subtext,
          node_metadata: n.node_metadata,
        },
        position: { x: 0, y: 0 },
      };
    });

    const nodeIdSet = new Set(rawNodes.map((n) => n.id));
    const baseEdges: Edge[] = rawEdges
      .filter((e) => nodeIdSet.has(e.source_id) && nodeIdSet.has(e.target_id))
      .map((e, idx) => ({
        id: `e-${e.source_id}-${e.target_id}-${e.relationship_type}-${idx}`,
        source: e.source_id,
        target: e.target_id,
        label: e.relationship_type,
        data: { rel_type: e.relationship_type },
        animated: ['ROUTES_TO', 'HANDLED_BY', 'CALLS', 'ACCESSES'].includes(e.relationship_type),
      }));

    return getLayoutedElements(baseNodes, baseEdges, direction);
  }, [rawNodes, rawEdges, direction]);

  // Apply selected state to nodes without triggering Dagre layout
  const displayNodes = useMemo(() => {
    return layoutedElements.nodes.map((node) => ({
      ...node,
      selected: node.id === selectedNodeId,
    }));
  }, [layoutedElements.nodes, selectedNodeId]);

  // Apply edge highlighting based on selectedNodeId and theme without recomputing layout
  const displayEdges = useMemo(() => {
    return layoutedElements.edges.map((e) => {
      const relType = (e.data?.rel_type as string) || (e.label as string) || '';
      const color = getEdgeColor(relType, isDark);
      const isSelected = Boolean(selectedNodeId && (e.source === selectedNodeId || e.target === selectedNodeId));

      return {
        ...e,
        style: {
          stroke: isSelected ? (isDark ? '#38BDF8' : '#0284C7') : color,
          strokeWidth: isSelected ? 2.5 : 1.2,
          opacity: selectedNodeId ? (isSelected ? 1.0 : 0.25) : 0.85,
        },
        labelStyle: {
          fill: isSelected ? (isDark ? '#38BDF8' : '#0284C7') : (isDark ? '#94A3B8' : '#475569'),
          fontSize: 9,
          fontWeight: 600,
          fontFamily: 'monospace',
        },
        labelBgStyle: {
          fill: isDark ? '#0B0F17' : '#FFFFFF',
          fillOpacity: 0.9,
          rx: 4,
          ry: 4,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isSelected ? (isDark ? '#38BDF8' : '#0284C7') : color,
          width: 14,
          height: 14,
        },
      };
    });
  }, [layoutedElements.edges, selectedNodeId, isDark]);

  const [nodes, setNodes, onNodesChange] = useNodesState(displayNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(displayEdges);

  // Sync state when displayNodes/displayEdges update
  useEffect(() => {
    setNodes(displayNodes);
  }, [displayNodes, setNodes]);

  useEffect(() => {
    setEdges(displayEdges);
  }, [displayEdges, setEdges]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onSelectNode(node.id === selectedNodeId ? null : node.id);
    },
    [onSelectNode, selectedNodeId]
  );

  const handlePaneClick = useCallback(() => {
    onSelectNode(null);
  }, [onSelectNode]);

  if (rawNodes.length === 0) {
    return (
      <div className="w-full h-full min-h-[560px] bg-slate-50 dark:bg-[#0B0F17] rounded-2xl border border-slate-200 dark:border-gray-800 flex flex-col items-center justify-center p-8 text-center space-y-3 transition-colors">
        <div className="w-12 h-12 rounded-xl bg-slate-200 dark:bg-gray-800/60 border border-slate-300 dark:border-gray-700/50 flex items-center justify-center text-slate-500 dark:text-gray-400">
          <Layers className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-semibold text-slate-800 dark:text-gray-200">No Graph Entities Match This Filter</h4>
        <p className="text-xs text-slate-500 dark:text-gray-400 max-w-sm">
          No matching nodes were found in the selected repository. Try selecting &quot;All Entities&quot; or re-analyzing the code.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-[560px] bg-slate-50 dark:bg-[#0B0F17] rounded-2xl border border-slate-200 dark:border-gray-800 relative overflow-hidden transition-colors">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.15}
        maxZoom={2.5}
        defaultEdgeOptions={{ type: 'smoothstep' }}
        className="touch-none"
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color={isDark ? '#1F2937' : '#CBD5E1'} />
        <Controls
          className="!bg-white dark:!bg-[#111827] !border-slate-200 dark:!border-gray-800 !rounded-xl !shadow-xl [&>button]:!bg-white dark:[&>button]:!bg-[#111827] [&>button]:!border-slate-200 dark:[&>button]:!border-gray-800 [&>button]:!text-slate-700 dark:[&>button]:!text-gray-300 hover:[&>button]:!bg-slate-100 dark:hover:[&>button]:!bg-gray-800"
        />
        <MiniMap
          nodeColor={(n) => {
            const type = (n.data?.node_type as string) || '';
            if (type === 'file') return '#0EA5E9';
            if (type === 'class') return '#A855F7';
            if (type === 'package') return '#F59E0B';
            if (type === 'api_endpoint' || type === 'endpoint') return '#10B981';
            if (type === 'database_entity' || type === 'db') return '#EC4899';
            return '#64748B';
          }}
          className="!bg-white/95 dark:!bg-[#111827]/90 !border-slate-200 dark:!border-gray-800 !rounded-xl !overflow-hidden shadow-md"
          maskColor={isDark ? 'rgba(11, 15, 23, 0.7)' : 'rgba(241, 245, 249, 0.7)'}
        />
      </ReactFlow>
    </div>
  );
};
