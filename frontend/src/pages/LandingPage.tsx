import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  Activity,
  Bell,
  BrainCircuit,
  FileText,
  Droplet,
  Heart,
  Brain,
  UserPlus,
  ClipboardList,
  TrendingUp,
  Mail,
  Phone,
  MapPin,
  LogIn,
  Search,
  Play,
  ArrowRight,
  Check,
} from "lucide-react";
import { useAuth } from "@/context/useAuth";
import { CareTeamIllustration } from "@/components/ui/CareTeamIllustration";
import { Modal } from "@/components/ui/Modal";
import { LoginModal } from "@/components/auth/LoginModal";
import aiHealthHero from "@/assets/images/ai-health-hero.jpg";

const FEATURES = [
  { icon: Activity, bg: "bg-blue-50", color: "text-blue-600", title: "Health Monitoring", description: "Track blood pressure, blood sugar, heart rate, and more." },
  { icon: Bell, bg: "bg-green-50", color: "text-green-600", title: "Real-time Alerts", description: "Get instant alerts for abnormal readings and emergencies." },
  { icon: BrainCircuit, bg: "bg-purple-50", color: "text-purple-600", title: "AI Risk Prediction", description: "Trained machine learning models assess your diabetes, hypertension, and stroke risk." },
  { icon: FileText, bg: "bg-orange-50", color: "text-orange-600", title: "Health Reports", description: "View trends and download AI-generated health reports easily." },
];

const AUDIENCES = [
  {
    icon: Droplet,
    color: "text-orange-500",
    bg: "bg-orange-50",
    title: "Diabetes Patients",
    description: "Monitor your blood sugar levels and keep your diabetes under control.",
    details: [
      "Log blood glucose, blood pressure, weight, and temperature from home",
      "AI risk model flags concerning glucose trends as they emerge",
      "See your full glucose history as a trend, not just one reading",
      "Get medication reminders tied to your own tracking",
    ],
  },
  {
    icon: Heart,
    color: "text-red-500",
    bg: "bg-red-50",
    title: "Hypertension Patients",
    description: "Track your blood pressure regularly and stay heart-healthy.",
    details: [
      "Log systolic/diastolic BP, heart rate, respiratory rate, SpO2, and weight",
      "AI risk model watches for patterns that suggest a hypertensive crisis",
      "Automatic alerts the moment a reading is dangerously high",
      "See your BP trend over time instead of judging one reading in isolation",
    ],
  },
  {
    icon: Brain,
    color: "text-purple-500",
    bg: "bg-purple-50",
    title: "Stroke Patients",
    description: "Monitor your recovery and help prevent another stroke with continuous care.",
    details: [
      "Track blood pressure, heart rate, SpO2, temperature, respiratory rate, and weight",
      "AI risk model estimates recurrence risk from your vitals history",
      "Instant alerts if your readings suggest a warning sign",
      "Built for ongoing post-stroke monitoring, not a one-time check-in",
    ],
  },
];

const STEPS = [
  { icon: UserPlus, title: "Get Enrolled", description: "Your clinic admin sets up your account for you." },
  { icon: ClipboardList, title: "Add Readings", description: "Enter your health readings regularly in the system." },
  { icon: BrainCircuit, title: "AI Assessment", description: "The trained ML model analyzes your data and estimates your risk." },
  { icon: TrendingUp, title: "Get Feedback", description: "Receive AI-generated advice, trend explanations, and alerts." },
];

const NAV_LINKS = [
  { label: "Home", href: "#top" },
  { label: "About", href: "#about" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "For Patients", href: "#audience" },
  { label: "AI & ML", href: "#features" },
  { label: "Contact", href: "#contact" },
];

