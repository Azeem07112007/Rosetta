import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import type { Translation } from "../../types";
import TranslatePage from "./TranslatePage";

export default function TranslationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [translation, setTranslation] = useState<Translation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      if (!id) return;
      try {
        const data = await api.get<Translation>(`/translations/${id}`);
        setTranslation(data);
      } catch {
        setError("Translation not found.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  if (error || !translation) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4">
        <p className="text-sm text-text-secondary">{error || "Translation not found."}</p>
        <button
          onClick={() => navigate("/app/history")}
          className="text-sm text-accent hover:text-accent-hover"
        >
          Back to history
        </button>
      </div>
    );
  }

  return <TranslatePage initialTranslation={translation} />;
}
