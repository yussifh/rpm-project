import { useState, type FormEvent } from "react";
import { Card } from "@/components/ui/Card";
import { useAuth } from "@/context/useAuth";
import { authApi } from "@/services/authApi";
import { patientApi } from "@/services/patientApi";
import { useAsyncData } from "@/hooks/useAsyncData";

const inputClass = "mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm focus:border-teal-500";
const labelClass = "block text-sm font-medium text-ink";

function EmergencyContactCard() {
  const { data: profile, refetch } = useAsyncData(() => patientApi.getMe(), []);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function startEditing() {
    setName(profile?.emergency_contact_name ?? "");
    setPhone(profile?.emergency_contact_phone ?? "");
    setIsEditing(true);
    setSuccess(false);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSaving(true);
    try {
      await patientApi.updateMe({ emergency_contact_name: name, emergency_contact_phone: phone });
      setIsEditing(false);
      setSuccess(true);
      refetch();
    } catch {
      setError("Couldn't save your emergency contact. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card className="mt-6">
      <h2 className="font-display text-sm font-bold text-ink">Emergency contact</h2>
      <p className="mt-1 text-xs text-ink-soft">
        If one of your readings triggers a critical alert, this contact is notified alongside you.
      </p>

      {!isEditing ? (
        <div className="mt-4">
          {profile?.emergency_contact_name ? (
            <div className="text-sm text-ink">
              <p className="font-medium">{profile.emergency_contact_name}</p>
              <p className="text-ink-soft">{profile.emergency_contact_phone}</p>
            </div>
          ) : (
            <p className="text-sm text-ink-soft">No emergency contact on file yet.</p>
          )}
          <button
            type="button"
            onClick={startEditing}
            className="mt-3 rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-sunken"
          >
            {profile?.emergency_contact_name ? "Edit" : "Add emergency contact"}
          </button>
          {success && <p className="mt-2 text-sm text-status-stable">Emergency contact saved.</p>}
        </div>
      ) : (
        <form onSubmit={handleSave} className="mt-4 grid grid-cols-1 gap-4 sm:max-w-sm">
          <div>
            <label className={labelClass}>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Phone number</label>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} className={inputClass} />
          </div>
          {error && <p className="text-sm text-status-critical">{error}</p>}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isSaving}
              className="rounded-lg bg-teal-500 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
            >
              {isSaving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-ink hover:bg-surface-sunken"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </Card>
  );
}

export function SettingsPage() {
  const { user } = useAuth();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess(true);
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Couldn't update password. Please check your current password and try again.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-ink">Settings</h1>
      <p className="mt-1 text-sm text-ink-soft">Your account details and security.</p>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Profile</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 text-sm">
          <div>
            <p className="text-xs uppercase tracking-wide text-ink-soft">Name</p>
            <p className="mt-1 text-ink">{user?.full_name}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-ink-soft">Email</p>
            <p className="mt-1 text-ink">{user?.email}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-ink-soft">Role</p>
            <p className="mt-1 capitalize text-ink">{user?.role}</p>
          </div>
        </div>
      </Card>

      {user?.role === "patient" && <EmergencyContactCard />}

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Change password</h2>
        <form onSubmit={handleSubmit} className="mt-4 grid grid-cols-1 gap-4 sm:max-w-sm">
          <div>
            <label className={labelClass}>Current password</label>
            <input
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>New password</label>
            <input
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className={inputClass}
            />
            <p className="mt-1 text-xs text-ink-soft">At least 8 characters, with a letter and a number.</p>
          </div>
          <div>
            <label className={labelClass}>Confirm new password</label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={inputClass}
            />
          </div>

          {error && <p className="text-sm text-status-critical">{error}</p>}
          {success && <p className="text-sm text-status-stable">Password updated successfully.</p>}

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-teal-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-teal-600 disabled:opacity-60"
            >
              {isSubmitting ? "Updating…" : "Update password"}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
}
