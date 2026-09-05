import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/useAuth";
import { Modal } from "@/components/ui/Modal";

const DASHBOARD_BY_ROLE: Record<string, string> = {
  admin: "/admin",
  patient: "/patient",
};

const inputClass = "mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm focus:border-teal-500";

/**
 * Sign-in as an overlay on top of the landing page, rather than a
 * separate route — same login logic as pages/auth/LoginPage.tsx (that
 * page stays intact and still handles the cases that genuinely need a
 * real navigation: ProtectedRoute redirecting here on session expiry,
 * or someone landing on /login directly). This modal is only for the
 * landing page's own Sign In / Login buttons, so choosing to sign in
 * never leaves the landing page behind it.
 */
export function LoginModal({ onClose }: { onClose: () => void }) {
  const { login } = useAuth();
  const navigate = useNavigate();

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
      navigate(DASHBOARD_BY_ROLE[user.role], { replace: true });
    } catch {
      setError("Incorrect email or password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal title="Sign in" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="login-modal-email" className="block text-sm font-medium text-ink">
            Email
          </label>
          <input
            id="login-modal-email"
            type="email"
            required
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="login-modal-password" className="block text-sm font-medium text-ink">
            Password
          </label>
          <input
            id="login-modal-password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
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

        <p className="text-center text-xs text-ink-soft">
          Don't have an account? Ask your clinic administrator to set one up for you.
        </p>
      </form>
    </Modal>
  );
}
