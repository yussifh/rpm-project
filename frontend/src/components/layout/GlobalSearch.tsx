import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, User } from "lucide-react";
import { useAsyncData } from "@/hooks/useAsyncData";
import { patientApi } from "@/services/patientApi";
import type { UserRole } from "@/types/auth";

interface GlobalSearchProps {
  role: UserRole;
}

const MAX_RESULTS = 6;

/** Header search box. Only admin has a patient list to search — patients
 * don't get this box at all (see Header.tsx) since there's no "patient
 * list" for them to search. Filtering happens client-side against the
 * already-fetched list, which is fine at this app's scale and avoids a
 * network round trip per keystroke. */
export function GlobalSearch({ role }: GlobalSearchProps) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const canSearchPatients = role === "admin";
  const { data: patients } = useAsyncData(
    () => (canSearchPatients ? patientApi.list() : Promise.resolve([])),
    [canSearchPatients]
  );

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || !patients) return [];
    return patients
      .filter(
        (p) =>
          (p.full_name ?? "").toLowerCase().includes(q) ||
          (p.email ?? "").toLowerCase().includes(q)
      )
      .slice(0, MAX_RESULTS);
  }, [query, patients]);

  function goToPatient() {
    setQuery("");
    setIsFocused(false);
    // Admin has no per-patient detail route yet — land on the
    // management list rather than a dead link.
    navigate(`/admin/patients`);
  }

  const showDropdown = isFocused && query.trim().length > 0;

  return (
    <div ref={containerRef} className="relative ml-4 max-w-md flex-1">
      <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/70" />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setTimeout(() => setIsFocused(false), 150)}
        placeholder="Search patients by name or email..."
        className="w-full rounded-lg border border-white/20 bg-white/10 py-2 pl-9 pr-3 text-sm text-white placeholder-white/60 focus:bg-white/20 focus:outline-none"
      />

      {showDropdown && (
        <div className="absolute left-0 right-0 top-full z-40 mt-1 max-h-72 overflow-y-auto rounded-lg border border-surface-border bg-white py-1 text-left shadow-lg">
          {results.length === 0 ? (
            <p className="px-3 py-2 text-sm text-ink-soft">No patients match "{query}"</p>
          ) : (
            results.map((patient) => (
              <button
                key={patient.id}
                type="button"
                onMouseDown={(e) => e.preventDefault()} // keep input focus so onBlur doesn't fire before onClick
                onClick={() => goToPatient()}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-ink hover:bg-surface-sunken"
              >
                <User size={14} className="shrink-0 text-ink-soft" />
                <span className="flex-1 truncate">
                  <span className="font-medium">{patient.full_name ?? "Unnamed patient"}</span>
                  {patient.email && <span className="ml-1.5 text-xs text-ink-soft">{patient.email}</span>}
                </span>
                {patient.primary_condition && (
                  <span className="shrink-0 rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-medium capitalize text-teal-700">
                    {patient.primary_condition}
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
