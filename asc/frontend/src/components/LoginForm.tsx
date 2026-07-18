"use client";

import { useState } from "react";
import { Zap, Loader2 } from "lucide-react";
import { login, register } from "@/lib/auth";

export default function LoginForm({ onSuccess }: { onSuccess: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError(null);
    if (!email.trim() || !password) {
      setError("Email and password are required");
      return;
    }
    setLoading(true);
    try {
      if (mode === "register") {
        await register(email.trim(), password, fullName.trim() || undefined);
      }
      await login(email.trim(), password);
      onSuccess();
    } catch (err: any) {
      setError(err?.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-6">
          <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center mb-3">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold">ASC</h1>
          <p className="text-sm text-surface-500">Autonomous Software Company</p>
        </div>

        <div className="bg-white rounded-2xl border border-surface-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">
            {mode === "login" ? "Sign in" : "Create account"}
          </h2>

          {error && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2">
              {error}
            </div>
          )}

          <div className="space-y-3">
            {mode === "register" && (
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Full name (optional)"
                className="w-full px-3 py-2.5 rounded-lg border border-surface-300 focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
                disabled={loading}
              />
            )}
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              className="w-full px-3 py-2.5 rounded-lg border border-surface-300 focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              disabled={loading}
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="Password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              className="w-full px-3 py-2.5 rounded-lg border border-surface-300 focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              disabled={loading}
            />
            <button
              onClick={submit}
              disabled={loading}
              className="w-full px-4 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {mode === "login" ? "Sign in" : "Create account"}
            </button>
          </div>

          <p className="text-center text-sm text-surface-500 mt-4">
            {mode === "login" ? "No account?" : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
              className="text-primary-600 font-medium hover:underline"
            >
              {mode === "login" ? "Register" : "Sign in"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
