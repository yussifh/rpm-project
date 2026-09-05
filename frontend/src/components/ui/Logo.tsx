interface LogoProps {
  /** "light" for use on dark/teal backgrounds (header), "dark" for use on white backgrounds (landing page nav). */
  variant?: "light" | "dark";
  className?: string;
}

/** Brand mark: a rounded shield with a medical cross, echoing the
 * reference design's blue-square-with-cross logo — built as inline SVG
 * so it stays crisp at any size and inherits currentColor for theming,
 * rather than shipping a raster image asset. */
export function Logo({ variant = "light", className = "" }: LogoProps) {
  const textColor = variant === "light" ? "text-white" : "text-ink";

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="30" height="30" rx="8" fill="currentColor" className="text-teal-500" />
        <path
          d="M15 8v14M8 15h14"
          stroke="white"
          strokeWidth="3.2"
          strokeLinecap="round"
        />
      </svg>
      <span className={`font-display text-lg font-bold whitespace-nowrap ${textColor}`}>RPM System</span>
    </span>
  );
}
