/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Design system, v2 — restyled to match a reference admin-dashboard
        // look the user provided: a bright teal header/brand color, a dark
        // navy icon sidebar with a profile widget, and card-based stats with
        // colored accent bars. Kept as named tokens (not just hardcoded hex
        // in components) so the palette stays a one-file change.
        ink: {
          DEFAULT: "#1A2530",
          soft: "#5B6B76",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          sunken: "#F4F6F7",
          border: "#E4E8EA",
        },
        // Bright teal brand color — the header bar, primary buttons, active
        // nav accents, and the floating action button all pull from this.
        teal: {
          50: "#E8F8F5",
          100: "#C6EEE7",
          400: "#2FBDA8",
          500: "#22A996",  // primary brand
          600: "#1B8B7B",
          700: "#166F63",
        },
        // Dark navy sidebar — distinct from the teal brand color so nav
        // stays legible and doesn't compete with teal action buttons/badges.
        navy: {
          400: "#3E4C59",
          500: "#2E3A46",  // sidebar background
          600: "#242E38",
          700: "#1B232B",
        },
        // Landing-page-only palette, sampled directly from the reference
        // design: deep navy nav/hero, and a green CTA color distinct from
        // the app's internal teal brand color (kept separate so the
        // already-tested internal dashboards aren't touched).
        brand: {
          navy: "#173A63", // header/hero background
          "navy-light": "#2A5490",
          blue: "#2D5F94",
          green: "#22C55E", // Sign Up / Search CTA
          "green-dark": "#16A34A",
        },
        status: {
          stable: "#3E8E5B",
          warning: "#E2A63B",
          critical: "#C0463C",
          info: "#3C6E9C",
        },
        // Small palette of accent colors for colored left-border rows
        // (event/alert/appointment list items) — echoes the reference
        // template's multi-colored event list.
        accent: {
          teal: "#2FBDA8",
          blue: "#3D7FE0",
          purple: "#8B6FD6",
          amber: "#E2A63B",
          red: "#D9544F",
        },
      },
      fontFamily: {
        display: ["Manrope", "sans-serif"],
        sans: ["Inter", "sans-serif"],
        // Signature touch: vitals/timestamps/IDs render in a monospace
        // tabular face — evoking a bedside monitor's digital readout.
        mono: ["IBM Plex Mono", "monospace"],
      },
      backgroundImage: {
        "teal-header": "linear-gradient(90deg, #2FBDA8 0%, #22A996 100%)",
      },
    },
  },
  plugins: [],
};
