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
} from 'lucide-react';
import { GraphNode as APIGraphNode, GraphEdge as APIGraphEdge } from '../../types';

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
      return <FileCode className="w-3.5 h-3.5 text-cyan-400" />;
    case 'class':
      return <Boxes className="w-3.5 h-3.5 text-purple-400" />;
    case 'function':
    case 'method':
      return <Code2 className="w-3.5 h-3.5 text-blue-400" />;
    case 'package':
      return <Package className="w-3.5 h-3.5 text-amber-400" />;
    case 'api_endpoint':
      return <Globe className="w-3.5 h-3.5 text-emerald-400" />;
    case 'directory':
    case 'module':
      return <Folder className="w-3.5 h-3.5 text-slate-400" />;
    case 'repository':
      return <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />;
    case 'variable':
      return <Variable className="w-3.5 h-3.5 text-pink-400" />;
    default:
      return <Layers className="w-3.5 h-3.5 text-gray-400" />;
  }
};

const getNodeTypeBadge = (type: string) => {
  switch (type) {
    case 'file':
      return 'bg-cyan-950/80 text-cyan-300 border-cyan-800/80';
    case 'class':
      return 'bg-purple-950/80 text-purple-300 border-purple-800/80';
    case 'function':
    case 'method':
      return 'bg-blue-950/80 text-blue-300 border-blue-800/80';
    case 'package':
      return 'bg-amber-950/80 text-amber-300 border-amber-800/80';
    case 'api_endpoint':
      return 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80';
    default:
      return 'bg-gray-800 text-gray-300 border-gray-700';
  }
};

