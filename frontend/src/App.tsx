import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { SavedJobsView } from './components/SavedJobsView';
import { KanbanBoard } from './components/KanbanBoard';
import { JobDetailModal } from './components/JobDetailModal';
import { ImportJobModal } from './components/ImportJobModal';
import { SettingsView } from './components/SettingsView';
import { DashboardView } from './components/DashboardView';
import type { Job, KanbanBoardResponse, DashboardSummary } from './types';
import { useTimeSettings } from './timeSettings';

type Tab = 'dashboard' | 'saved' | 'kanban' | 'settings';
const tabFromHash = (): Tab => {
  const value = window.location.hash.slice(1);
  return value === 'dashboard' || value === 'kanban' || value === 'settings' ? value : 'saved';
};

export const App: React.FC = () => {
  const { settings: timeSettings } = useTimeSettings();
  const [currentTab, setCurrentTab] = useState<Tab>(tabFromHash);
  const changeTab = (tab: Tab) => {
    window.location.hash = tab;
    setCurrentTab(tab);
  };
  const [savedJobs, setSavedJobs] = useState<Job[]>([]);
  const [kanbanData, setKanbanData] = useState<KanbanBoardResponse>({
    stages: {},
    total_applications: 0,
  });
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isLoadingJobs, setIsLoadingJobs] = useState<boolean>(true);
  const [isLoadingKanban, setIsLoadingKanban] = useState<boolean>(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState<boolean>(false);
  const [dashboardError, setDashboardError] = useState<boolean>(false);

  useEffect(() => {
    const syncTab = () => setCurrentTab(tabFromHash());
    window.addEventListener('hashchange', syncTab);
    return () => window.removeEventListener('hashchange', syncTab);
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const fetchSavedJobs = async () => {
    try {
      setIsJobsLoading(true);
      const res = await fetch('/api/jobs/saved');
      if (res.ok) {
        const data = await res.json();
        setSavedJobs(data.jobs || []);
      }
    } catch (e) {
      console.error('Failed to fetch saved jobs:', e);
    } finally {
      setIsJobsLoading(false);
    }
  };

  const setIsJobsLoading = (loading: boolean) => setIsLoadingJobs(loading);

  const fetchKanban = async () => {
    try {
      setIsLoadingKanban(true);
      const res = await fetch('/api/pipeline/kanban');
      if (res.ok) {
        const data = await res.json();
        setKanbanData(data);
      }
    } catch (e) {
      console.error('Failed to fetch kanban board:', e);
    } finally {
      setIsLoadingKanban(false);
    }
  };

  const fetchDashboard = async () => {
    setIsLoadingDashboard(true);
    setDashboardError(false);
    try {
      const res = await fetch('/api/pipeline/dashboard');
      if (!res.ok) throw new Error(`Dashboard request failed: ${res.status}`);
      setDashboardData(await res.json());
    } catch (e) {
      console.error('Failed to fetch dashboard:', e);
      setDashboardError(true);
    } finally {
      setIsLoadingDashboard(false);
    }
  };

  useEffect(() => {
    fetchSavedJobs();
    fetchKanban();
  }, []);

  useEffect(() => {
    if (currentTab === 'dashboard') fetchDashboard();
  }, [currentTab, timeSettings.timezone]);

  const handleSelectJob = async (jobId: string) => {
    try {
      setIsLoadingDetail(true);
      setSelectedJob(null);
      const res = await fetch(`/api/jobs/${jobId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedJob(data);
      }
    } catch (e) {
      console.error('Failed to load job details:', e);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleMoveStage = async (applicationId: string, toStage: string, outcome?: string) => {
    try {
      const payload: { to_stage: string; outcome?: string } = { to_stage: toStage };
      if (outcome !== undefined) {
        payload.outcome = outcome;
      }
      const res = await fetch(`/api/pipeline/applications/${applicationId}/stage`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const stageLabel = toStage.replace('_', ' ');
        const outcomeLabel = outcome && outcome !== 'clear' ? ` (${outcome})` : '';
        showToast(`Updated to ${stageLabel}${outcomeLabel}`);
        fetchKanban();
        if (currentTab === 'dashboard') fetchDashboard();
        if (selectedJob && selectedJob.application?.id === applicationId) {
          handleSelectJob(selectedJob.id);
        }
      }
    } catch (e) {
      console.error('Failed to update stage:', e);
      showToast('Failed to update stage');
    }
  };

  const handleStartApplication = async (jobId: string) => {
    try {
      const res = await fetch(`/api/jobs/${jobId}/start-application`, { method: 'POST' });
      if (res.ok) {
        showToast('Application created in pipeline!');
        fetchKanban();
        setCurrentTab('kanban');
      }
    } catch (e) {
      console.error('Failed to start application:', e);
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    try {
      const res = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('Job deleted successfully');
        setSelectedJob(null);
        await fetchSavedJobs();
        await fetchKanban();
        if (currentTab === 'dashboard') await fetchDashboard();
      } else {
        showToast('Failed to delete job');
      }
    } catch (e) {
      console.error('Failed to delete job:', e);
      showToast('Error deleting job');
    }
  };

  const handleJobImported = async () => {
    showToast('Job analyzed and saved successfully!');
    await fetchSavedJobs();
    await fetchKanban();
    changeTab('saved');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-amber-500 selection:text-white">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-amber-600 text-white font-medium text-xs px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2 border border-amber-400/40 animate-bounce">
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Navbar */}
      <Navbar
        currentTab={currentTab}
        onTabChange={changeTab}
        savedCount={savedJobs.length}
        kanbanCount={kanbanData.total_applications}
        onOpenImport={() => setIsImportModalOpen(true)}
      />

      {/* Main Views */}
      <main className="flex-1">
        {currentTab === 'dashboard' ? (
          <DashboardView
            data={dashboardData}
            isLoading={isLoadingDashboard}
            hasError={dashboardError}
            onRetry={fetchDashboard}
            onSelectJob={handleSelectJob}
          />
        ) : currentTab === 'saved' ? (
          <SavedJobsView
            jobs={savedJobs}
            onSelectJob={handleSelectJob}
            onStartApplication={handleStartApplication}
            onOpenImport={() => setIsImportModalOpen(true)}
            isLoading={isLoadingJobs}
          />
        ) : currentTab === 'kanban' ? (
          <KanbanBoard
            stages={kanbanData.stages}
            onSelectJob={handleSelectJob}
            onMoveStage={handleMoveStage}
            isLoading={isLoadingKanban}
          />
        ) : (
          <SettingsView />
        )}
      </main>

      {/* Job Details Modal */}
      {selectedJob && (
        <JobDetailModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          onMoveStage={handleMoveStage}
          onDeleteJob={handleDeleteJob}
          isLoading={isLoadingDetail}
        />
      )}

      {/* Import Job Modal */}
      <ImportJobModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onJobImported={handleJobImported}
      />
    </div>
  );
};

export default App;
