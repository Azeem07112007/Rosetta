import { Link } from "react-router-dom";
import { Code2, ArrowRightLeft, Clock, Shield, Zap, FileText } from "lucide-react";
import { Button } from "../../components/ui/Button";

const features = [
  {
    icon: ArrowRightLeft,
    title: "Multi-language translation",
    description:
      "Translate code between 23 programming languages including Python, TypeScript, Rust, Go, and more.",
  },
  {
    icon: Zap,
    title: "AI-powered accuracy",
    description:
      "Uses Google Gemini to produce idiomatic translations that follow the conventions of the target language.",
  },
  {
    icon: FileText,
    title: "Inline explanations",
    description:
      "Toggle explanation mode to get line-by-line notes on non-trivial translation decisions.",
  },
  {
    icon: Code2,
    title: "Syntax-highlighted editors",
    description:
      "Side-by-side code editors with full syntax highlighting, line numbers, and code folding.",
  },
  {
    icon: Clock,
    title: "Translation history",
    description:
      "All translations are saved to your account. Revisit, re-translate, or download past results.",
  },
  {
    icon: Shield,
    title: "Secure by default",
    description:
      "Your code is processed server-side with TLS encryption. No code is stored beyond your account.",
  },
];

export default function LandingPage() {
  return (
    <div>
      {/* Hero */}
      <section className="mx-auto max-w-content px-6 py-20 lg:py-28">
        <div className="max-w-2xl">
          <h1 className="text-3xl font-bold tracking-tight text-text-primary lg:text-[2.75rem] lg:leading-tight">
            Translate code between programming languages
          </h1>
          <p className="mt-4 max-w-prose text-base text-text-secondary leading-relaxed">
            Rosetta converts source code from one language to another using AI.
            Paste your code, select a target language, and get an idiomatic
            translation with optional explanations of the differences.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/signup">
              <Button size="lg">Get started</Button>
            </Link>
            <Link to="/signin">
              <Button variant="secondary" size="lg">Sign in</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border-default bg-bg-secondary">
        <div className="mx-auto max-w-content px-6 py-16 lg:py-20">
          <h2 className="text-xl font-semibold text-text-primary">What Rosetta does</h2>
          <p className="mt-2 max-w-prose text-sm text-text-secondary">
            A focused tool for developers who need to port, learn, or compare code across languages.
          </p>

          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-md border border-border-default bg-bg-primary p-6"
              >
                <feature.icon size={20} className="mb-3 text-accent" />
                <h3 className="text-sm font-medium text-text-primary">
                  {feature.title}
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-text-secondary">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Supported languages */}
      <section className="border-t border-border-default">
        <div className="mx-auto max-w-content px-6 py-16 lg:py-20">
          <h2 className="text-xl font-semibold text-text-primary">Supported languages</h2>
          <p className="mt-2 max-w-prose text-sm text-text-secondary">
            Rosetta supports translation between any pair of these languages.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {[
              "Python", "TypeScript", "JavaScript", "Java", "C#", "C++", "C",
              "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "Dart",
              "R", "SQL", "Bash", "PowerShell", "Lua", "Perl", "Haskell", "Elixir",
            ].map((lang) => (
              <span
                key={lang}
                className="rounded-md bg-bg-secondary px-3 py-1.5 font-mono text-xs text-text-secondary border border-border-subtle"
              >
                {lang}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border-default bg-bg-secondary">
        <div className="mx-auto max-w-content px-6 py-16 text-center">
          <h2 className="text-xl font-semibold text-text-primary">
            Start translating code
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            Free to use with 100 translations per month.
          </p>
          <Link to="/signup">
            <Button size="lg" className="mt-6">Create a free account</Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
