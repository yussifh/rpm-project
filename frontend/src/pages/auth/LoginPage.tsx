import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/useAuth";
import { Card } from "@/components/ui/Card";

const DASHBOARD_BY_ROLE: Record<string, string> = {
  admin: "/admin",
  patient: "/patient",
};

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const user = await login({ email, password });
      const redirectTo = (location.state as { from?: Location })?.from?.pathname;
      navigate(redirectTo || DASHBOARD_BY_ROLE[user.role], { replace: true });
    } catch {
      setError("Incorrect email or password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-green-dark to-brand-green px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 h-3 w-3 rounded-full bg-white" />
          <h1 className="font-display text-2xl font-bold text-white">RPM System</h1>
          <p className="mt-1 text-sm text-white/80">Remote Patient Monitoring</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-ink">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm focus:border-teal-500"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-ink">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm focus:border-teal-500"
              />
            </div>

            {error && <p className="text-sm text-status-critical">{error}</p>}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-lg bg-teal-500 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-teal-600 disabled:opacity-60"
            >
              {isSubmitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </Card>

        <p className="mt-6 text-center text-sm text-white/80">
          Don't have an account? Ask your clinic administrator to set one up for you.
        </p>
      </div>
    </div>
  );
}
