import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Helper to parse inline markdown (bold, italic, inline code)
  const renderInline = (text: string): React.ReactNode => {
    // Regex splits by: `code`, **bold**, *italic*
    const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g);

    return parts.map((part, i) => {
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return (
          <code
            key={i}
            className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-gray-800/90 text-cyan-700 dark:text-cyan-300 font-mono text-[12px] border border-slate-200 dark:border-gray-700/50"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return (
          <strong key={i} className="font-semibold text-slate-900 dark:text-white">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
        return (
          <em key={i} className="italic text-slate-700 dark:text-slate-300">
            {part.slice(1, -1)}
          </em>
        );
      }
      return part;
    });
  };

  // Split into blocks: code blocks vs text blocks
  const blocks: React.ReactNode[] = [];
  const lines = content.split('\n');
  let inCodeBlock = false;
  let codeLanguage = '';
  let codeBuffer: string[] = [];
  let codeBlockCounter = 0;

  let listBuffer: { type: 'ul' | 'ol'; items: string[] } | null = null;

  const flushList = () => {
    if (listBuffer) {
      if (listBuffer.type === 'ul') {
        blocks.push(
          <ul key={`ul-${blocks.length}`} className="my-2.5 space-y-1.5 list-disc list-inside pl-1 text-slate-700 dark:text-slate-200">
            {listBuffer.items.map((item, idx) => (
              <li key={idx} className="text-xs leading-relaxed text-slate-700 dark:text-slate-200">
                {renderInline(item)}
              </li>
            ))}
          </ul>
        );
      } else {
        blocks.push(
          <ol key={`ol-${blocks.length}`} className="my-2.5 space-y-1.5 list-decimal list-inside pl-1 text-slate-700 dark:text-slate-200">
            {listBuffer.items.map((item, idx) => (
              <li key={idx} className="text-xs leading-relaxed text-slate-700 dark:text-slate-200">
                {renderInline(item)}
              </li>
            ))}
          </ol>
        );
      }
      listBuffer = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Fenced Code Block start / end
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        // End code block
        const codeText = codeBuffer.join('\n');
        const currentIndex = codeBlockCounter++;
        blocks.push(
          <div
            key={`code-${currentIndex}`}
            className="my-3 rounded-lg overflow-hidden border border-slate-800 dark:border-gray-800 bg-[#0B0F17] font-mono text-xs shadow-md"
          >
            <div className="flex items-center justify-between px-3 py-1.5 bg-gray-900/90 border-b border-gray-800 text-[11px] text-gray-400">
              <span className="uppercase font-semibold tracking-wider text-cyan-400">
                {codeLanguage || 'code'}
              </span>
              <button
                onClick={() => handleCopy(codeText, currentIndex)}
                className="flex items-center space-x-1 text-gray-400 hover:text-white transition-colors"
                title="Copy code"
              >
                {copiedIndex === currentIndex ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <pre className="p-3 overflow-x-auto text-slate-200 leading-relaxed font-mono">
              <code>{codeText}</code>
            </pre>
          </div>
        );
        inCodeBlock = false;
        codeLanguage = '';
        codeBuffer = [];
      } else {
        flushList();
        inCodeBlock = true;
        codeLanguage = line.trim().slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    const trimmed = line.trim();

    // Empty lines
    if (!trimmed) {
      flushList();
      continue;
    }

    // Blockquote
    if (trimmed.startsWith('>')) {
      flushList();
      const quoteText = trimmed.replace(/^>\s?/, '');
      blocks.push(
        <blockquote
          key={`quote-${i}`}
          className="my-2 pl-3 py-1.5 border-l-2 border-cyan-500 bg-cyan-50/70 dark:bg-cyan-950/20 text-slate-700 dark:text-slate-300 text-xs italic rounded-r"
        >
          {renderInline(quoteText)}
        </blockquote>
      );
      continue;
    }

    // Headings
    if (trimmed.startsWith('### ')) {
      flushList();
      blocks.push(
        <h4 key={`h4-${i}`} className="mt-4 mb-2 text-sm font-semibold text-cyan-600 dark:text-cyan-400 tracking-tight">
          {renderInline(trimmed.slice(4))}
        </h4>
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      blocks.push(
        <h3 key={`h3-${i}`} className="mt-4 mb-2 text-base font-bold text-slate-900 dark:text-white tracking-tight">
          {renderInline(trimmed.slice(3))}
        </h3>
      );
      continue;
    }
    if (trimmed.startsWith('# ')) {
      flushList();
      blocks.push(
        <h2 key={`h2-${i}`} className="mt-5 mb-2.5 text-lg font-bold text-slate-900 dark:text-white tracking-tight">
          {renderInline(trimmed.slice(2))}
        </h2>
      );
      continue;
    }

    // Unordered List (- or *)
    const ulMatch = trimmed.match(/^[-*]\s+(.+)/);
    if (ulMatch) {
      if (!listBuffer || listBuffer.type !== 'ul') {
        flushList();
        listBuffer = { type: 'ul', items: [] };
      }
      listBuffer.items.push(ulMatch[1]);
      continue;
    }

    // Ordered List (1., 2., etc.)
    const olMatch = trimmed.match(/^\d+\.\s+(.+)/);
    if (olMatch) {
      if (!listBuffer || listBuffer.type !== 'ol') {
        flushList();
        listBuffer = { type: 'ol', items: [] };
      }
      listBuffer.items.push(olMatch[1]);
      continue;
    }

    // Regular Paragraph
    flushList();
    blocks.push(
      <p key={`p-${i}`} className="my-2 text-xs leading-relaxed text-slate-700 dark:text-slate-200">
        {renderInline(line)}
      </p>
    );
  }

  flushList();

  return <div className="space-y-1">{blocks}</div>;
};
