import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import TranslatePage from "./TranslatePage";
import { checkA11y } from "../../test/a11y";

// Mock the API client
vi.mock("../../lib/api", () => ({
  api: {
    post: vi.fn(),
  },
  ApiClientError: class ApiClientError extends Error {
    code: string;
    status: number;
    details: Record<string, unknown>;
    constructor(status: number, error: { code: string; message: string }) {
      super(error.message);
      this.name = "ApiClientError";
      this.code = error.code;
      this.status = status;
      this.details = {};
    }
  },
}));

// Mock CodeMirror (jsdom doesn't support it)
vi.mock("@uiw/react-codemirror", () => ({
  default: ({
    value,
    onChange,
    placeholder,
  }: {
    value: string;
    onChange?: (val: string) => void;
    placeholder?: string;
  }) => (
    <textarea
      data-testid="codemirror"
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder || "code editor"}
    />
  ),
}));

// Mock CodeMirror language extensions
vi.mock("@codemirror/lang-python", () => ({ python: vi.fn() }));
vi.mock("@codemirror/lang-javascript", () => ({ javascript: vi.fn() }));
vi.mock("@codemirror/lang-java", () => ({ java: vi.fn() }));
vi.mock("@codemirror/lang-cpp", () => ({ cpp: vi.fn() }));
vi.mock("@codemirror/lang-rust", () => ({ rust: vi.fn() }));
vi.mock("@codemirror/lang-go", () => ({ go: vi.fn() }));
vi.mock("@codemirror/lang-php", () => ({ php: vi.fn() }));
vi.mock("@codemirror/lang-sql", () => ({ sql: vi.fn() }));

describe("TranslatePage", () => {
  let apiModule: { api: { post: ReturnType<typeof vi.fn> } };

  beforeEach(async () => {
    vi.clearAllMocks();
    apiModule = (await import("../../lib/api")) as unknown as typeof apiModule;
  });

  it("renders source and output editors", () => {
    render(
      <MemoryRouter>
        <TranslatePage />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: /translate code/i })).toBeInTheDocument();
    expect(screen.getByText("Source")).toBeInTheDocument();
    expect(screen.getByText("Output")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /translate/i })).toBeInTheDocument();
  });

  it("renders language selectors", () => {
    render(
      <MemoryRouter>
        <TranslatePage />
      </MemoryRouter>
    );

    expect(screen.getByLabelText(/from/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/to/i)).toBeInTheDocument();
  });

  it("shows error when trying to translate empty code", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <TranslatePage />
      </MemoryRouter>
    );

    await user.click(screen.getByRole("button", { name: /translate/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/enter some code/i);
    });
    expect(apiModule.api.post).not.toHaveBeenCalled();
  });

  it("calls API and displays translated code", async () => {
    const user = userEvent.setup();
    apiModule.api.post.mockResolvedValueOnce({
      id: "test-id",
      source_language: "python",
      target_language: "typescript",
      source_code: 'print("hello")',
      translated_code: 'console.log("hello");',
      explanation: null,
      detected_language: null,
      model_used: "gemini-2.0-flash",
      tokens_used: 50,
      created_at: "2026-10-13T00:00:00Z",
    });

    render(
      <MemoryRouter>
        <TranslatePage />
      </MemoryRouter>
    );

    const editors = screen.getAllByTestId("codemirror");
    await user.type(editors[0], 'print("hello")');
    await user.click(screen.getByRole("button", { name: /translate/i }));

    await waitFor(() => {
      expect(apiModule.api.post).toHaveBeenCalledWith(
        "/translations",
        expect.objectContaining({
          source_code: 'print("hello")',
          target_language: "python",
        })
      );
    });
  });

  it("shows the explain differences checkbox", () => {
    render(
      <MemoryRouter>
        <TranslatePage />
      </MemoryRouter>
    );

    expect(screen.getByLabelText(/explain differences/i)).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <MemoryRouter>
        <TranslatePage />
      </MemoryRouter>
    );

    await checkA11y(container);
  });
});
