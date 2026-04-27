import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { RequireAuth } from "@/components/RequireAuth";
import { AuthProvider } from "@/lib/auth";
import { queryClient } from "@/lib/queryClient";
import { AuthMethodsPage } from "@/pages/AuthMethodsPage";
import { ConnectionsPage } from "@/pages/ConnectionsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { EndpointsPage } from "@/pages/EndpointsPage";
import { HealthPage } from "@/pages/HealthPage";
import { LoginPage } from "@/pages/LoginPage";
import { SchedulesPage } from "@/pages/SchedulesPage";
import { SettingsPage } from "@/pages/SettingsPage";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequireAuth />}>
              <Route element={<Layout />}>
                <Route index element={<DashboardPage />} />
                <Route path="connections" element={<ConnectionsPage />} />
                <Route path="auth" element={<AuthMethodsPage />} />
                <Route path="endpoints" element={<EndpointsPage />} />
                <Route path="schedules" element={<SchedulesPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="health" element={<HealthPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
