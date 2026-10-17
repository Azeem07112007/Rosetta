/** Supported programming language definition. */
export interface Language {
  id: string;
  displayName: string;
  fileExtension: string;
}

/** Translation record from the API. */
export interface Translation {
  id: string;
  source_language: string;
  target_language: string;
  source_code: string;
  translated_code: string;
  explanation: string | null;
  detected_language: string | null;
  model_used: string;
  tokens_used: number;
  created_at: string;
}

/** Paginated translation list response. */
export interface TranslationListResponse {
  translations: Translation[];
  total: number;
  page: number;
  page_size: number;
}

/** Translation creation request. */
export interface TranslationCreateRequest {
  source_code: string;
  source_language: string;
  target_language: string;
  explain: boolean;
}

/** Usage statistics for the current month. */
export interface UsageStats {
  translation_count: number;
  tokens_consumed: number;
  monthly_limit: number;
  month: string;
}

/** User account information. */
export interface Account {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string | null;
}

/** Auth response from the API. */
export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user_id: string;
  email: string;
}

/** Supported languages list (shared constant). */
export const SUPPORTED_LANGUAGES: Language[] = [
  { id: "python", displayName: "Python", fileExtension: ".py" },
  { id: "typescript", displayName: "TypeScript", fileExtension: ".ts" },
  { id: "javascript", displayName: "JavaScript", fileExtension: ".js" },
  { id: "java", displayName: "Java", fileExtension: ".java" },
  { id: "csharp", displayName: "C#", fileExtension: ".cs" },
  { id: "cpp", displayName: "C++", fileExtension: ".cpp" },
  { id: "c", displayName: "C", fileExtension: ".c" },
  { id: "go", displayName: "Go", fileExtension: ".go" },
  { id: "rust", displayName: "Rust", fileExtension: ".rs" },
  { id: "ruby", displayName: "Ruby", fileExtension: ".rb" },
  { id: "php", displayName: "PHP", fileExtension: ".php" },
  { id: "swift", displayName: "Swift", fileExtension: ".swift" },
  { id: "kotlin", displayName: "Kotlin", fileExtension: ".kt" },
  { id: "scala", displayName: "Scala", fileExtension: ".scala" },
  { id: "dart", displayName: "Dart", fileExtension: ".dart" },
  { id: "r", displayName: "R", fileExtension: ".r" },
  { id: "sql", displayName: "SQL", fileExtension: ".sql" },
  { id: "bash", displayName: "Bash", fileExtension: ".sh" },
  { id: "powershell", displayName: "PowerShell", fileExtension: ".ps1" },
  { id: "lua", displayName: "Lua", fileExtension: ".lua" },
  { id: "perl", displayName: "Perl", fileExtension: ".pl" },
  { id: "haskell", displayName: "Haskell", fileExtension: ".hs" },
  { id: "elixir", displayName: "Elixir", fileExtension: ".ex" },
  { id: "cobol", displayName: "COBOL", fileExtension: ".cbl" },
];