const CustomEntityNode: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeType = (data.node_type as string) || 'file';
  const badgeClass = getNodeTypeBadge(nodeType);

  return (
    <div
      className={`px-3 py-2.5 rounded-xl bg-[#111827]/95 border transition-all duration-200 select-none shadow-lg min-w-[170px] max-w-[260px] ${
        selected
          ? 'border-cyan-400 ring-2 ring-cyan-400/30 shadow-cyan-500/20'
          : 'border-gray-800 hover:border-gray-700 hover:bg-[#162032]'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-cyan-500 !border-gray-900" />
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-cyan-500 !border-gray-900" />

      <div className="flex items-center justify-between mb-1.5 gap-2">
        <div className="flex items-center space-x-1.5 overflow-hidden">
          {getNodeIcon(nodeType)}
          <span className="font-semibold text-xs text-gray-100 truncate tracking-tight">
            {data.label as string}
          </span>
        </div>
        <span className={`text-[9px] px-1.5 py-0.5 rounded border uppercase font-mono font-medium shrink-0 ${badgeClass}`}>
          {nodeType.replace('_', ' ')}
        </span>
      </div>

      {Boolean(data.file_path) && (
        <p className="text-[10px] text-gray-400 truncate font-mono">
          {String(data.file_path)}
        </p>
      )}

      {Boolean(data.subtext) && (
        <p className="text-[10px] text-gray-400 mt-1 truncate">
          {String(data.subtext)}
        </p>
      )}

      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-blue-500 !border-gray-900" />
      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-blue-500 !border-gray-900" />
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
  dagreGraph.setGraph({ rankdir: direction, nodesep: 40, ranksep: 60 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: direction === 'TB' ? Position.Top : Position.Left,
      sourcePosition: direction === 'TB' ? Position.Bottom : Position.Right,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

// ─── Edge Relationship Colors ────────────────────────────────────────────────

const getEdgeColor = (relType: string) => {
  switch (relType) {
    case 'IMPORTS':
      return '#38BDF8'; // Cyan
    case 'CALLS':
      return '#60A5FA'; // Blue
    case 'EXTENDS':
      return '#C084FC'; // Purple
    case 'DEPENDS_ON':
      return '#FBBF24'; // Amber
    case 'ROUTES_TO':
    case 'EXPOSES':
      return '#34D399'; // Emerald
    case 'CONTAINS':
      return '#475569'; // Slate
    default:
      return '#64748B'; // Gray
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
  const nodeTypes = useMemo(() => ({ customEntity: CustomEntityNode }), []);

  // Format nodes for React Flow
  const initialNodes: Node[] = useMemo(() => {
    return rawNodes.map((n) => {
      let subtext = '';
      if (n.line_number) subtext = `Line ${n.line_number}`;
      if (n.node_metadata?.version) subtext = `v${n.node_metadata.version}`;
      if (n.node_metadata?.http_method) subtext = `${n.node_metadata.http_method}`;

      return {
        id: n.id,
        type: 'customEntity',
        data: {
          label: n.name,
          node_type: n.node_type,
          file_path: n.file_path,
          subtext,
        },
        position: { x: 0, y: 0 },
        selected: n.id === selectedNodeId,
      };
    });
  }, [rawNodes, selectedNodeId]);

  // Format edges for React Flow
  const initialEdges: Edge[] = useMemo(() => {
    return rawEdges.map((e, idx) => {
      const color = getEdgeColor(e.relationship_type);
      const isSelected = selectedNodeId && (e.source_id === selectedNodeId || e.target_id === selectedNodeId);

      return {
        id: `e-${e.source_id}-${e.target_id}-${idx}`,
        source: e.source_id,
        target: e.target_id,
        label: e.relationship_type,
        animated: e.relationship_type === 'ROUTES_TO' || e.relationship_type === 'CALLS',
        style: {
          stroke: isSelected ? '#38BDF8' : color,
          strokeWidth: isSelected ? 2.5 : 1.2,
          opacity: selectedNodeId ? (isSelected ? 1.0 : 0.25) : 0.85,
        },
        labelStyle: {
          fill: isSelected ? '#38BDF8' : '#94A3B8',
          fontSize: 9,
          fontWeight: 600,
          fontFamily: 'monospace',
        },
        labelBgStyle: {
          fill: '#0B0F17',
          fillOpacity: 0.85,
          rx: 4,
          ry: 4,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isSelected ? '#38BDF8' : color,
          width: 14,
          height: 14,
        },
      };
    });
  }, [rawEdges, selectedNodeId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Recalculate layout whenever nodes, edges, or layout direction changes
  useEffect(() => {
    if (initialNodes.length > 0) {
      const layouted = getLayoutedElements(initialNodes, initialEdges, direction);
      setNodes(layouted.nodes);
      setEdges(layouted.edges);
    } else {
      setNodes([]);
      setEdges([]);
    }
  }, [initialNodes, initialEdges, direction, setNodes, setEdges]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onSelectNode(node.id === selectedNodeId ? null : node.id);
    },
    [onSelectNode, selectedNodeId]
  );

  const handlePaneClick = useCallback(() => {
    onSelectNode(null);
  }, [onSelectNode]);

  return (
    <div className="w-full h-full min-h-[560px] bg-[#0B0F17] rounded-2xl border border-gray-800 relative overflow-hidden">
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
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#1F2937" />
        <Controls
          className="!bg-[#111827] !border-gray-800 !rounded-xl !shadow-xl [&>button]:!bg-[#111827] [&>button]:!border-gray-800 [&>button]:!text-gray-300 hover:[&>button]:!bg-gray-800"
        />
        <MiniMap
          nodeColor={(n) => {
            const type = (n.data?.node_type as string) || '';
            if (type === 'file') return '#38BDF8';
            if (type === 'class') return '#C084FC';
            if (type === 'package') return '#FBBF24';
            if (type === 'api_endpoint') return '#34D399';
            return '#475569';
          }}
          className="!bg-[#111827]/90 !border-gray-800 !rounded-xl !overflow-hidden"
          maskColor="rgba(11, 15, 23, 0.7)"
        />
      </ReactFlow>
    </div>
  );
};
