import React, { useState } from 'react';
import { X, Github, AlertCircle, Loader2, CheckCircle2, ArrowRight } from 'lucide-react';

interface ConnectRepoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnect: (repoUrl: string) => Promise<void>;
}

export const ConnectRepoModal: React.FC<ConnectRepoModalProps> = ({
  isOpen,
  onClose,
  onConnect,
}) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = repoUrl.trim();
    if (!trimmed) {
      setError('Please enter a GitHub repository URL or owner/repo slug.');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await onConnect(trimmed);
      setRepoUrl('');
      onClose();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to connect repository. Please verify the URL and try again.';
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExampleClick = (example: string) => {
    setRepoUrl(example);
    setError(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-lg rounded-2xl bg-[#0F172A] border border-gray-800 shadow-2xl p-6 text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-gray-800">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Github className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Connect GitHub Repository</h3>
              <p className="text-xs text-gray-400">Initialize a live AI Digital Twin for software intelligence</p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mt-4 p-3 rounded-xl bg-rose-950/50 border border-rose-800/80 text-xs text-rose-300 flex items-start space-x-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2">
              GitHub Repository URL or Slug
            </label>
            <div className="relative">
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/owner/repository or owner/repository"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-xl bg-gray-900 border border-gray-700 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition font-mono"
                autoFocus
              />
            </div>
            <p className="mt-1.5 text-[11px] text-gray-400">
              Works with any public GitHub repository. No token required for public repos.
            </p>
          </div>

          {/* Quick Examples */}
          <div className="pt-1">
            <span className="text-[11px] font-medium text-gray-400">Quick Test Examples:</span>
            <div className="flex flex-wrap gap-2 mt-2">
              {['facebook/react', 'microsoft/vscode', 'octocat/Hello-World'].map((ex) => (
                <button
                  type="button"
                  key={ex}
                  onClick={() => handleExampleClick(ex)}
                  disabled={isSubmitting}
                  className="px-2.5 py-1 rounded-lg bg-gray-800/80 hover:bg-gray-700 border border-gray-700 text-xs text-cyan-300 font-mono transition"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>

          {/* Informative Checklist */}
          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800 text-[11px] text-gray-400 space-y-1.5">
            <div className="flex items-center space-x-2 text-gray-300 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Real GitHub API telemetry extraction:</span>
            </div>
            <p className="pl-5 text-gray-400">
              Fetches commits, active contributors, open PRs, issues, branches, releases, and computes the Repository Health Index.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-gray-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs font-semibold text-gray-300 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-xs font-semibold text-white shadow-lg shadow-cyan-500/20 transition flex items-center space-x-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Connecting & Syncing...</span>
                </>
              ) : (
                <>
                  <span>Connect Repository</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
