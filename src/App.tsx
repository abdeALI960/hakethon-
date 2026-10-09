import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Header } from './components/Header';
import { EndpointManager } from './components/EndpointManager';
import { IncidentHistoryReport } from './components/IncidentHistoryReport';
import { LiveOverviewDemo } from './components/LiveOverviewDemo';
import { Footer } from './components/Footer';
import { SqliteModal } from './components/Modals/SqliteModal';
import { ChangeTargetModal } from './components/Modals/ChangeTargetModal';
import { AddEndpointModal } from './components/Modals/AddEndpointModal';
import { EmergencyIntakeModal } from './components/Modals/EmergencyIntakeModal';
import { ProfileSettingsModal } from './components/Modals/ProfileSettingsModal';
import { Toast } from './components/Toast';

const DashboardContent: React.FC = () => {
  const { activeTab, backendStatus, dashboardError } = useApp();

  return (
    <div className="flex flex-col min-h-screen bg-surface text-on-surface antialiased">
      <Header />

      <main className="w-full pt-16 bg-surface min-h-[calc(100vh-64px)] flex-1">
        <div className="flex flex-col w-full">
          {backendStatus === 'offline' && (
            <div role="status" aria-live="polite" className="mx-margin-desktop mt-4 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-2 text-sm text-amber-200">
              Backend offline, showing simulated data.
            </div>
          )}
          {backendStatus === 'connected' && dashboardError && (
            <div role="status" aria-live="polite" className="mx-margin-desktop mt-4 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-2 text-sm text-amber-200">
              {dashboardError}
            </div>
          )}
          {/* Subtle ambient glow background elements constrained inside wrapper */}
          <div className="relative w-full px-margin-desktop py-space-xl flex flex-col gap-space-xl overflow-hidden">
            <div className="absolute top-0 right-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none -z-10"></div>
            <div className="absolute bottom-1/3 left-10 w-80 h-80 bg-tertiary/5 rounded-full blur-3xl pointer-events-none -z-10"></div>

            {/* Section 1: Header & Target Website & Endpoint Manager */}
            <EndpointManager />

            {/* Section 2: Active Tab View */}
            {activeTab === 'incident-report' ? (
              <IncidentHistoryReport />
            ) : (
              <LiveOverviewDemo />
            )}
          </div>
        </div>
      </main>

      <Footer />

      {/* Modals & Overlays */}
      <SqliteModal />
      <ChangeTargetModal />
      <AddEndpointModal />
      <EmergencyIntakeModal />
      <ProfileSettingsModal />
      <Toast />
    </div>
  );
};

export default function App() {
  return (
    <AppProvider>
      <DashboardContent />
    </AppProvider>
  );
}
