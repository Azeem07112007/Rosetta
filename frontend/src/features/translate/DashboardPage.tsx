import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Code2, Clock, BarChart3 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { api } from "../../lib/api";
import type { UsageStats, Translation, TranslationListResponse } from "../../types";
import { SUPPORTED_LANGUAGES } from "../../types";

function getLangName(id: string): string {
  return SUPPORTED_LANGUAGES.find((l) => l.id === id)?.displayName || id;
}

export default function DashboardPage() {
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [recent, setRecent] = useState<Translation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [usageData, translationsData] = await Promise.all([
          api.get<UsageStats>("/usage"),
          api.get<TranslationListResponse>("/translations", { page: 1, page_size: 5 }),
        ]);
        setUsage(usageData);
        setRecent(translationsData.translations);
      } catch {
        // Silently handle; empty states will render
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Dashboard</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Your translation activity at a glance.
          </p>
        </div>
        <Link to="/app/translate">
          <Button>
            <Code2 size={16} />
            New translation
          </Button>
        </Link>
      </div>

      {/* Stats cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-md border border-border-default bg-bg-secondary p-6">
          <div className="flex items-center gap-2 text-text-secondary">
            <BarChart3 size={16} />
            <span className="text-xs font-medium uppercase tracking-wide">Translations this month</span>
          </div>
          <p className="mt-2 text-2xl font-semibold text-text-primary">
            {usage?.translation_count ?? 0}
            <span className="text-sm font-normal text-text-tertiary">
              {" "}/ {usage?.monthly_limit ?? 100}
            </span>
          </p>
          {usage && (
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-bg-tertiary">
              <div
                className="h-full rounded-full bg-accent transition-all duration-300"
                style={{ width: `${Math.min((usage.translation_count / usage.monthly_limit) * 100, 100)}%` }}
              />
            </div>
          )}
        </div>

        <div className="rounded-md border border-border-default bg-bg-secondary p-6">
          <div className="flex items-center gap-2 text-text-secondary">
            <Code2 size={16} />
            <span className="text-xs font-medium uppercase tracking-wide">Tokens used</span>
          </div>
          <p className="mt-2 text-2xl font-semibold text-text-primary">
            {(usage?.tokens_consumed ?? 0).toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-text-tertiary">
            {usage?.month ?? "Current month"}
          </p>
        </div>

        <div className="rounded-md border border-border-default bg-bg-secondary p-6">
          <div className="flex items-center gap-2 text-text-secondary">
            <Clock size={16} />
            <span className="text-xs font-medium uppercase tracking-wide">Remaining</span>
          </div>
          <p className="mt-2 text-2xl font-semibold text-text-primary">
            {Math.max((usage?.monthly_limit ?? 100) - (usage?.translation_count ?? 0), 0)}
          </p>
          <p className="mt-1 text-xs text-text-tertiary">
            translations available
          </p>
        </div>
      </div>

      {/* Recent translations */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-medium text-text-primary">Recent translations</h2>
          {recent.length > 0 && (
            <Link to="/app/history" className="flex items-center gap-1 text-xs text-accent hover:text-accent-hover transition-colors">
              View all <ArrowRight size={12} />
            </Link>
          )}
        </div>

        {recent.length === 0 ? (
          <div className="rounded-md border border-border-default bg-bg-secondary p-12 text-center">
            <Code2 size={32} className="mx-auto mb-3 text-text-tertiary" />
            <p className="text-sm font-medium text-text-primary">No translations yet</p>
            <p className="mt-1 text-xs text-text-secondary">
              Start by translating some code.
            </p>
            <Link to="/app/translate">
              <Button variant="secondary" size="sm" className="mt-4">
                Translate code
              </Button>
            </Link>
          </div>
        ) : (
          <div className="overflow-hidden rounded-md border border-border-default">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border-subtle bg-bg-secondary">
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary">From</th>
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary">To</th>
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary hidden sm:table-cell">Preview</th>
                  <th className="px-4 py-3 text-xs font-medium text-text-secondary text-right">Date</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-border-subtle last:border-0 hover:bg-bg-tertiary/50 transition-colors duration-120 cursor-pointer"
                    onClick={() => window.location.href = `/app/translate/${t.id}`}
                  >
                    <td className="px-4 py-3">
                      <span className="rounded bg-bg-tertiary px-2 py-0.5 font-mono text-xs">{getLangName(t.source_language)}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-bg-tertiary px-2 py-0.5 font-mono text-xs">{getLangName(t.target_language)}</span>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className="truncate block max-w-xs font-mono text-xs text-text-tertiary">
                        {t.source_code.slice(0, 80)}{t.source_code.length > 80 ? "..." : ""}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-text-tertiary whitespace-nowrap">
                      {new Date(t.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
