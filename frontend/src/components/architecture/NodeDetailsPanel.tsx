import React, { useEffect, useState } from 'react';
import {
  X,
  FileCode,
  Boxes,
  Code2,
  Package,
  Globe,
  ArrowRight,
  ArrowLeft,
  ExternalLink,
  Code,
  Layers,
  Info,
} from 'lucide-react';
import { NodeDetailData } from '../../types';
import { apiService } from '../../services/api';

interface Props {
  projectId: number;
  nodeId: string;
  onClose: () => void;
  onSelectNode: (nodeId: string) => void;
}

export const NodeDetailsPanel: React.FC<Props> = ({
  projectId,
  nodeId,
  onClose,
  onSelectNode,
}) => {
  const [detail, setDetail] = useState<NodeDetailData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiService.getNodeDetail(projectId, nodeId);
        if (isMounted) setDetail(data);
      } catch (err: any) {
        if (isMounted) setError(err?.response?.data?.detail || err?.message || 'Failed to load node details');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchDetail();
    return () => {
      isMounted = false;
    };
  }, [projectId, nodeId]);

  return (
    <div className="w-80 md:w-96 bg-[#111827]/95 backdrop-blur-md border border-gray-800 rounded-2xl p-5 shadow-2xl flex flex-col h-[560px] overflow-hidden text-gray-200">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-800 shrink-0">
        <div className="flex items-center space-x-2 overflow-hidden">
          <Layers className="w-4 h-4 text-cyan-400 shrink-0" />
          <h3 className="font-bold text-sm text-white truncate">Node Inspector</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center space-y-2 text-gray-400">
          <div className="w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs">Inspecting entity AST...</span>
        </div>
      ) : error || !detail ? (
        <div className="flex-1 flex items-center justify-center p-4 text-center text-xs text-rose-400">
          {error || 'Node data unavailable'}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto pt-3 space-y-4 pr-1">
          {/* Node Summary Card */}
          <div className="bg-[#0B0F17] border border-gray-800 rounded-xl p-3.5 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <span className="font-bold text-sm text-cyan-300 break-all font-mono">
                {detail.node.name}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 uppercase font-mono font-semibold shrink-0">
                {detail.node.node_type}
              </span>
            </div>

            {detail.node.file_path && (
              <div className="flex items-center text-xs text-gray-400 space-x-1.5 font-mono">
                <FileCode className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                <span className="truncate">{detail.node.file_path}</span>
                {detail.node.line_number && (
                  <span className="text-cyan-400">:{detail.node.line_number}</span>
                )}
              </div>
            )}

            {detail.node.module && (
              <div className="text-[11px] text-gray-400">
                <span className="text-gray-400">Module: </span>
                <span className="font-mono text-gray-300">{detail.node.module}</span>
              </div>
            )}
          </div>

          {/* Metadata attributes */}
          {detail.node.node_metadata && Object.keys(detail.node.node_metadata).length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider flex items-center space-x-1">
                <Code className="w-3.5 h-3.5 text-gray-400" />
                <span>Extracted Attributes</span>
              </h4>
              <div className="bg-[#0B0F17] border border-gray-800/80 rounded-xl p-3 text-xs space-y-1 font-mono">
                {detail.node.node_metadata.bases && (
                  <div>
                    <span className="text-gray-400">Extends: </span>
                    <span className="text-purple-400 font-semibold">
                      {detail.node.node_metadata.bases.join(', ')}
                    </span>
                  </div>
                )}
                {detail.node.node_metadata.parameters && (
                  <div>
                    <span className="text-gray-400">Params: </span>
                    <span className="text-blue-300">
                      ({detail.node.node_metadata.parameters.join(', ')})
                    </span>
                  </div>
                )}
                {detail.node.node_metadata.loc && (
                  <div>
                    <span className="text-gray-400">Lines of Code: </span>
                    <span className="text-white">{detail.node.node_metadata.loc}</span>
                  </div>
                )}
                {detail.node.node_metadata.version && (
                  <div>
                    <span className="text-gray-400">Version: </span>
                    <span className="text-amber-400">{detail.node.node_metadata.version}</span>
                  </div>
                )}
                {detail.node.node_metadata.docstring && (
                  <div className="text-[11px] text-gray-400 pt-1 border-t border-gray-800 font-sans italic">
                    "{detail.node.node_metadata.docstring}"
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Dependencies (Outgoing) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider flex items-center space-x-1">
                <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
                <span>Outgoing Dependencies ({detail.dependencies.length})</span>
              </h4>
            </div>
            {detail.dependencies.length === 0 ? (
              <p className="text-xs text-gray-400 italic px-2">No outgoing dependencies</p>
            ) : (
              <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                {detail.dependencies.map((dep) => (
                  <button
                    key={dep.id}
                    onClick={() => onSelectNode(dep.id)}
                    className="w-full text-left p-2 rounded-lg bg-[#0B0F17] hover:bg-gray-800/80 border border-gray-800/60 flex items-center justify-between group transition-colors"
                  >
                    <div className="overflow-hidden">
                      <p className="text-xs font-semibold text-gray-200 group-hover:text-cyan-400 truncate">
                        {dep.name}
                      </p>
                      <p className="text-[10px] text-gray-400 truncate font-mono">
                        {dep.node_type} • {dep.file_path || dep.module}
                      </p>
                    </div>
                    <ExternalLink className="w-3 h-3 text-gray-400 group-hover:text-cyan-400 shrink-0 ml-1" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Dependents (Incoming) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider flex items-center space-x-1">
                <ArrowLeft className="w-3.5 h-3.5 text-cyan-400" />
                <span>Incoming Dependents ({detail.dependents.length})</span>
              </h4>
            </div>
            {detail.dependents.length === 0 ? (
              <p className="text-xs text-gray-400 italic px-2">No incoming dependents</p>
            ) : (
              <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                {detail.dependents.map((dep) => (
                  <button
                    key={dep.id}
                    onClick={() => onSelectNode(dep.id)}
                    className="w-full text-left p-2 rounded-lg bg-[#0B0F17] hover:bg-gray-800/80 border border-gray-800/60 flex items-center justify-between group transition-colors"
                  >
                    <div className="overflow-hidden">
                      <p className="text-xs font-semibold text-gray-200 group-hover:text-cyan-400 truncate">
                        {dep.name}
                      </p>
                      <p className="text-[10px] text-gray-400 truncate font-mono">
                        {dep.node_type} • {dep.file_path || dep.module}
                      </p>
                    </div>
                    <ExternalLink className="w-3 h-3 text-gray-400 group-hover:text-cyan-400 shrink-0 ml-1" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
