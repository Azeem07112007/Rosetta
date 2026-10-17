import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import SignUpPage from "./SignUpPage";
import { checkA11y } from "../../test/a11y";

const mockSignUp = vi.fn();

vi.mock("./AuthContext", () => ({
  useAuth: () => ({
    signUp: mockSignUp,
    user: null,
    session: null,
    loading: false,
    signOut: vi.fn(),
    signIn: vi.fn(),
  }),
}));

describe("SignUpPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders email, password, and confirm password inputs", () => {
    render(
      <MemoryRouter>
        <SignUpPage />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: /create your account/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/^email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("validates password length under 8 characters", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <SignUpPage />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/^email/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password/i), "short");
    await user.type(screen.getByLabelText(/confirm password/i), "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument();
    });
    expect(mockSignUp).not.toHaveBeenCalled();
  });

  it("validates password confirmation mismatch", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <SignUpPage />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/^email/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password/i), "password123");
    await user.type(screen.getByLabelText(/confirm password/i), "differentPassword");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
    expect(mockSignUp).not.toHaveBeenCalled();
  });

  it("calls signUp and shows success state on valid submission", async () => {
    const user = userEvent.setup();
    mockSignUp.mockResolvedValueOnce(undefined);

    render(
      <MemoryRouter>
        <SignUpPage />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/^email/i), "newuser@example.com");
    await user.type(screen.getByLabelText(/^password/i), "securePassword123");
    await user.type(screen.getByLabelText(/confirm password/i), "securePassword123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalledWith("newuser@example.com", "securePassword123");
      expect(screen.getByRole("heading", { name: /check your email/i })).toBeInTheDocument();
    });
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <MemoryRouter>
        <SignUpPage />
      </MemoryRouter>
    );

    await checkA11y(container);
  });
});
