import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Trash2, Code2, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { api } from "../../lib/api";
import type { Translation, TranslationListResponse } from "../../types";
import { SUPPORTED_LANGUAGES } from "../../types";

function getLangName(id: string): string {
  return SUPPORTED_LANGUAGES.find((l) => l.id === id)?.displayName || id;
}

export default function HistoryPage() {
  const [translations, setTranslations] = useState<Translation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const pageSize = 20;

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await api.get<TranslationListResponse>("/translations", {
          page,
          page_size: pageSize,
        });
        setTranslations(data.translations);
        setTotal(data.total);
      } catch {
        // Empty state will show
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [page]);

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/translations/${id}`);
      setTranslations((prev) => prev.filter((t) => t.id !== id));
      setTotal((prev) => prev - 1);
    } catch {
      // Silently fail; could add toast here
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Translation history</h1>
          <p className="mt-1 text-sm text-text-secondary">
            {total} translation{total !== 1 ? "s" : ""} total
          </p>
        </div>
        <Link to="/app/translate">
          <Button size="sm">
            <Code2 size={14} />
            New translation
          </Button>
        </Link>
      </div>

      {loading ? (
        <div className="flex min-h-[30vh] items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        </div>
      ) : translations.length === 0 ? (
        <div className="rounded-md border border-border-default bg-bg-secondary p-12 text-center">
          <Code2 size={32} className="mx-auto mb-3 text-text-tertiary" />
          <p className="text-sm font-medium text-text-primary">No translations yet</p>
          <p className="mt-1 text-xs text-text-secondary">
            Your translation history will appear here.
          </p>
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-md border border-border-default">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border-subtle bg-bg-secondary">
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary">From</th>
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary">To</th>
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary hidden md:table-cell">Preview</th>
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary hidden sm:table-cell">Tokens</th>
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary text-right">Date</th>
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary w-10"></th>
                </tr>
              </thead>
              <tbody>
                {translations.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-border-subtle last:border-0 hover:bg-bg-tertiary/50 transition-colors duration-120"
                  >
                    <td className="px-4 py-3">
                      <Link to={`/app/translate/${t.id}`}>
                        <span className="rounded bg-bg-tertiary px-2 py-0.5 font-mono text-xs">{getLangName(t.source_language)}</span>
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-bg-tertiary px-2 py-0.5 font-mono text-xs">{getLangName(t.target_language)}</span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <Link to={`/app/translate/${t.id}`} className="truncate block max-w-xs font-mono text-xs text-text-tertiary hover:text-text-secondary">
                        {t.source_code.slice(0, 80)}{t.source_code.length > 80 ? "..." : ""}
                      </Link>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell text-xs text-text-tertiary font-mono">
                      {t.tokens_used.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-text-tertiary whitespace-nowrap">
                      {new Date(t.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDelete(t.id)}
                        className="flex h-7 w-7 items-center justify-center rounded text-text-tertiary hover:bg-error/10 hover:text-error transition-colors duration-120"
                        aria-label="Delete translation"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-xs text-text-tertiary">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  <ChevronLeft size={14} />
                  Previous
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                  <ChevronRight size={14} />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
