import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoginPage } from "@/pages/auth/LoginPage";
import { AdminDashboard } from "@/pages/dashboard/AdminDashboard";
import { PatientDashboard } from "@/pages/dashboard/PatientDashboard";
import { PatientsPage } from "@/pages/admin/PatientsPage";
import { PatientRecordsPage } from "@/pages/admin/PatientRecordsPage";
import { AuditLogPage } from "@/pages/admin/AuditLogPage";
import { ModelsPage } from "@/pages/admin/ModelsPage";
import { AlertsPage as AdminAlertsPage } from "@/pages/admin/AlertsPage";
import { VitalsPage } from "@/pages/patient/VitalsPage";
import { MedicationsPage } from "@/pages/patient/MedicationsPage";
import { AssessmentPage } from "@/pages/patient/AssessmentPage";
import { AssistantPage } from "@/pages/patient/AssistantPage";
import { NotificationsPage } from "@/pages/shared/NotificationsPage";
import { SettingsPage } from "@/pages/shared/SettingsPage";
import { ProgressPage } from "@/pages/patient/ProgressPage";
import { LandingPage } from "@/pages/LandingPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { UnauthorizedPage } from "@/pages/UnauthorizedPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<Navigate to="/login" replace />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />

      {/* --- Admin: manages the technical side (patients, datasets, ML models) --- */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<AdminDashboard />} />
        <Route path="patients" element={<PatientsPage />} />
        <Route path="patients/:patientId" element={<PatientRecordsPage />} />
        <Route path="models" element={<ModelsPage />} />
        <Route path="alerts" element={<AdminAlertsPage />} />
        <Route path="audit" element={<AuditLogPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* --- Patient --- */}
      <Route
        path="/patient"
        element={
          <ProtectedRoute allowedRoles={["patient"]}>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PatientDashboard />} />
        <Route path="vitals" element={<VitalsPage />} />
        <Route path="progress" element={<ProgressPage />} />
        <Route path="assessment" element={<AssessmentPage />} />
        <Route path="medications" element={<MedicationsPage />} />
        <Route path="assistant" element={<AssistantPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
