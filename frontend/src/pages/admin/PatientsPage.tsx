import { Fragment, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import { adminApi } from "@/services/adminApi";
import { patientApi } from "@/services/patientApi";
import { reportApi } from "@/services/reportApi";
import type { PatientCreatePayload } from "@/types/admin";
import type { PatientProfile } from "@/types/patient";

const inputClass = "mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm focus:border-teal-500";
const labelClass = "block text-sm font-medium text-ink";

const initialForm: PatientCreatePayload = {
  email: "",
  password: "",
  full_name: "",
  date_of_birth: "",
  gender: "female",
};

interface EditForm {
  full_name: string;
  email: string;
  phone_number: string;
  date_of_birth: string;
  gender: string;
  blood_group: string;
  height_cm: string;
  weight_kg: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  chronic_conditions_summary: string;
}

function toEditForm(patient: PatientProfile): EditForm {
  return {
    full_name: patient.full_name ?? "",
    email: patient.email ?? "",
    phone_number: patient.phone_number ?? "",
    date_of_birth: patient.date_of_birth,
    gender: patient.gender,
    blood_group: patient.blood_group ?? "",
    height_cm: patient.height_cm?.toString() ?? "",
    weight_kg: patient.weight_kg?.toString() ?? "",
    emergency_contact_name: patient.emergency_contact_name ?? "",
    emergency_contact_phone: patient.emergency_contact_phone ?? "",
    chronic_conditions_summary: patient.chronic_conditions_summary ?? "",
  };
}

export function PatientsPage() {
  const navigate = useNavigate();
  const { data: patients, isLoading, error, refetch } = useAsyncData(() => patientApi.list(), []);
  const { data: users, refetch: refetchUsers } = useAsyncData(() => adminApi.listUsers("patient"), []);

  const [pendingId, setPendingId] = useState<string | null>(null);

  const [form, setForm] = useState<PatientCreatePayload>(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  function update<K extends keyof PatientCreatePayload>(key: K, value: PatientCreatePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);
    try {
      await adminApi.createPatient({
        ...form,
        phone_number: form.phone_number || undefined,
        blood_group: form.blood_group || undefined,
      });
      setForm(initialForm);
      refetch();
      refetchUsers();
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Couldn't create patient account. Please check the details and try again.";
      setFormError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const isActiveByUserId = new Map(users?.map((u) => [u.id, u.is_active]) ?? []);

  async function toggleActive(userId: string, isActive: boolean) {
    setPendingId(userId);
    try {
      if (isActive) {
        await adminApi.deactivateUser(userId);
      } else {
        await adminApi.activateUser(userId);
      }
      refetchUsers();
    } finally {
      setPendingId(null);
    }
  }

  function startEdit(patient: PatientProfile) {
    setEditingId(patient.id);
    setEditForm(toEditForm(patient));
    setEditError(null);
  }

  function updateEdit<K extends keyof EditForm>(key: K, value: EditForm[K]) {
    setEditForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function saveEdit(patient: PatientProfile) {
    if (!editForm) return;
    setEditError(null);
    setIsSaving(true);
    try {
      await Promise.all([
        adminApi.updateUser(patient.user_id, {
          full_name: editForm.full_name,
          email: editForm.email,
          phone_number: editForm.phone_number || undefined,
        }),
        adminApi.updatePatient(patient.id, {
          date_of_birth: editForm.date_of_birth,
          gender: editForm.gender,
          blood_group: editForm.blood_group || undefined,
          height_cm: editForm.height_cm ? Number(editForm.height_cm) : undefined,
          weight_kg: editForm.weight_kg ? Number(editForm.weight_kg) : undefined,
          emergency_contact_name: editForm.emergency_contact_name || undefined,
          emergency_contact_phone: editForm.emergency_contact_phone || undefined,
          chronic_conditions_summary: editForm.chronic_conditions_summary || undefined,
        }),
      ]);
      setEditingId(null);
      setEditForm(null);
      refetch();
      refetchUsers();
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Couldn't save changes. Please try again.";
      setEditError(message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-ink">Patients</h1>
      <p className="mt-1 text-sm text-ink-soft">All registered patients.</p>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Add a patient</h2>
        <form onSubmit={handleCreate} className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className={labelClass}>Full name</label>
            <input required value={form.full_name} onChange={(e) => update("full_name", e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input type="email" required value={form.email} onChange={(e) => update("email", e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Phone number</label>
            <input value={form.phone_number ?? ""} onChange={(e) => update("phone_number", e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Date of birth</label>
            <input
              type="date"
              required
              value={form.date_of_birth}
              onChange={(e) => update("date_of_birth", e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Gender</label>
            <select value={form.gender} onChange={(e) => update("gender", e.target.value as PatientCreatePayload["gender"])} className={inputClass}>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Blood group (optional)</label>
            <input value={form.blood_group ?? ""} onChange={(e) => update("blood_group", e.target.value)} className={inputClass} />
          </div>

          {formError && <p className="sm:col-span-2 text-sm text-status-critical">{formError}</p>}

          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-teal-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-teal-600 disabled:opacity-60"
            >
              {isSubmitting ? "Creating…" : "Create patient account"}
            </button>
          </div>
        </form>
      </Card>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Directory</h2>
        {error && <p className="mt-4 text-sm text-status-critical">Couldn't load patients.</p>}
        {isLoading ? (
          <p className="mt-4 text-sm text-ink-soft">Loading…</p>
        ) : !patients || patients.length === 0 ? (
          <p className="mt-4 text-sm text-ink-soft">No patients have registered yet.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs uppercase tracking-wide text-ink-soft">
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Email</th>
                  <th className="py-2 pr-4 font-medium">Gender</th>
                  <th className="py-2 pr-4 font-medium">DOB</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 pr-4 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {patients.map((patient) => {
                  const isActive = isActiveByUserId.get(patient.user_id) ?? true;
                  const isEditing = editingId === patient.id;
                  return (
                    <Fragment key={patient.id}>
                      <tr className="border-b border-surface-border last:border-0">
                        <td className="py-3 pr-4 font-medium text-ink">{patient.full_name}</td>
                        <td className="py-3 pr-4 text-ink-soft">{patient.email}</td>
                        <td className="py-3 pr-4 capitalize text-ink-soft">{patient.gender}</td>
                        <td className="py-3 pr-4 readout text-ink-soft">{patient.date_of_birth}</td>
                        <td className="py-3 pr-4">
                          <Badge tone={isActive ? "stable" : "neutral"}>{isActive ? "Active" : "Inactive"}</Badge>
                        </td>
                        <td className="py-3 pr-4 whitespace-nowrap">
                          <button
                            onClick={() => navigate(`/admin/patients/${patient.id}`)}
                            className="mr-3 text-sm font-medium text-teal-600 hover:underline"
                          >
                            View Records
                          </button>
                          <button
                            onClick={() => (isEditing ? setEditingId(null) : startEdit(patient))}
                            className="mr-3 text-sm font-medium text-teal-600 hover:underline"
                          >
                            {isEditing ? "Cancel" : "Edit"}
                          </button>
                          <button
                            onClick={() => toggleActive(patient.user_id, isActive)}
                            disabled={pendingId === patient.user_id}
                            className="mr-3 text-sm font-medium text-teal-600 hover:underline disabled:opacity-60"
                          >
                            {isActive ? "Deactivate" : "Activate"}
                          </button>
                          <button
                            onClick={() => reportApi.downloadSummary(patient.id, patient.full_name)}
                            className="text-sm font-medium text-teal-600 hover:underline"
                          >
                            Report
                          </button>
                        </td>
                      </tr>
                      {isEditing && editForm && (
                        <tr className="border-b border-surface-border bg-surface-sunken">
                          <td colSpan={6} className="p-4">
                            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                              <div>
                                <label className={labelClass}>Full name</label>
                                <input value={editForm.full_name} onChange={(e) => updateEdit("full_name", e.target.value)} className={inputClass} />
                              </div>
                              <div>
                                <label className={labelClass}>Email</label>
                                <input value={editForm.email} onChange={(e) => updateEdit("email", e.target.value)} className={inputClass} />
                              </div>
                              <div>
                                <label className={labelClass}>Phone</label>
                                <input value={editForm.phone_number} onChange={(e) => updateEdit("phone_number", e.target.value)} className={inputClass} />
                              </div>
                              <div>
                                <label className={labelClass}>Date of birth</label>
                                <input
                                  type="date"
                                  value={editForm.date_of_birth}
                                  onChange={(e) => updateEdit("date_of_birth", e.target.value)}
                                  className={inputClass}
                                />
                              </div>
                              <div>
                                <label className={labelClass}>Gender</label>
                                <select value={editForm.gender} onChange={(e) => updateEdit("gender", e.target.value)} className={inputClass}>
                                  <option value="female">Female</option>
                                  <option value="male">Male</option>
                                  <option value="other">Other</option>
                                </select>
                              </div>
                              <div>
                                <label className={labelClass}>Blood group</label>
                                <input value={editForm.blood_group} onChange={(e) => updateEdit("blood_group", e.target.value)} className={inputClass} />
                              </div>
                              <div>
                                <label className={labelClass}>Height (cm)</label>
                                <input
                                  type="number"
                                  value={editForm.height_cm}
                                  onChange={(e) => updateEdit("height_cm", e.target.value)}
                                  className={inputClass}
                                />
                              </div>
                              <div>
                                <label className={labelClass}>Weight (kg)</label>
                                <input
                                  type="number"
                                  value={editForm.weight_kg}
                                  onChange={(e) => updateEdit("weight_kg", e.target.value)}
                                  className={inputClass}
                                />
                              </div>
                              <div>
                                <label className={labelClass}>Emergency contact name</label>
                                <input
                                  value={editForm.emergency_contact_name}
                                  onChange={(e) => updateEdit("emergency_contact_name", e.target.value)}
                                  className={inputClass}
                                />
                              </div>
                              <div>
                                <label className={labelClass}>Emergency contact phone</label>
                                <input
                                  value={editForm.emergency_contact_phone}
                                  onChange={(e) => updateEdit("emergency_contact_phone", e.target.value)}
                                  className={inputClass}
                                />
                              </div>
                              <div className="sm:col-span-3">
                                <label className={labelClass}>Chronic conditions summary</label>
                                <input
                                  value={editForm.chronic_conditions_summary}
                                  onChange={(e) => updateEdit("chronic_conditions_summary", e.target.value)}
                                  className={inputClass}
                                />
                              </div>
                            </div>
                            {editError && <p className="mt-3 text-sm text-status-critical">{editError}</p>}
                            <div className="mt-3 flex gap-3">
                              <button
                                onClick={() => saveEdit(patient)}
                                disabled={isSaving}
                                className="rounded-lg bg-teal-500 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
                              >
                                {isSaving ? "Saving…" : "Save changes"}
                              </button>
                              <button
                                onClick={() => setEditingId(null)}
                                className="rounded-lg border border-surface-border px-4 py-2 text-xs font-medium text-ink hover:bg-white"
                              >
                                Cancel
                              </button>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
