import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import SignInPage from "./SignInPage";
import { checkA11y } from "../../test/a11y";

const mockSignIn = vi.fn();

vi.mock("./AuthContext", () => ({
  useAuth: () => ({
    signIn: mockSignIn,
    user: null,
    session: null,
    loading: false,
    signOut: vi.fn(),
    signUp: vi.fn(),
  }),
}));

describe("SignInPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders email, password inputs and submit button", () => {
    render(
      <MemoryRouter>
        <SignInPage />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: /sign in to rosetta/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /forgot password\?/i })).toBeInTheDocument();
  });

  it("shows validation error on invalid email", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <SignInPage />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/email/i), "invalid-email");
    await user.type(screen.getByLabelText(/password/i), "secret123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/enter a valid email address/i)).toBeInTheDocument();
    });
    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it("calls signIn on valid submission", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValueOnce(undefined);

    render(
      <MemoryRouter>
        <SignInPage />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/email/i), "dev@example.com");
    await user.type(screen.getByLabelText(/password/i), "validPassword123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("dev@example.com", "validPassword123");
    });
  });

  it("displays server error message when sign in fails", async () => {
    const user = userEvent.setup();
    mockSignIn.mockRejectedValueOnce(new Error("Invalid login credentials"));

    render(
      <MemoryRouter>
        <SignInPage />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/email/i), "dev@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrongPassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid login credentials");
    });
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <MemoryRouter>
        <SignInPage />
      </MemoryRouter>
    );

    await checkA11y(container);
  });
});
