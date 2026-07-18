import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginForm from "@/components/LoginForm";

// Mock auth so we never hit a network; we test the component's orchestration.
const loginMock = vi.fn();
const registerMock = vi.fn();
vi.mock("@/lib/auth", () => ({
  login: (...args: unknown[]) => loginMock(...args),
  register: (...args: unknown[]) => registerMock(...args),
}));

describe("LoginForm", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("renders the sign-in title by default", () => {
    render(<LoginForm onSuccess={() => {}} />);
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
  });

  it("requires email and password before submitting", async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    render(<LoginForm onSuccess={onSuccess} />);
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByText(/email and password are required/i)).toBeInTheDocument();
    expect(loginMock).not.toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("logs in and calls onSuccess on submit", async () => {
    const user = userEvent.setup();
    loginMock.mockResolvedValue("jwt");
    const onSuccess = vi.fn();
    render(<LoginForm onSuccess={onSuccess} />);
    await user.type(screen.getByPlaceholderText("you@example.com"), "u@e.com");
    await user.type(screen.getByPlaceholderText("Password"), "secret");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(loginMock).toHaveBeenCalledWith("u@e.com", "secret");
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });

  it("shows an error message when auth fails", async () => {
    const user = userEvent.setup();
    loginMock.mockRejectedValue(new Error("Invalid credentials"));
    render(<LoginForm onSuccess={() => {}} />);
    await user.type(screen.getByPlaceholderText("you@example.com"), "u@e.com");
    await user.type(screen.getByPlaceholderText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
  });

  it("registers then logs in when in register mode", async () => {
    const user = userEvent.setup();
    loginMock.mockResolvedValue("jwt");
    registerMock.mockResolvedValue(undefined);
    render(<LoginForm onSuccess={() => {}} />);

    // Switch to register mode.
    await user.click(screen.getByRole("button", { name: /^register$/i }));
    // "Create account" appears in both the heading and the submit button;
    // scope to the heading to assert the full-name field is now shown.
    const heading = screen.getByRole("heading", { name: "Create account" });
    const dialog = heading.closest("div")!.parentElement!;
    expect(within(dialog).getByPlaceholderText("Full name (optional)")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("you@example.com"), "new@e.com");
    await user.type(screen.getByPlaceholderText("Password"), "secret");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(registerMock).toHaveBeenCalledWith("new@e.com", "secret", undefined);
    expect(loginMock).toHaveBeenCalledWith("new@e.com", "secret");
  });
});
