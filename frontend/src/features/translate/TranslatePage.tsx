import { useState, useCallback } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { javascript } from "@codemirror/lang-javascript";
import { java } from "@codemirror/lang-java";
import { cpp } from "@codemirror/lang-cpp";
import { rust } from "@codemirror/lang-rust";
import { go } from "@codemirror/lang-go";
import { php } from "@codemirror/lang-php";
import { sql } from "@codemirror/lang-sql";
import { ArrowRightLeft, Copy, Download, Check, MessageSquare } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { api, ApiClientError } from "../../lib/api";
import { SUPPORTED_LANGUAGES, type Translation } from "../../types";

const languageExtensions: Record<string, () => ReturnType<typeof python>> = {
  python: python,
  typescript: () => javascript({ typescript: true }),
  javascript: javascript,
  java: java,
  csharp: () => java(), // Close enough syntax highlighting
  cpp: cpp,
  c: cpp,
  go: go,
  rust: rust,
  php: php,
  sql: sql,
};

function getExtension(langId: string) {
  const factory = languageExtensions[langId];
  return factory ? [factory()] : [];
}

const languageOptions = [
  { value: "auto", label: "Auto-detect" },
  ...SUPPORTED_LANGUAGES.map((l) => ({ value: l.id, label: l.displayName })),
];

const targetOptions = SUPPORTED_LANGUAGES.map((l) => ({
  value: l.id,
  label: l.displayName,
}));

interface TranslatePageProps {
  initialTranslation?: Translation;
}

export default function TranslatePage({ initialTranslation }: TranslatePageProps) {
  const [sourceCode, setSourceCode] = useState(initialTranslation?.source_code || "");
  const [sourceLang, setSourceLang] = useState(initialTranslation?.source_language || "auto");
  const [targetLang, setTargetLang] = useState(initialTranslation?.target_language || "python");
  const [explain, setExplain] = useState(false);
  const [translatedCode, setTranslatedCode] = useState(initialTranslation?.translated_code || "");
  const [explanation, setExplanation] = useState(initialTranslation?.explanation || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const handleTranslate = useCallback(async () => {
    if (!sourceCode.trim()) {
      setError("Enter some code to translate.");
      return;
    }
    if (sourceLang !== "auto" && sourceLang === targetLang) {
      setError("Source and target language must be different.");
      return;
    }

    setError("");
    setLoading(true);
    setTranslatedCode("");
    setExplanation("");

    try {
      const result = await api.post<Translation>("/translations", {
        source_code: sourceCode,
        source_language: sourceLang,
        target_language: targetLang,
        explain,
      });
      setTranslatedCode(result.translated_code);
      setExplanation(result.explanation || "");
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Translation failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }, [sourceCode, sourceLang, targetLang, explain]);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(translatedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [translatedCode]);

  const handleDownload = useCallback(() => {
    const lang = SUPPORTED_LANGUAGES.find((l) => l.id === targetLang);
    const ext = lang?.fileExtension || ".txt";
    const blob = new Blob([translatedCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `translated${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }, [translatedCode, targetLang]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Translate code</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Paste your source code, select languages, and translate.
        </p>
      </div>

      {/* Controls bar */}
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <div className="w-48">
          <Select
            label="From"
            options={languageOptions}
            value={sourceLang}
            onChange={(e) => setSourceLang(e.target.value)}
          />
        </div>

        <div className="flex items-end pb-[2px]">
          <ArrowRightLeft size={18} className="text-text-tertiary" />
        </div>

        <div className="w-48">
          <Select
            label="To"
            options={targetOptions}
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
          />
        </div>

        <label className="flex cursor-pointer items-center gap-2 pb-[2px]">
          <input
            type="checkbox"
            checked={explain}
            onChange={(e) => setExplain(e.target.checked)}
            className="h-4 w-4 rounded border-border-default text-accent focus:ring-accent"
          />
          <span className="flex items-center gap-1 text-sm text-text-secondary">
            <MessageSquare size={14} />
            Explain differences
          </span>
        </label>

        <div className="ml-auto">
          <Button onClick={handleTranslate} loading={loading} size="md">
            Translate
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-error bg-error/5 px-4 py-3 text-sm text-error" role="alert">
          {error}
        </div>
      )}

      {/* Editor panels */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Source */}
        <div className="flex flex-col">
          <div className="flex items-center justify-between rounded-t-md border border-b-0 border-border-default bg-bg-secondary px-4 py-2">
            <span className="text-xs font-medium text-text-secondary">Source</span>
            <span className="font-mono text-xs text-text-tertiary">
              {sourceCode.length.toLocaleString()} chars
            </span>
          </div>
          <div className="overflow-hidden rounded-b-md border border-border-default">
            <CodeMirror
              value={sourceCode}
              onChange={setSourceCode}
              extensions={getExtension(sourceLang === "auto" ? "python" : sourceLang)}
              placeholder="Paste or type your source code here..."
              minHeight="300px"
              maxHeight="600px"
              basicSetup={{
                lineNumbers: true,
                foldGutter: true,
                highlightActiveLine: true,
              }}
              className="text-sm"
            />
          </div>
        </div>

        {/* Output */}
        <div className="flex flex-col">
          <div className="flex items-center justify-between rounded-t-md border border-b-0 border-border-default bg-bg-secondary px-4 py-2">
            <span className="text-xs font-medium text-text-secondary">Output</span>
            {translatedCode && (
              <div className="flex items-center gap-1">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 rounded px-2 py-1 text-xs text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-colors duration-120"
                  aria-label="Copy translated code"
                >
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  {copied ? "Copied" : "Copy"}
                </button>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1 rounded px-2 py-1 text-xs text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-colors duration-120"
                  aria-label="Download translated code"
                >
                  <Download size={12} />
                  Download
                </button>
              </div>
            )}
          </div>
          <div className="overflow-hidden rounded-b-md border border-border-default">
            {translatedCode ? (
              <CodeMirror
                value={translatedCode}
                extensions={getExtension(targetLang)}
                readOnly
                minHeight="300px"
                maxHeight="600px"
                basicSetup={{
                  lineNumbers: true,
                  foldGutter: true,
                  highlightActiveLine: false,
                }}
                className="text-sm"
              />
            ) : (
              <div className="flex min-h-[300px] items-center justify-center text-sm text-text-tertiary">
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
                    Translating...
                  </div>
                ) : (
                  "Translated code will appear here."
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Explanation panel */}
      {explanation && (
        <div className="mt-4 rounded-md border border-border-default bg-bg-secondary p-6">
          <h2 className="mb-3 text-sm font-medium text-text-primary">Translation notes</h2>
          <div className="max-w-prose whitespace-pre-wrap font-mono text-xs leading-relaxed text-text-secondary">
            {explanation}
          </div>
        </div>
      )}
    </div>
  );
}
