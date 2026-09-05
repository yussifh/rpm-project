import dashboardBg from "@/assets/images/dashboard-bg.jpg";
import aiHealthHero from "@/assets/images/ai-health-hero.jpg";

interface DashboardWelcomeBannerProps {
  variant: "admin" | "patient";
  name?: string;
  subtitle: string;
}

const PHOTO_BY_VARIANT: Record<DashboardWelcomeBannerProps["variant"], string> = {
  admin: dashboardBg,
  patient: aiHealthHero,
};

/** Full-bleed photo hero banner at the top of each dashboard. The admin
 * banner keeps the photo clear (bottom-weighted gradient only, just
 * enough for the heading text to stay legible). The patient banner uses
 * the AI/health hero image dimmed across its whole surface — a flat dark
 * overlay stacked under the same bottom gradient — since here the photo
 * is decorative/thematic rather than the star, and full brightness would
 * compete with the "Welcome back" heading and the AI framing it's meant
 * to evoke, not showcase itself. */
export function DashboardWelcomeBanner({ variant, name, subtitle }: DashboardWelcomeBannerProps) {
  return (
    <div
      className="relative flex h-56 items-end overflow-hidden rounded-xl bg-brand-navy px-6 py-6 sm:h-64 sm:px-8"
      style={{
        backgroundImage: `url(${PHOTO_BY_VARIANT[variant]})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      {variant === "patient" && (
        <div className="pointer-events-none absolute inset-0" style={{ background: "rgba(10,26,46,0.55)" }} />
      )}
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: "linear-gradient(to top, rgba(10,26,46,0.9) 0%, rgba(10,26,46,0.35) 55%, rgba(10,26,46,0) 85%)" }}
      />
      <div className="relative">
        <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
          Welcome back{name ? `, ${name}` : ""}
        </h1>
        <p className="mt-1 text-sm text-white/85">{subtitle}</p>
      </div>
    </div>
  );
}
