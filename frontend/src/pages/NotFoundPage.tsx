import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-sunken px-4 text-center">
      <p className="font-display text-6xl font-extrabold text-teal-500">404</p>
      <h1 className="mt-2 font-display text-xl font-bold text-ink">Page not found</h1>
      <p className="mt-1 text-sm text-ink-soft">The page you're looking for doesn't exist.</p>
      <Link to="/login" className="mt-6 text-sm font-medium text-teal-500 hover:underline">
        Back to sign in
      </Link>
    </div>
  );
}
