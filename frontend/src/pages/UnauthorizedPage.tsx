import { Link } from "react-router-dom";

export function UnauthorizedPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-sunken px-4 text-center">
      <p className="font-display text-6xl font-extrabold text-status-critical">403</p>
      <h1 className="mt-2 font-display text-xl font-bold text-ink">Access denied</h1>
      <p className="mt-1 text-sm text-ink-soft">You don't have permission to view this page.</p>
      <Link to="/login" className="mt-6 text-sm font-medium text-teal-500 hover:underline">
        Back to sign in
      </Link>
    </div>
  );
}