export function LandingPage() {
  const { user } = useAuth();
  const [openAudience, setOpenAudience] = useState<(typeof AUDIENCES)[number] | null>(null);
  const [showLogin, setShowLogin] = useState(false);

  if (user) {
    return <Navigate to={`/${user.role}`} replace />;
  }

  return (
    <div id="top" className="min-h-screen bg-white">
      {/* --- Tier 1: utility bar --- */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border px-6 py-4 sm:px-10">
        <span className="inline-flex items-center gap-2">
          <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
            <circle cx="17" cy="17" r="17" fill="#173A63" />
            <path
              d="M9 18h3l2-5 3 10 2-5h6"
              fill="none"
              stroke="#22C55E"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="leading-tight">
            <span className="block font-display text-lg font-bold text-brand-navy">RPM System</span>
            <span className="block text-[11px] text-ink-soft">Remote Patient Monitoring</span>
          </span>
        </span>

        <div className="relative order-3 w-full max-w-md sm:order-2 sm:w-auto sm:flex-1">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft" />
          <input
            type="text"
            placeholder="Search patients, features…"
            className="w-full rounded-lg border border-surface-border bg-surface-sunken py-2 pl-9 pr-3 text-sm focus:border-teal-500 focus:outline-none"
          />
        </div>

        <div className="order-2 flex items-center gap-3 sm:order-3">
          <button
            type="button"
            onClick={() => setShowLogin(true)}
            className="flex items-center gap-1.5 rounded-lg bg-brand-green px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-green-dark"
          >
            <LogIn size={14} />
            Login
          </button>
        </div>
      </div>

      {/* --- Tier 2: nav bar --- */}
      <nav className="hidden flex-wrap justify-center gap-1 bg-brand-navy px-6 sm:flex sm:px-10">
        {NAV_LINKS.map(({ label, href }, i) => (
          <a
            key={label}
            href={href}
            className={`px-4 py-2.5 text-sm font-medium text-white/85 hover:text-white ${
              i === 0 ? "border-b-2 border-brand-green text-white" : ""
            }`}
          >
            {label}
          </a>
        ))}
      </nav>

      {/* --- Hero ---
          Same full-bleed-photo-plus-dim-overlay structure as the patient
          dashboard's DashboardWelcomeBanner (background-image + a flat
          dark tint, rather than a small inset photo card) — kept as one
          continuous background image so text reads consistently over it
          regardless of what's visually underneath at any given point. */}
      <section className="relative overflow-hidden">
        <div
          className="relative"
          style={{
            backgroundImage: `url(${aiHealthHero})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        >
          <span className="sr-only">
            Background: a clinician's hand and a robotic hand each holding a glowing icon, representing health
            data connecting to AI analysis.
          </span>
          {/* Flat dim, sampled from the same brand-navy used elsewhere on
              this page (nav bar, CTA banner) so the tint reads as
              intentional brand color rather than a generic dark filter —
              opacity high enough that white text stays readable no matter
              how bright the underlying photo is at that point. */}
          <div className="pointer-events-none absolute inset-0" style={{ background: "rgba(23,58,99,0.78)" }} />

          <div className="relative mx-auto max-w-6xl px-6 py-20 sm:px-10 sm:py-28">
            <div className="max-w-2xl">
              <h1 className="font-display text-3xl font-bold leading-tight text-white sm:text-4xl">
                AI-Powered Risk Prediction for
                <br />
                <span className="text-teal-100">Diabetes, Hypertension</span>
                <br />
                <span className="text-teal-100">and Stroke</span>
              </h1>
              <p className="mt-5 max-w-md text-white/85">
                Trained machine learning models analyze your vitals and health history to assess your risk —
                explained in plain language by your AI Health Assistant. Track trends, get alerts, and understand
                your health, anywhere, anytime.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setShowLogin(true)}
                  className="rounded-lg bg-brand-green px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-green-dark"
                >
                  Sign In
                </button>
                <a
                  href="#how-it-works"
                  className="flex items-center gap-2 rounded-lg border border-white px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-brand-navy"
                >
                  <Play size={14} />
                  How It Works
                </a>
              </div>
            </div>

            {/* Three vital-reading cards — kept as solid white cards (dark
                text) rather than translucent, so they read clearly as a
                UI element sitting on top of the photo rather than blending
                into the dim, regardless of what's behind them. */}
            <div className="mt-12 flex flex-wrap gap-4">
              <div className="rounded-lg border border-surface-border bg-white p-3 shadow-lg">
                <div className="flex items-center gap-1.5 text-xs font-medium text-ink">
                  <Heart size={13} className="text-red-500" />
                  Blood Pressure
                </div>
                <p className="readout mt-1 text-lg font-bold text-ink">
                  120/80 <span className="text-xs font-normal text-ink-soft">mmHg</span>
                </p>
                <p className="mt-0.5 flex items-center gap-1 text-[11px] text-status-stable">
                  <span className="h-1.5 w-1.5 rounded-full bg-status-stable" /> Normal
                </p>
              </div>

              <div className="rounded-lg border border-surface-border bg-white p-3 shadow-lg">
                <div className="flex items-center gap-1.5 text-xs font-medium text-ink">
                  <Droplet size={13} className="text-blue-500" />
                  Blood Sugar
                </div>
                <p className="readout mt-1 text-lg font-bold text-ink">
                  5.8 <span className="text-xs font-normal text-ink-soft">mmol/L</span>
                </p>
                <p className="mt-0.5 flex items-center gap-1 text-[11px] text-status-stable">
                  <span className="h-1.5 w-1.5 rounded-full bg-status-stable" /> Normal
                </p>
              </div>

              <div className="rounded-lg border border-surface-border bg-white p-3 shadow-lg">
                <div className="flex items-center gap-1.5 text-xs font-medium text-ink">
                  <Activity size={13} className="text-red-500" />
                  Heart Rate
                </div>
                <p className="readout mt-1 text-lg font-bold text-ink">
                  72 <span className="text-xs font-normal text-ink-soft">bpm</span>
                </p>
                <p className="mt-0.5 flex items-center gap-1 text-[11px] text-status-stable">
                  <span className="h-1.5 w-1.5 rounded-full bg-status-stable" /> Normal
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* --- Features --- */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-16 sm:px-10">
        <h2 className="text-center font-display text-2xl font-bold text-ink sm:text-3xl">Our Core Features</h2>
        <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, bg, color, title, description }) => (
            <div key={title} className="rounded-xl border border-surface-border bg-white p-6 text-center shadow-sm">
              <div className={`mx-auto flex h-12 w-12 items-center justify-center rounded-full ${bg} ${color}`}>
                <Icon size={22} />
              </div>
              <h3 className="mt-4 font-display text-base font-bold text-ink">{title}</h3>
              <p className="mt-1.5 text-sm text-ink-soft">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* --- Who can use --- */}
      <section id="audience" className="bg-[#EEF3F8] px-6 py-16 sm:px-10">
        <h2 className="text-center font-display text-2xl font-bold text-ink sm:text-3xl">Who Can Use RPM System?</h2>
        <div className="mx-auto mt-10 grid max-w-6xl grid-cols-1 gap-6 sm:grid-cols-3">
          {AUDIENCES.map((audience) => (
            <div key={audience.title} className="rounded-xl border border-surface-border bg-white p-6 shadow-sm">
              <div className={`flex h-11 w-11 items-center justify-center rounded-full ${audience.bg} ${audience.color}`}>
                <audience.icon size={20} />
              </div>
              <h3 className="mt-4 font-display text-base font-bold text-blue-700">{audience.title}</h3>
              <p className="mt-1.5 text-sm text-ink-soft">{audience.description}</p>
              <button
                type="button"
                onClick={() => setOpenAudience(audience)}
                className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline"
              >
                Learn more <ArrowRight size={13} />
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* --- How it works --- */}
      <section id="how-it-works" className="mx-auto max-w-6xl px-6 py-16 sm:px-10">
        <h2 className="text-center font-display text-2xl font-bold text-ink sm:text-3xl">How It Works</h2>
        <div className="mt-12 grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ icon: Icon, title, description }, i) => (
            <div key={title} className="relative text-center">
              {i < STEPS.length - 1 && (
                <div className="absolute left-1/2 top-8 hidden w-full border-t-2 border-dashed border-surface-border lg:block" />
              )}
              <div className="relative z-10 mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-surface-border bg-white text-brand-navy shadow-sm">
                <Icon size={24} />
              </div>
              <span className="mt-3 inline-flex h-5 w-5 items-center justify-center rounded-full bg-brand-green text-[11px] font-bold text-white">
                {i + 1}
              </span>
              <h3 className="mt-2 font-display text-sm font-bold text-ink">{title}</h3>
              <p className="mt-1 text-xs text-ink-soft">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* --- CTA banner --- */}
      <section id="about" className="mx-auto max-w-6xl px-6 pb-16 sm:px-10">
        <div className="flex flex-col items-center gap-6 rounded-2xl bg-brand-navy px-8 py-10 sm:flex-row sm:px-12">
          <CareTeamIllustration variant="patient" className="h-20 w-20 shrink-0" />
          <div className="flex-1 text-center sm:text-left">
            <h2 className="font-display text-xl font-bold text-white sm:text-2xl">Take Control of Your Health Today</h2>
            <p className="mt-1 text-sm text-white/75">
              Already set up by your clinic? Sign in to see your dashboard.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowLogin(true)}
            className="flex shrink-0 items-center gap-2 rounded-lg bg-brand-green px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-green-dark"
          >
            Sign In <ArrowRight size={15} />
          </button>
        </div>
      </section>

      {/* --- Footer --- */}
      <footer id="contact" className="bg-brand-navy px-6 py-12 text-white sm:px-10">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <span className="inline-flex items-center gap-2">
              <svg width="24" height="24" viewBox="0 0 34 34" fill="none">
                <circle cx="17" cy="17" r="17" fill="white" fillOpacity="0.15" />
                <path d="M9 18h3l2-5 3 10 2-5h6" fill="none" stroke="#22C55E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="font-display text-base font-bold text-white">RPM System</span>
            </span>
            <p className="mt-3 text-sm text-white/70">
              Your health, our priority. Remote monitoring for a healthier tomorrow.
            </p>
          </div>

          <div>
            <h4 className="text-sm font-bold text-white">Quick Links</h4>
            <ul className="mt-3 space-y-2 text-sm text-white/70">
              <li><a href="#top" className="hover:text-white">Home</a></li>
              <li><a href="#about" className="hover:text-white">About</a></li>
              <li><a href="#how-it-works" className="hover:text-white">How It Works</a></li>
              <li><a href="#audience" className="hover:text-white">For Patients</a></li>
              <li><Link to="/login" className="hover:text-white">AI &amp; ML</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-bold text-white">Support</h4>
            {/* Placeholder items — no standalone pages exist for these yet. */}
            <ul className="mt-3 space-y-2 text-sm text-white/50">
              <li>Help Center</li>
              <li>FAQs</li>
              <li>Terms of Service</li>
              <li>Privacy Policy</li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-bold text-white">Contact Us</h4>
            {/* Placeholder contact details — replace with real values before launch. */}
            <ul className="mt-3 space-y-2 text-sm text-white/70">
              <li className="flex items-center gap-2">
                <Phone size={14} /> +1 (555) 000-0000
              </li>
              <li className="flex items-center gap-2">
                <Mail size={14} /> support@example.com
              </li>
              <li className="flex items-center gap-2">
                <MapPin size={14} /> Your City, Country
              </li>
            </ul>
          </div>
        </div>

        <div className="mx-auto mt-10 max-w-6xl border-t border-white/15 pt-6 text-center text-xs text-white/50">
          © 2026 RPM System. All rights reserved.
        </div>
      </footer>

      {openAudience && (
        <Modal title={openAudience.title} onClose={() => setOpenAudience(null)}>
          <p className="text-sm text-ink-soft">{openAudience.description}</p>
          <ul className="mt-4 space-y-2">
            {openAudience.details.map((detail) => (
              <li key={detail} className="flex items-start gap-2 text-sm text-ink">
                <Check size={15} className="mt-0.5 shrink-0 text-teal-600" />
                <span>{detail}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-ink-soft">
            Accounts are set up by your clinic admin — there's no public sign-up.
          </p>
          <button
            type="button"
            onClick={() => {
              setOpenAudience(null);
              setShowLogin(true);
            }}
            className="mt-4 inline-flex w-full items-center justify-center rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700"
          >
            Go to Login
          </button>
        </Modal>
      )}

      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}
    </div>
  );
}
