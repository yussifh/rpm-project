interface CareTeamIllustrationProps {
  /** "hero" = full three-person illustration for the landing page.
   * "admin" | "patient" = a smaller single-figure variant for that
   * role's dashboard banner, sharing the same style/palette. */
  variant?: "hero" | "admin" | "patient";
  className?: string;
}

/**
 * Hand-built flat-illustration character(s) with actual human facial
 * features (eyes, brows, nose, mouth, ears, hair) — the friendly
 * "flat design person" style common on health-tech sites (à la
 * unDraw/Storyset), not a photo or AI-generated raster image. Kept
 * intentionally generic/non-identifiable (no real person depicted) so
 * it's safe to ship as first-party art, sharing one color language
 * across every variant so the landing hero and dashboard banners read
 * as one design system.
 */

function Face({
  cx,
  cy,
  r,
  skin,
  glasses = false,
}: {
  cx: number;
  cy: number;
  r: number;
  skin: string;
  glasses?: boolean;
}) {
  const eyeY = cy - r * 0.06;
  const eyeDx = r * 0.36;
  return (
    <g>
      {/* ears */}
      <ellipse cx={cx - r * 0.98} cy={cy + r * 0.05} rx={r * 0.14} ry={r * 0.22} fill={skin} />
      <ellipse cx={cx + r * 0.98} cy={cy + r * 0.05} rx={r * 0.14} ry={r * 0.22} fill={skin} />
      {/* head */}
      <circle cx={cx} cy={cy} r={r} fill={skin} />
      {/* eyebrows */}
      <path d={`M${cx - eyeDx - 6} ${eyeY - 8} q6 -5 12 0`} stroke="#3A2A1A" strokeWidth={2.2} fill="none" strokeLinecap="round" />
      <path d={`M${cx + eyeDx - 6} ${eyeY - 8} q6 -5 12 0`} stroke="#3A2A1A" strokeWidth={2.2} fill="none" strokeLinecap="round" />
      {/* eyes */}
      <circle cx={cx - eyeDx} cy={eyeY} r={r * 0.075} fill="#2A241D" />
      <circle cx={cx + eyeDx} cy={eyeY} r={r * 0.075} fill="#2A241D" />
      {/* nose */}
      <path d={`M${cx} ${eyeY + 4} q3 ${r * 0.16} -3 ${r * 0.2}`} stroke="#00000022" strokeWidth={2} fill="none" strokeLinecap="round" />
      {/* mouth — gentle smile */}
      <path
        d={`M${cx - r * 0.22} ${cy + r * 0.34} q${r * 0.22} ${r * 0.2} ${r * 0.44} 0`}
        stroke="#7A3B2E"
        strokeWidth={2.4}
        fill="none"
        strokeLinecap="round"
      />
      {glasses && (
        <g stroke="#2E3A46" strokeWidth={2} fill="rgba(255,255,255,0.15)">
          <circle cx={cx - eyeDx} cy={eyeY} r={r * 0.24} />
          <circle cx={cx + eyeDx} cy={eyeY} r={r * 0.24} />
          <path d={`M${cx - eyeDx + r * 0.24} ${eyeY} L${cx + eyeDx - r * 0.24} ${eyeY}`} />
        </g>
      )}
    </g>
  );
}

export function CareTeamIllustration({ variant = "hero", className = "" }: CareTeamIllustrationProps) {
  if (variant === "hero") {
    return (
      <svg viewBox="0 0 360 260" className={className} role="img" aria-label="Illustration of a care team">
        <rect x="0" y="0" width="360" height="260" rx="16" fill="#0F2C4D" />

        {/* back figure — left (nurse) */}
        <g transform="translate(50,66)">
          <rect x="-36" y="66" width="72" height="94" rx="22" fill="#134A7A" />
          <path d="M-14 66 q14 14 28 0 v14 h-28z" fill="#E8B48A" />
          <Face cx={0} cy={32} r={30} skin="#C98A5E" />
          <path
            d="M-28 14 a28 28 0 0 1 56 0 q0 10 -6 16 q2 -12 -6 -16 q-4 8 -16 8 q-14 0 -18 -10 q-6 4 -10 2z"
            fill="#241B14"
          />
        </g>

        {/* back figure — right (white coat) */}
        <g transform="translate(310,66)">
          <rect x="-36" y="66" width="72" height="94" rx="22" fill="#FFFFFF" />
          <path d="M-14 66 q14 14 28 0 v14 h-28z" fill="#E8B48A" />
          <Face cx={0} cy={32} r={30} skin="#E8B48A" />
          <path d="M-27 12 a27 27 0 0 1 54 0 v9 a32 32 0 0 1 -54 0z" fill="#5A3D22" />
        </g>

        {/* front-center figure (clinician with stethoscope) */}
        <g transform="translate(180,44)">
          <rect x="-54" y="90" width="108" height="126" rx="28" fill="#FFFFFF" />
          <path d="M-16 90 q16 16 32 0 v16 h-32z" fill="#D99A6C" />
          <Face cx={0} cy={40} r={38} skin="#D99A6C" />
          <path
            d="M-34 18 a34 34 0 0 1 68 0 q0 12 -8 20 q2 -14 -8 -18 q-6 10 -20 10 q-16 0 -22 -12 q-8 6 -10 0z"
            fill="#241B14"
          />
          {/* coat collar */}
          <path d="M-16 108 L-4 132 L8 108" fill="none" stroke="#E4E8EA" strokeWidth={3} />
          {/* stethoscope */}
          <path d="M-20 116 q-16 12 0 30 q16 18 0 34" fill="none" stroke="#22A996" strokeWidth={5} strokeLinecap="round" />
          <circle cx="-20" cy="180" r="7" fill="#22A996" />
        </g>
      </svg>
    );
  }

  const palette: Record<string, { coat: string; skin: string; hair: string; glasses?: boolean }> = {
    admin: { coat: "#2E3A46", skin: "#D99A6C", hair: "#241B14" },
    patient: { coat: "#22A996", skin: "#E8B48A", hair: "#8A8A8A", glasses: true },
  };
  const { coat, skin, hair, glasses } = palette[variant] ?? palette.admin;

  return (
    <svg viewBox="0 0 120 120" className={className} role="img" aria-label={`Illustration representing the ${variant} role`}>
      <rect
        x="4"
        y="46"
        width="112"
        height="72"
        rx="20"
        fill={coat}
        stroke={coat === "#FFFFFF" ? "#E4E8EA" : "none"}
        strokeWidth={coat === "#FFFFFF" ? 1.5 : 0}
      />
      <path d="M46 46 q14 14 28 0 v10 h-28z" fill={skin} />
      <Face cx={60} cy={40} r={28} skin={skin} glasses={glasses} />
      <path
        d="M32 24a28 28 0 0 1 56 0q0 9 -6 15q1 -10 -6 -13q-5 8 -16 8q-13 0 -18 -9q-6 4 -10 -1z"
        fill={hair}
      />
    </svg>
  );
}
