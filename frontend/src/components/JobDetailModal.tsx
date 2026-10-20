import React, { useState, useMemo, useEffect, useCallback } from 'react';
import {
  X,
  Building2,
  MapPin,
  DollarSign,
  ExternalLink,
  Sparkles,
  UserCheck,
  Clock,
  FileText,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Target,
  Mail,
  RefreshCw,
  Download,
  Copy,
  Check,
  FileCheck,
  ShieldAlert,
  UserPlus,
  Briefcase,
} from 'lucide-react';
import type { Job, JobAnalysisResult, JobDocumentsInfo, CompanyReconData } from '../types';
import { getJobIdentifierItems } from '../jobIdentifiers';
import { useTimeSettings } from '../timeSettings';
import { formatDate, formatDateTime, hasUnknownTimeZone } from '../time';
import { NextActionPanel } from './NextActionPanel';

interface JobDetailModalProps {
  job: Job | null;
  onClose: () => void;
  onDeleteJob?: (jobId: string) => void;
  isLoading: boolean;
  onCadenceUpdate?: (updated: Job) => void;
}



export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  job,
  onClose,
  onDeleteJob,
  isLoading,
  onCadenceUpdate,
}) => {
  const { settings } = useTimeSettings();
  const [activeTab, setActiveTab] = useState<'jd' | 'recon' | 'contacts' | 'resume' | 'cover_letter' | 'timeline'>('jd');
  const [deleteEventId, setDeleteEventId] = useState<string | null>(null);
  const [timelineBusy, setTimelineBusy] = useState(false);
  const [timelineNotice, setTimelineNotice] = useState('');
  const [timelineError, setTimelineError] = useState('');
  const [undoEventId, setUndoEventId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false);
  const [copiedJobIdentifier, setCopiedJobIdentifier] = useState<string | null>(null);

  const [currentJob, setCurrentJob] = useState<Job | null>(job);
  async function correctTimeline(eventId: string, restore = false) {
    if (!currentJob?.application || timelineBusy) return;
    setTimelineBusy(true);
    setTimelineError('');
    try {
      const base = `/api/pipeline/applications/${encodeURIComponent(currentJob.application.id)}/timeline/${encodeURIComponent(eventId)}`;
      const response = await fetch(restore ? `${base}/restore` : base, { method: restore ? 'POST' : 'DELETE' });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not update timeline.');
      setDeleteEventId(null);
      setUndoEventId(restore ? null : eventId);
      setTimelineNotice(result.message);
      const updatedResponse = await fetch(`/api/jobs/${encodeURIComponent(currentJob.id)}`);
      if (!updatedResponse.ok) throw new Error('Change saved. Reopen this job to refresh the timeline.');
      const updated = await updatedResponse.json() as Job;
      setCurrentJob(updated);
      onCadenceUpdate?.(updated);
    } catch (err) {
      setTimelineError(err instanceof Error ? err.message : 'Could not update timeline.');
    } finally { setTimelineBusy(false); }
  }

  const [isRematching, setIsRematching] = useState<boolean>(false);

  useEffect(() => {
    setDeleteEventId(null);
    setTimelineNotice('');
    setTimelineError('');
    setUndoEventId(null);
  }, [job?.id]);

  useEffect(() => {
    setCurrentJob(job);
  }, [job]);

  const activeJob = currentJob || job;

  const handleRematch = async () => {
    if (!activeJob?.id) return;
    setIsRematching(true);
    try {
      const res = await fetch(`/api/jobs/${activeJob.id}/rematch`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to rematch job');
      }
      const data = await res.json();
      if (data.job) {
        setCurrentJob(data.job);
      }
    } catch (err: any) {
      console.error('Rematch error:', err);
      alert(`Rematch failed: ${err.message}`);
    } finally {
      setIsRematching(false);
    }
  };

  // Document states
  const [documentsInfo, setDocumentsInfo] = useState<JobDocumentsInfo | null>(null);
  const [isLoadingDocs, setIsLoadingDocs] = useState<boolean>(false);
  const [selectedResumeVersion, setSelectedResumeVersion] = useState<string>('');
  const [selectedCoverLetterVersion, setSelectedCoverLetterVersion] = useState<string>('');
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [copiedPrompt, setCopiedPrompt] = useState<boolean>(false);
  const [isTailoring, setIsTailoring] = useState<boolean>(false);

  const fetchDocuments = useCallback(async (jobId: string) => {
    setIsLoadingDocs(true);
    try {
      const res = await fetch(`/api/jobs/${jobId}/documents`);
      if (res.ok) {
        const data: JobDocumentsInfo = await res.json();
        setDocumentsInfo(data);
        if (data.resume?.latest_version) {
          setSelectedResumeVersion(data.resume.latest_version);
        }
        if (data.cover_letter?.latest_version) {
          setSelectedCoverLetterVersion(data.cover_letter.latest_version);
        }
      }
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    if (job?.id) {
      fetchDocuments(job.id);
    }
  }, [job?.id, fetchDocuments]);

  const handleRefreshDocs = () => {
    if (job?.id) {
      setRefreshKey((prev) => prev + 1);
      fetchDocuments(job.id);
    }
  };

  const handleTailorDocs = async (type: 'resume' | 'cover_letter') => {
    if (!job?.id) return;
    setIsTailoring(true);
    try {
      const apiType = type === 'cover_letter' ? 'cover-letter' : 'resume';
      const res = await fetch(`/api/jobs/${job.id}/tailor/${apiType}`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to tailor ${apiType}`);
      }
      const data = await res.json();
      if (data.documents_info) {
        setDocumentsInfo(data.documents_info);
      } else {
        await fetchDocuments(job.id);
      }
      setRefreshKey((prev) => prev + 1);
    } catch (err: any) {
      console.error('Tailor documents error:', err);
      alert(`Tailoring failed: ${err.message}`);
    } finally {
      setIsTailoring(false);
    }
  };

  const parsedAnalysis: JobAnalysisResult | null = useMemo(() => {
    if (!activeJob?.analysis_json) return null;
    try {
      return JSON.parse(activeJob.analysis_json) as JobAnalysisResult;
    } catch (e) {
      console.error('Failed to parse analysis_json:', e);
      return null;
    }
  }, [activeJob?.analysis_json]);

  const parsedRecon: CompanyReconData | null = useMemo(() => {
    if (activeJob?.company_recon) return activeJob.company_recon;
    if (!activeJob?.company_recon_json) return null;
    try {
      return JSON.parse(activeJob.company_recon_json) as CompanyReconData;
    } catch (e) {
      console.error('Failed to parse company_recon_json:', e);
      return null;
    }
  }, [activeJob?.company_recon, activeJob?.company_recon_json]);

  const [isSubmittingRecon, setIsReconning] = useState<boolean>(false);
  const reconPending = activeJob?.company_recon_status === 'pending' || activeJob?.company_recon_status === 'running';
  const isReconning = isSubmittingRecon || reconPending;

  useEffect(() => {
    if (!activeJob?.id || !reconPending) return;
    const jobId = activeJob.id;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
        if (response.ok) {
          const updated = await response.json() as Job;
          if (cancelled) return;
          setCurrentJob(updated);
          if (updated.company_recon_status !== 'pending' && updated.company_recon_status !== 'running') return;
        }
      } catch { /* Keep the saved job visible while a refresh is unavailable. */ }
      if (!cancelled) timer = setTimeout(refresh, 2000);
    };
    timer = setTimeout(refresh, 2000);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [activeJob?.id, reconPending]);

  const handleRunRecon = async () => {
    if (!activeJob?.id || isReconning) return;
    setIsReconning(true);
    try {
      const res = await fetch(`/api/jobs/${activeJob.id}/recon`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to run company recon');
      }
      const data = await res.json();
      if (data.job) {
        setCurrentJob(data.job);
      }
    } catch (err: any) {
      console.error('Recon error:', err);
      alert(`Company Recon failed: ${err.message}`);
    } finally {
      setIsReconning(false);
    }
  };

  // Outreach and Contacts state
  const [generatingOutreach, setGeneratingOutreach] = useState<Record<string, boolean>>({});
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [showAddContact, setShowAddContact] = useState<boolean>(false);
  const [isAddingContact, setIsAddingContact] = useState<boolean>(false);
  const [newContact, setNewContact] = useState({
    name: '',
    role_title: '',
    contact_type: 'hiring_manager',
    linkedin_url: '',
    email: '',
    notes: '',
  });

  const handleGenerateOutreach = async (contactId: string) => {
    if (!activeJob?.id) return;
    setGeneratingOutreach((prev) => ({ ...prev, [contactId]: true }));
    try {
      const res = await fetch(`/api/jobs/${activeJob.id}/contacts/${contactId}/generate-outreach`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to generate outreach');
      }
      const data = await res.json();
      if (data.contact && activeJob) {
        setCurrentJob((prev) => {
          if (!prev) return null;
          const updatedContacts = (prev.contacts || []).map((c) =>
            c.id === contactId ? { ...c, messages: data.messages } : c
          );
          return { ...prev, contacts: updatedContacts };
        });
      }
    } catch (err: any) {
      console.error('Generate outreach error:', err);
      alert(`Outreach generation failed: ${err.message}`);
    } finally {
      setGeneratingOutreach((prev) => ({ ...prev, [contactId]: false }));
    }
  };

  const handleCopyMessage = (msgId: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(msgId);
    setTimeout(() => setCopiedMsgId(null), 2500);
  };

  const handleUpdateMessageStatus = async (messageId: string, status: string) => {
    try {
      const res = await fetch(`/api/jobs/messages/${messageId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      if (res.ok) {
        setCurrentJob((prev) => {
          if (!prev) return null;
          const updatedContacts = (prev.contacts || []).map((c) => ({
            ...c,
            messages: (c.messages || []).map((m) =>
              m.id === messageId ? { ...m, status, sent_at: status === 'sent' ? new Date().toISOString() : m.sent_at } : m
            )
          }));
          return { ...prev, contacts: updatedContacts };
        });
      }
    } catch (err) {
      console.error('Update message status error:', err);
    }
  };

  const handleAddContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeJob?.id || !newContact.name || !newContact.role_title) return;
    setIsAddingContact(true);
    try {
      const res = await fetch(`/api/jobs/${activeJob.id}/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newContact)
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to add contact');
      }
      const added = await res.json();
      setCurrentJob((prev) => {
        if (!prev) return null;
        return { ...prev, contacts: [...(prev.contacts || []), { ...added, messages: [] }] };
      });
      setShowAddContact(false);
      setNewContact({ name: '', role_title: '', contact_type: 'hiring_manager', linkedin_url: '', email: '', notes: '' });
    } catch (err: any) {
      console.error('Add contact error:', err);
      alert(`Add contact failed: ${err.message}`);
    } finally {
      setIsAddingContact(false);
    }
  };

  const [copiedAgentCmd, setCopiedAgentCmd] = useState<boolean>(false);

  const handleCopyAgentCommand = () => {
    if (!activeJob?.id) return;
    const cmd = `scout gatekeepers for job ${activeJob.id} (${activeJob.company} - ${activeJob.title})`;
    navigator.clipboard.writeText(cmd);
    setCopiedAgentCmd(true);
    setTimeout(() => setCopiedAgentCmd(false), 2500);
  };

  const handleCopyJobIdentifier = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedJobIdentifier(value);
      setTimeout(() => setCopiedJobIdentifier(null), 2500);
    } catch (err) {
      console.error('Failed to copy job identifier:', err);
    }
  };

  const handleDeleteContact = async (contactId: string) => {
    if (!confirm('Are you sure you want to delete this gatekeeper and all their outreach drafts?')) return;
    try {
      const res = await fetch(`/api/jobs/contacts/${contactId}`, { method: 'DELETE' });
      if (res.ok) {
        setCurrentJob((prev) => {
          if (!prev) return null;
          return { ...prev, contacts: (prev.contacts || []).filter((c) => c.id !== contactId) };
        });
      }
    } catch (err) {
      console.error('Delete contact error:', err);
    }
  };

  const renderDocumentPreview = (type: 'resume' | 'cover_letter') => {
    if (!job) return null;
    const docInfo = type === 'resume' ? documentsInfo?.resume : documentsInfo?.cover_letter;
    const selectedVersion = type === 'resume' ? selectedResumeVersion : selectedCoverLetterVersion;
    const setSelectedVersion = type === 'resume' ? setSelectedResumeVersion : setSelectedCoverLetterVersion;
    const docTitle = type === 'resume' ? 'Resume' : 'Cover Letter';
    const apiDocType = type === 'resume' ? 'resume' : 'cover-letter';

    const activeVersionData = docInfo?.versions.find((v) => v.version === selectedVersion) || docInfo?.versions[0];
    const previewUrl = `/api/jobs/${job.id}/documents/${apiDocType}?version=${encodeURIComponent(selectedVersion || '')}&t=${refreshKey}`;
    const downloadUrl = `/api/jobs/${job.id}/documents/${apiDocType}?version=${encodeURIComponent(selectedVersion || '')}&download=true`;
    const downloadFileName = activeVersionData?.download_filename || docInfo?.download_filename || `${docTitle}.pdf`;

    if (!docInfo?.available) {
      const agentChatPrompt = `Tailor only the ${docTitle.toLowerCase()} for ${job.title} at ${job.company} (Job ID: ${job.id})`;
      return (
        <div className="flex flex-col items-center justify-center py-12 px-6 bg-ui-page/40 border border-dashed border-ui-line-soft rounded-2xl text-center">
          <div className="p-3.5 bg-ui-raised/80 rounded-2xl text-ui-muted mb-3 border border-ui-line">
            {type === 'resume' ? <FileText className="h-8 w-8 text-ui-ink-amber-500/80" /> : <Mail className="h-8 w-8 text-ui-ink-amber-500/80" />}
          </div>
          <h3 className="text-base font-semibold text-ui-heading mb-1">
            No {docTitle} Generated Yet
          </h3>
          <p className="text-xs text-ui-muted max-w-md mb-4 leading-relaxed">
            Create this document with DoorKnock's Typst engine, or ask your AI Agent to draft it in chat.
          </p>

          {/* Workflow Awareness: Company Recon Status */}
          {parsedRecon ? (
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-ui-fill-emerald-950/40 border border-ui-line-emerald-800/50 text-ui-ink-emerald-300 text-xs mb-4 max-w-lg w-full text-left">
              <Sparkles className="h-4 w-4 text-ui-ink-emerald-400 shrink-0" />
              <span className="text-[0.6875rem] leading-relaxed">
                <strong>Recon Active:</strong> Tailoring will automatically align with {parsedRecon.department_intel?.team_name || 'department'} frictions and business model hooks.
              </span>
            </div>
          ) : (
            <div className="flex items-center justify-between gap-3 px-3.5 py-2 rounded-xl bg-ui-fill-amber-950/30 border border-ui-line-amber-800/40 text-ui-ink-amber-200 text-xs mb-4 max-w-lg w-full text-left">
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-ui-ink-amber-400 shrink-0" />
                <span className="text-[0.6875rem] text-ui-ink-amber-200/90 leading-relaxed">
                  Tip: Run <strong>Company Recon</strong> first to feed strategic business model & department hooks into your documents.
                </span>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('recon')}
                className="text-[0.6875rem] font-semibold text-ui-ink-amber-400 hover:text-ui-ink-amber-300 underline shrink-0 cursor-pointer"
              >
                Go to Recon
              </button>
            </div>
          )}

          <button
            onClick={() => handleTailorDocs(type)}
            disabled={isTailoring}
            className="flex items-center gap-2 px-5 py-2.5 text-xs font-bold bg-ui-fill-amber-600 hover:bg-ui-fill-amber-500 text-ui-on-action rounded-xl shadow-lg shadow-amber-950/50 transition mb-4 disabled:opacity-50 cursor-pointer"
          >
            <Sparkles className={`h-4 w-4 ${isTailoring ? 'animate-spin text-ui-on-action-icon' : 'text-ui-on-action-icon'}`} />
            <span>{isTailoring ? 'Tailoring with Typst...' : `✨ Tailor ${docTitle} Now`}</span>
          </button>

          {/* AI Prompt Box: Option 1 (Chat with Agent) */}
          <div className="w-full max-w-lg bg-ui-panel border border-ui-line-soft rounded-xl p-3 text-left mb-4 shadow-inner">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[0.6875rem] font-semibold text-ui-muted uppercase tracking-wider">
                Ask Agent in Chat (Option 1)
              </span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(agentChatPrompt);
                  setCopiedPrompt(true);
                  setTimeout(() => setCopiedPrompt(false), 2000);
                }}
                className="flex items-center gap-1 text-xs text-ui-ink-amber-400 hover:text-ui-ink-amber-300 transition cursor-pointer"
              >
                {copiedPrompt ? <Check className="h-3.5 w-3.5 text-ui-ink-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copiedPrompt ? 'Copied' : 'Copy Prompt'}</span>
              </button>
            </div>
            <p className="text-xs text-ui-secondary bg-ui-page p-2.5 rounded border border-ui-line-soft/80 select-all leading-relaxed font-sans">
              {agentChatPrompt}
            </p>
          </div>

          <button
            onClick={handleRefreshDocs}
            disabled={isLoadingDocs || isTailoring}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-ui-raised hover:bg-ui-hover text-ui-heading rounded-xl border border-ui-line transition shadow cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoadingDocs ? 'animate-spin text-ui-ink-amber-400' : ''}`} />
            <span>Check for Generated PDF</span>
          </button>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* Document Header Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-ui-page/80 border border-ui-line-soft rounded-xl">
          <div className="flex items-center gap-3">
            <label className="text-xs text-ui-muted font-medium">Version:</label>
            <select
              value={selectedVersion}
              onChange={(e) => setSelectedVersion(e.target.value)}
              className="bg-ui-raised border border-ui-line text-ui-secondary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-ui-line-amber-500 font-mono font-medium"
            >
              {docInfo.versions.map((v) => (
                <option key={v.version} value={v.version}>
                  {v.version} {v.version === docInfo.latest_version ? '(Latest)' : ''}
                </option>
              ))}
            </select>

            {activeVersionData && (
              <span className="text-[0.6875rem] text-ui-muted hidden sm:inline font-mono">
                {(activeVersionData.size_bytes / 1024).toFixed(1)} KB • {activeVersionData.download_filename || activeVersionData.filename}
              </span>
            )}

            {parsedRecon ? (
              <span className="hidden lg:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[0.625rem] font-medium bg-ui-fill-emerald-950/80 text-ui-ink-emerald-300 border border-ui-line-emerald-800/60" title="Tailored using Company Recon business model and department hooks">
                <Sparkles className="h-3 w-3 text-ui-ink-emerald-400" />
                <span>Recon Intel Synced</span>
              </span>
            ) : (
              <button
                type="button"
                onClick={() => setActiveTab('recon')}
                className="hidden lg:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[0.625rem] font-medium bg-ui-fill-amber-950/40 text-ui-ink-amber-300/80 border border-ui-line-amber-900/60 hover:text-ui-ink-amber-200 hover:border-ui-line-amber-700 transition cursor-pointer"
                title="Run Company Recon to unlock deeper business model hooks"
              >
                <Building2 className="h-3 w-3 text-ui-ink-amber-400" />
                <span>Run Recon for Deep Hooks</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleTailorDocs(type)}
              disabled={isTailoring}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-ui-raised hover:bg-ui-hover text-ui-ink-amber-300 font-medium rounded-lg transition border border-ui-line-amber-900/40 disabled:opacity-50 cursor-pointer"
              title={`Re-tailor ${docTitle} with Typst`}
            >
              <Sparkles className={`h-3.5 w-3.5 ${isTailoring ? 'animate-spin' : ''}`} />
              <span>{isTailoring ? 'Tailoring...' : `Re-tailor ${docTitle}`}</span>
            </button>

            <button
              onClick={handleRefreshDocs}
              disabled={isLoadingDocs || isTailoring}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-ui-raised hover:bg-ui-hover text-ui-secondary rounded-lg transition border border-ui-line"
              title="Refresh document status"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoadingDocs ? 'animate-spin text-ui-ink-amber-400' : ''}`} />
              <span>Refresh</span>
            </button>

            <a
              href={previewUrl}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-ui-raised hover:bg-ui-hover text-ui-secondary rounded-lg transition border border-ui-line"
              title="Open full PDF in new tab"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>Open Tab</span>
            </a>

            <a
              href={downloadUrl}
              download={downloadFileName}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-ui-fill-amber-600 hover:bg-ui-fill-amber-500 text-ui-on-action font-medium rounded-lg transition shadow shadow-amber-950/40"
              title={`Download as ${downloadFileName}`}
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download PDF</span>
            </a>
          </div>
        </div>

        {/* Embedded PDF iframe */}
        <div className="relative w-full h-[66vh] rounded-xl overflow-hidden border border-ui-line-soft bg-ui-page shadow-2xl flex flex-col">
          <iframe
            src={previewUrl}
            className="w-full h-full border-0 bg-ui-panel"
            title={`${docTitle} Preview`}
          />
        </div>
      </div>
    );
  };

  if (!job && !isLoading) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ui-overlay/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-ui-panel border border-ui-line rounded-2xl w-full max-w-6xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-ui-line-soft bg-ui-page/80 flex items-start justify-between gap-4">
          {isLoading || !job ? (
            <div className="animate-pulse space-y-2 w-full">
              <div className="h-6 bg-ui-raised rounded w-1/3"></div>
              <div className="h-4 bg-ui-raised rounded w-1/4"></div>
            </div>
          ) : (
            <div className="w-full">
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-ui-body flex items-center gap-1.5">
                    <Building2 className="h-4 w-4 text-ui-ink-amber-500" />
                    {job.company}
                  </span>
                  {(() => {
                    const decision = parsedAnalysis?.triage?.decision || (
                      activeJob?.suitability_score !== undefined && activeJob?.suitability_score !== null
                        ? (activeJob.suitability_score >= 90 ? 'STRONG_KNOCK' : activeJob.suitability_score >= 75 ? 'SELECTIVE_APPLY' : activeJob.suitability_score >= 60 ? 'HIGH_RISK_LOW_ROI' : 'HARD_PASS')
                        : null
                    );
                    if (!decision) return null;
                    const config = {
                      STRONG_KNOCK: { label: 'STRONG KNOCK', icon: '🎯', style: 'bg-ui-fill-emerald-950/80 text-ui-ink-emerald-400 border-ui-line-emerald-700/70' },
                      SELECTIVE_APPLY: { label: 'SELECTIVE APPLY', icon: '⚡', style: 'bg-ui-fill-amber-950/80 text-ui-ink-amber-400 border-ui-line-amber-700/70' },
                      HIGH_RISK_LOW_ROI: { label: 'HIGH RISK', icon: '⚠️', style: 'bg-ui-fill-rose-950/80 text-ui-ink-rose-400 border-ui-line-rose-800/70' },
                      HARD_PASS: { label: 'HARD PASS', icon: '⛔', style: 'bg-ui-panel text-ui-muted border-ui-line' },
                      DO_NOT_APPLY: { label: 'HARD PASS', icon: '⛔', style: 'bg-ui-panel text-ui-muted border-ui-line' },
                    }[decision] || { label: decision.replace(/_/g, ' '), icon: '📋', style: 'bg-ui-raised text-ui-body border-ui-line' };

                    return (
                      <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border flex items-center gap-1.5 shadow-sm ${config.style}`}>
                        <span>{config.icon}</span>
                        <span>{config.label}</span>
                      </span>
                    );
                  })()}
                </div>

                {job.application && <span className="text-xs text-ui-body">Stage: {job.application.current_stage === 'knocked' ? 'Contacted' : job.application.current_stage.replaceAll('_', ' ')}</span>}

              </div>

              <h2 className="text-xl font-bold text-ui-heading">{job.title}</h2>

              <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-ui-muted">
                {job.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3 text-ui-subtle" />
                    {job.location}
                  </span>
                )}
                {job.workplace_type && (
                  <span className="capitalize bg-ui-raised px-2 py-0.5 rounded">
                    {job.workplace_type}
                  </span>
                )}
                {job.salary_min && (
                  <span className="text-ui-ink-amber-400 flex items-center gap-1 font-medium">
                    <DollarSign className="h-3 w-3" />
                    ${job.salary_min.toLocaleString()}
                    {job.salary_max ? ` - $${job.salary_max.toLocaleString()}` : ''}/{job.salary_interval || 'yr'}
                  </span>
                )}
                {job.job_url && (
                  <a
                    href={job.job_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-ui-secondary hover:text-ui-heading bg-ui-raised/90 hover:bg-ui-hover border border-ui-line/80 hover:border-ui-line-amber-500/50 rounded-lg transition-all shadow-sm group"
                    title="Open original job posting"
                  >
                    <span>Original Posting</span>
                    <ExternalLink className="h-3 w-3 text-ui-muted group-hover:text-ui-ink-amber-400 transition-colors" />
                  </a>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-[0.6875rem] text-ui-subtle">
                {getJobIdentifierItems(job).map(({ label, value }) => {
                  const isCopied = copiedJobIdentifier === value;

                  return (
                    <span key={label} className="inline-flex items-center gap-1.5">
                      <span className="font-medium text-ui-muted">{label}:</span>
                      <code className="font-mono text-ui-body select-text">{value}</code>
                      <button
                        type="button"
                        onClick={() => handleCopyJobIdentifier(value)}
                        className="inline-flex items-center rounded p-0.5 text-ui-subtle hover:bg-ui-raised hover:text-ui-ink-amber-300 transition"
                        title={`Copy ${label}`}
                        aria-label={`Copy ${label}`}
                      >
                        {isCopied ? <Check className="h-3 w-3 text-ui-ink-emerald-400" /> : <Copy className="h-3 w-3" />}
                      </button>
                      {isCopied && <span className="text-ui-ink-emerald-400">Copied</span>}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          <button
            onClick={onClose}
            className="text-ui-muted hover:text-ui-heading p-1.5 rounded-lg hover:bg-ui-raised transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Tabs - Modern Segmented Control (Zero Horizontal Scroll) */}
        <div className="px-6 py-2.5 border-b border-ui-line-soft bg-ui-page/70 shrink-0">
          <nav className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1 p-1 bg-ui-panel/90 border border-ui-line-soft/90 rounded-xl" aria-label="Job details tabs">
            {/* 1. Job Brief */}
            <button
              type="button"
              onClick={() => setActiveTab('jd')}
              title="Tactical Match Brief & Job Description"
              className={`flex min-w-0 flex-wrap items-center justify-center gap-1.5 py-2 px-1.5 text-[0.6875rem] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'jd'
                  ? 'bg-ui-fill-amber-500/15 text-ui-ink-amber-300 border border-ui-line-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-raised/60 border border-transparent'
              }`}
            >
              <FileText className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'jd' ? 'text-ui-ink-amber-400' : 'text-ui-muted'}`} />
              <span className="whitespace-nowrap">Job Brief</span>
            </button>

            {/* 2. Company & Team Recon */}
            <button
              type="button"
              onClick={() => setActiveTab('recon')}
              title="Company Business Model & Team Intelligence Recon"
              className={`flex min-w-0 flex-wrap items-center justify-center gap-1.5 py-2 px-1.5 text-[0.6875rem] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'recon'
                  ? 'bg-ui-fill-amber-500/15 text-ui-ink-amber-300 border border-ui-line-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-raised/60 border border-transparent'
              }`}
            >
              <Building2 className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'recon' ? 'text-ui-ink-amber-400' : 'text-ui-muted'}`} />
              <span className="whitespace-nowrap">Company Recon</span>
              {parsedRecon && !isReconning && activeJob?.company_recon_status !== 'failed' ? (
                <span className="px-1 py-0.5 rounded text-[0.5625rem] font-mono font-bold bg-ui-fill-emerald-950 text-ui-ink-emerald-400 border border-ui-line-emerald-800/80 shrink-0">
                  Active
                </span>
              ) : (
                <span className="px-1 py-0.5 rounded text-[0.5625rem] font-mono bg-ui-raised text-ui-subtle border border-ui-line/60 shrink-0">
                  {isReconning ? 'Running' : activeJob?.company_recon_status === 'failed' ? 'Retry' : 'Ready'}
                </span>
              )}
            </button>

            {/* 3. Gatekeeper & Outreach */}
            <button
              type="button"
              onClick={() => setActiveTab('contacts')}
              title="Gatekeeper Recon & Cold Outreach Launchpad"
              className={`flex min-w-0 flex-wrap items-center justify-center gap-1.5 py-2 px-1.5 text-[0.6875rem] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'contacts'
                  ? 'bg-ui-fill-amber-500/15 text-ui-ink-amber-300 border border-ui-line-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-raised/60 border border-transparent'
              }`}
            >
              <UserCheck className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'contacts' ? 'text-ui-ink-blue-400' : 'text-ui-muted'}`} />
              <span className="whitespace-nowrap">Gatekeepers</span>
              <span className="px-1.5 py-0.5 rounded-full text-[0.5625rem] font-mono font-bold bg-ui-raised text-ui-body border border-ui-line shrink-0">
                {activeJob?.contacts?.length || 0}
              </span>
            </button>

            {/* 4. Tailored Resume */}
            <button
              type="button"
              onClick={() => setActiveTab('resume')}
              title="Typst Tailored ATS Resume"
              className={`flex min-w-0 flex-wrap items-center justify-center gap-1.5 py-2 px-1.5 text-[0.6875rem] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'resume'
                  ? 'bg-ui-fill-amber-500/15 text-ui-ink-amber-300 border border-ui-line-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-raised/60 border border-transparent'
              }`}
            >
              <FileCheck className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'resume' ? 'text-ui-ink-emerald-400' : 'text-ui-muted'}`} />
              <span className="whitespace-nowrap">Resume</span>
              {documentsInfo?.resume?.available ? (
                <span className="px-1 py-0.5 rounded text-[0.5625rem] font-mono font-bold bg-ui-fill-emerald-950 text-ui-ink-emerald-400 border border-ui-line-emerald-800/80 shrink-0">
                  {documentsInfo.resume.latest_version}
                </span>
              ) : (
                <span className="px-1 py-0.5 rounded text-[0.5625rem] font-mono bg-ui-raised/80 text-ui-subtle border border-ui-line/50 shrink-0">
                  None
                </span>
              )}
            </button>

            {/* 5. Tailored Cover Letter */}
            <button
              type="button"
              onClick={() => setActiveTab('cover_letter')}
              title="Sepia De-AI Problem-First Cover Letter"
              className={`flex min-w-0 flex-wrap items-center justify-center gap-1.5 py-2 px-1.5 text-[0.6875rem] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'cover_letter'
                  ? 'bg-ui-fill-amber-500/15 text-ui-ink-amber-300 border border-ui-line-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-raised/60 border border-transparent'
              }`}
            >
              <Mail className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'cover_letter' ? 'text-ui-ink-indigo-400' : 'text-ui-muted'}`} />
              <span className="whitespace-nowrap">Cover Letter</span>
              {documentsInfo?.cover_letter?.available ? (
                <span className="px-1 py-0.5 rounded text-[0.5625rem] font-mono font-bold bg-ui-fill-emerald-950 text-ui-ink-emerald-400 border border-ui-line-emerald-800/80 shrink-0">
                  {documentsInfo.cover_letter.latest_version}
                </span>
              ) : (
                <span className="px-1 py-0.5 rounded text-[0.5625rem] font-mono bg-ui-raised/80 text-ui-subtle border border-ui-line/50 shrink-0">
                  None
                </span>
              )}
            </button>

            {/* 6. Timeline Events */}
            <button
              type="button"
              onClick={() => setActiveTab('timeline')}
              title="Application Stage Event History"
              className={`flex min-w-0 flex-wrap items-center justify-center gap-1.5 py-2 px-1.5 text-[0.6875rem] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'timeline'
                  ? 'bg-ui-fill-amber-500/15 text-ui-ink-amber-300 border border-ui-line-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-raised/60 border border-transparent'
              }`}
            >
              <Clock className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'timeline' ? 'text-ui-ink-amber-400' : 'text-ui-muted'}`} />
              <span className="whitespace-nowrap">Timeline</span>
              <span className="px-1.5 py-0.5 rounded-full text-[0.5625rem] font-mono font-bold bg-ui-raised text-ui-body border border-ui-line shrink-0">
                {activeJob?.timeline?.length || 0}
              </span>
            </button>
          </nav>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {(activeTab === 'jd' || activeTab === 'timeline') && activeJob && <NextActionPanel key={activeJob.id} action={activeJob.next_action || {
            application_id: activeJob.application?.id || '', job_id: activeJob.id,
            title: activeJob.title, company: activeJob.company, kind: 'closed',
            label: 'Record application progress', date: null, due_date: null, state: 'closed',
            reason: 'Confirm a real event to update your application history.', basis: 'Saved job', followup_count: 0,
          }} currentStage={activeJob.application?.current_stage || 'saved'} onRecorded={async () => {
            const response = await fetch(`/api/jobs/${activeJob.id}`);
            if (!response.ok) throw new Error('Event saved. Refresh the job to load the updated timeline.');
            const updated: Job = await response.json();
            setCurrentJob(updated);
            onCadenceUpdate?.(updated);
          }} />}
          {isLoading || !job ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ui-line-amber-500"></div>
            </div>
          ) : activeTab === 'jd' ? (
            <div className="space-y-6">
              {(activeJob?.suitability_reason || parsedAnalysis) && (
                <div className="bg-ui-fill-amber-950/20 border border-ui-line-amber-800/40 rounded-xl p-5 space-y-4 shadow-lg">
                  <div className="flex items-center justify-between border-b border-ui-line-amber-900/40 pb-3">
                    <h4 className="text-xs font-bold text-ui-ink-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Sparkles className="h-4 w-4" />
                      Tactical Match Brief
                    </h4>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleRematch}
                        disabled={isRematching}
                        className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-ui-panel hover:bg-ui-raised text-ui-ink-amber-300 font-medium rounded-lg transition border border-ui-line-amber-800/40 disabled:opacity-50 cursor-pointer shadow-sm"
                        title="Re-run Match Analysis with V2 Tactical Brief"
                      >
                        <RefreshCw className={`h-3 w-3 ${isRematching ? 'animate-spin text-ui-ink-amber-400' : ''}`} />
                        <span>{isRematching ? 'Re-matching...' : 'Rematch Analysis'}</span>
                      </button>
                      {parsedAnalysis?.triage ? (
                        <span className={`text-xs font-bold px-2.5 py-1 rounded-full border flex items-center gap-1.5 ${
                          parsedAnalysis.triage.decision === 'STRONG_KNOCK'
                            ? 'bg-ui-fill-emerald-950/80 text-ui-ink-emerald-400 border-ui-line-emerald-700/70'
                            : parsedAnalysis.triage.decision === 'SELECTIVE_APPLY'
                            ? 'bg-ui-fill-amber-950/80 text-ui-ink-amber-400 border-ui-line-amber-700/70'
                            : parsedAnalysis.triage.decision === 'HIGH_RISK_LOW_ROI'
                            ? 'bg-ui-fill-rose-950/80 text-ui-ink-rose-400 border-ui-line-rose-800/70'
                            : 'bg-ui-panel text-ui-muted border-ui-line'
                        }`}>
                          <span>{parsedAnalysis.triage.decision === 'STRONG_KNOCK' ? '🎯' : parsedAnalysis.triage.decision === 'SELECTIVE_APPLY' ? '⚡' : parsedAnalysis.triage.decision === 'HIGH_RISK_LOW_ROI' ? '⚠️' : '⛔'}</span>
                          <span>{parsedAnalysis.triage.decision.replace(/_/g, ' ')}</span>
                        </span>
                      ) : activeJob?.suitability_score !== undefined && activeJob?.suitability_score !== null && (
                        <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-ui-panel text-ui-body border border-ui-line flex items-center gap-1.5">
                          <span>{activeJob.suitability_score >= 90 ? '🎯' : activeJob.suitability_score >= 75 ? '⚡' : '⚠️'}</span>
                          <span>{activeJob.suitability_score >= 90 ? 'STRONG KNOCK' : activeJob.suitability_score >= 75 ? 'SELECTIVE APPLY' : 'HIGH RISK'}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {parsedAnalysis?.triage ? (
                    <div className="space-y-3.5">
                      {/* Card 1: Strategic Rationale & Dealbreaker Audit */}
                      <div className="bg-ui-page/70 p-3.5 rounded-xl border border-ui-line-soft/80 space-y-2">
                        <div className="text-xs text-ui-secondary leading-relaxed font-sans">
                          <span className="font-bold text-ui-ink-amber-400">Strategic Rationale: </span>
                          {parsedAnalysis.triage.strategic_thesis}
                        </div>
                        <div className="text-[0.6875rem] text-ui-muted pt-1.5 border-t border-ui-line-soft/80 flex items-center justify-between">
                          <span>Dealbreaker Audit:</span>
                          {(() => {
                            const detected = (parsedAnalysis.triage.dealbreakers_detected || []).filter(
                              (d) => d && d.trim().toLowerCase() !== 'none' && d.trim().toLowerCase() !== 'none detected'
                            );
                            if (detected.length > 0) {
                              return (
                                <span className="text-ui-ink-rose-400 font-semibold flex items-center gap-1">
                                  <span>⚠️</span>
                                  <span>{detected.join(', ')}</span>
                                </span>
                              );
                            }
                            return <span className="text-ui-ink-emerald-400 font-medium">✓ None detected</span>;
                          })()}
                        </div>
                      </div>

                      {/* Card 2: Acute Employer Bottlenecks & Day-1 Antidote */}
                      {parsedAnalysis.employer_mandate && (
                        <div className="bg-ui-page/70 p-3.5 rounded-xl border border-ui-line-soft/80 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[0.6875rem] font-bold text-ui-ink-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                              <Target className="h-3.5 w-3.5 text-ui-ink-amber-500" />
                              Acute Employer Bottlenecks
                            </span>
                            {parsedAnalysis.employer_mandate.role_archetype && (
                              <span className="text-[0.625rem] font-bold px-2 py-0.5 rounded bg-ui-fill-blue-500/20 text-ui-ink-blue-300 border border-ui-line-blue-500/30">
                                Role: {parsedAnalysis.employer_mandate.role_archetype}
                              </span>
                            )}
                          </div>
                          {parsedAnalysis.employer_mandate.acute_operational_frictions?.length > 0 && (
                            <ul className="space-y-1.5">
                              {parsedAnalysis.employer_mandate.acute_operational_frictions.map((pt, i) => (
                                <li key={i} className="text-xs text-ui-body flex items-start gap-2 bg-ui-panel/60 p-2 rounded-md border border-ui-line-soft">
                                  <span className="text-ui-ink-amber-500 font-bold">🔥</span>
                                  <span>{pt}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                          {parsedAnalysis.employer_mandate.immediate_value_hook && (
                            <div className="text-xs text-ui-body bg-ui-fill-amber-950/20 p-2.5 rounded-lg border border-ui-line-amber-900/30">
                              <span className="text-ui-ink-amber-300 font-bold">Day-1 Antidote: </span>
                              {parsedAnalysis.employer_mandate.immediate_value_hook}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Card 3: Gaps & Strategic Defense */}
                      {parsedAnalysis.gaps_and_mitigation && parsedAnalysis.gaps_and_mitigation.length > 0 && (
                        <div className="bg-ui-page/70 p-3.5 rounded-xl border border-ui-line-soft/80 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[0.6875rem] font-bold text-ui-muted uppercase tracking-wider flex items-center gap-1.5">
                              <ShieldAlert className="h-3.5 w-3.5 text-ui-ink-amber-500" />
                              Identified Gaps & Strategic Defense
                            </span>
                            <span className="text-[0.625rem] font-bold px-2 py-0.5 rounded bg-ui-fill-amber-500/10 text-ui-ink-amber-300 border border-ui-line-amber-500/30">
                              Risk Audit
                            </span>
                          </div>
                          <div className="space-y-1.5">
                            {parsedAnalysis.gaps_and_mitigation.map((g, i) => (
                              <div key={i} className="bg-ui-panel/60 p-2.5 rounded-lg border border-ui-line-soft text-xs space-y-1">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-ui-ink-amber-400 flex items-center gap-1">
                                    <span>▲ Gap:</span> <span>{g.gap}</span>
                                  </span>
                                  <span className="text-[0.625rem] px-1.5 py-0.5 rounded bg-ui-page text-ui-muted border border-ui-line-soft">{g.severity}</span>
                                </div>
                                <div className="text-ui-body text-[0.6875rem] bg-ui-page/60 p-2 rounded border border-ui-line-soft/80 leading-relaxed">
                                  <span className="text-ui-ink-emerald-400 font-semibold">🛡️ Defense: </span>
                                  {g.compensating_evidence}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Legacy 3-Dimensional & Checklist View */
                    <div className="space-y-4">
                      {parsedAnalysis && (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div className="bg-ui-page/60 p-3 rounded-lg border border-ui-line-soft text-center">
                            <div className="text-[0.6875rem] text-ui-muted uppercase font-medium">Technical Fit</div>
                            <div className="text-lg font-bold text-ui-ink-emerald-400 mt-0.5">
                              {parsedAnalysis.technical_fit_score ? `${Math.round(parsedAnalysis.technical_fit_score)}%` : 'N/A'}
                            </div>
                          </div>
                          <div className="bg-ui-page/60 p-3 rounded-lg border border-ui-line-soft text-center">
                            <div className="text-[0.6875rem] text-ui-muted uppercase font-medium">Domain Fit</div>
                            <div className="text-lg font-bold text-ui-ink-blue-400 mt-0.5">
                              {parsedAnalysis.domain_fit_score ? `${Math.round(parsedAnalysis.domain_fit_score)}%` : 'N/A'}
                            </div>
                          </div>
                          <div className="bg-ui-page/60 p-3 rounded-lg border border-ui-line-soft text-center">
                            <div className="text-[0.6875rem] text-ui-muted uppercase font-medium">Work Auth / Eligibility</div>
                            <div className="text-lg font-bold text-ui-ink-amber-400 mt-0.5">
                              {parsedAnalysis.eligibility_fit_score ? `${Math.round(parsedAnalysis.eligibility_fit_score)}%` : 'N/A'}
                            </div>
                          </div>
                        </div>
                      )}

                      {(job.suitability_reason || parsedAnalysis?.suitability_reason) && (
                        <div>
                          <p className="text-xs text-ui-body leading-relaxed font-sans">
                            {job.suitability_reason || parsedAnalysis?.suitability_reason}
                          </p>
                        </div>
                      )}

                      {parsedAnalysis?.employer_pain_points && parsedAnalysis.employer_pain_points.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-ui-line-amber-900/30">
                          <div className="text-[0.6875rem] font-bold text-ui-ink-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                            <Target className="h-3.5 w-3.5 text-ui-ink-amber-500" />
                            Target Employer Pain Points (DoorKnock Hooks)
                          </div>
                          <ul className="space-y-1.5">
                            {parsedAnalysis.employer_pain_points.map((pt, i) => (
                              <li key={i} className="text-xs text-ui-body flex items-start gap-2 bg-ui-page/40 p-2 rounded-md border border-ui-line-amber-950/50">
                                <span className="text-ui-ink-amber-500 font-bold">•</span>
                                <span>{pt}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {parsedAnalysis?.key_strengths && parsedAnalysis.key_strengths.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-ui-line-amber-900/30">
                          <div className="text-[0.6875rem] font-bold text-ui-ink-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                            <CheckCircle2 className="h-3.5 w-3.5 text-ui-ink-emerald-500" />
                            Candidate Evidence Highlights
                          </div>
                          <ul className="space-y-1.5">
                            {parsedAnalysis.key_strengths.map((str, i) => (
                              <li key={i} className="text-xs text-ui-body flex items-start gap-2 bg-ui-page/40 p-2 rounded-md border border-ui-line-emerald-950/50">
                                <span className="text-ui-ink-emerald-500 font-bold">✓</span>
                                <span>{str}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {parsedAnalysis?.gaps_or_risks && parsedAnalysis.gaps_or_risks.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-ui-line-amber-900/30">
                          <div className="text-[0.6875rem] font-bold text-ui-ink-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                            <AlertTriangle className="h-3.5 w-3.5 text-ui-ink-rose-500" />
                            Identified Gaps & Interview Risks
                          </div>
                          <ul className="space-y-1.5">
                            {parsedAnalysis.gaps_or_risks.map((gap, i) => (
                              <li key={i} className="text-xs text-ui-body flex items-start gap-2 bg-ui-page/40 p-2 rounded-md border border-ui-line-rose-950/50">
                                <span className="text-ui-ink-rose-500 font-bold">!</span>
                                <span>{gap}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {job.job_brief && (
                <div>
                  <h4 className="text-xs font-bold text-ui-muted uppercase tracking-wider mb-2">
                    Executive Brief
                  </h4>
                  <p className="text-sm text-ui-body leading-relaxed bg-ui-page/60 p-4 rounded-xl border border-ui-line-soft">
                    {job.job_brief}
                  </p>
                </div>
              )}

              <div>
                <h4 className="text-xs font-bold text-ui-muted uppercase tracking-wider mb-2">
                  Full Job Description
                </h4>
                <div className="text-xs text-ui-body whitespace-pre-wrap leading-relaxed bg-ui-page/80 p-5 rounded-xl border border-ui-line-soft max-h-96 overflow-y-auto select-text font-mono">
                  {job.job_description || 'No job description text available.'}
                </div>
              </div>
            </div>
          ) : activeTab === 'recon' ? (
            <div className="space-y-6">
              {/* Recon Header & Action Bar */}
              <div className="bg-ui-page/80 border border-ui-line-soft rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-md">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-ui-fill-amber-500/10 border border-ui-line-amber-500/30 flex items-center justify-center text-ui-ink-amber-400">
                    <Building2 className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-ui-heading flex items-center gap-2">
                      <span>Company & Department Recon Intelligence</span>
                      {parsedRecon && (
                        <span className="text-[0.625rem] font-mono px-2 py-0.5 rounded bg-ui-fill-emerald-500/10 text-ui-ink-emerald-300 border border-ui-line-emerald-500/30">
                          AI research
                        </span>
                      )}
                    </h3>
                    <p className="text-xs text-ui-muted mt-0.5">
                      Strategic business model, department charter, and direct supervisor pain points.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleRunRecon}
                    disabled={isReconning}
                    className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-ui-fill-amber-500/10 hover:bg-ui-fill-amber-500/20 text-ui-ink-amber-300 border border-ui-line-amber-500/40 transition shadow-sm disabled:opacity-50 cursor-pointer"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${isReconning ? 'animate-spin text-ui-ink-amber-400' : ''}`} />
                    <span>{isReconning ? 'Executing Recon...' : activeJob?.company_recon_status === 'failed' ? 'Retry Recon' : parsedRecon ? 'Re-run Recon' : 'Run Recon Now'}</span>
                  </button>
                </div>
              </div>

              <div role="status" aria-live="polite" className="text-sm text-ui-body">
                {isReconning ? 'Company Recon is running. You can close this window; results will be saved to this job.'
                  : activeJob?.company_recon_status === 'failed' ? 'Company Recon failed or was interrupted. Your job is saved. Check AI settings, then retry.'
                  : null}
              </div>

              {!parsedRecon ? (
                <div className="text-center py-12 border border-dashed border-ui-line-soft rounded-xl space-y-3 bg-ui-page/40">
                  <Building2 className="h-10 w-10 text-ui-faint mx-auto" />
                  <div>
                    <p className="text-sm font-semibold text-ui-body">{isReconning ? 'Researching company and department...'
                      : activeJob?.company_recon_status === 'failed' ? 'Company research is unavailable.' : 'No company reconnaissance performed yet.'}</p>
                    <p className="text-xs text-ui-subtle mt-1 max-w-md mx-auto">
                      Analyze employer monetization, macro headwinds, target department charter, and hiring manager anxieties to power high-conversion outreach.
                    </p>
                  </div>
                  <button
                    onClick={handleRunRecon}
                    disabled={isReconning}
                    className="px-4 py-2 text-xs font-bold rounded-xl bg-ui-fill-amber-600 hover:bg-ui-fill-amber-500 text-ui-on-action transition shadow-lg shadow-amber-950/50 inline-flex items-center gap-2"
                  >
                    <Sparkles className="h-4 w-4" />
                    <span>{isReconning ? 'Executing Recon...' : activeJob?.company_recon_status === 'failed' ? 'Retry Company Recon' : 'Run Strategic Recon Now'}</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Meta badges */}
                  <div className="flex flex-wrap items-center gap-2 text-xs text-ui-muted">
                    <span className="font-semibold text-ui-secondary">{parsedRecon.company_name}</span>
                    {parsedRecon.company_stage?.funding_or_tier && (
                      <span className="px-2 py-0.5 rounded bg-ui-raised text-ui-body border border-ui-line">
                        {parsedRecon.company_stage.funding_or_tier}
                      </span>
                    )}
                    {parsedRecon.company_stage?.market_standing && (
                      <span className="px-2 py-0.5 rounded bg-ui-fill-blue-500/10 text-ui-ink-blue-300 border border-ui-line-blue-500/20">
                        {parsedRecon.company_stage.market_standing}
                      </span>
                    )}
                    {parsedRecon.researched_at && (
                      <span className="text-ui-subtle text-[0.6875rem] font-mono ml-auto">
                        Analyzed: {formatDateTime(parsedRecon.researched_at, settings.timezone)}
                      </span>
                    )}
                  </div>

                  {/* 2-Column Core Intelligence Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Card 1: Business Model & Revenue Engine */}
                    <div className="bg-ui-page/80 border border-ui-line-soft rounded-xl p-4 space-y-3 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-ui-line-soft">
                          <span className="text-xs font-bold text-ui-ink-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                            <DollarSign className="h-4 w-4 text-ui-ink-amber-500" />
                            Business Model & Revenue Engine
                          </span>
                        </div>

                        {parsedRecon.business_model?.revenue_engine && (
                          <div>
                            <span className="text-[0.6875rem] font-semibold text-ui-muted uppercase block">Monetization Engine</span>
                            <p className="text-xs text-ui-secondary mt-0.5 leading-relaxed">{parsedRecon.business_model.revenue_engine}</p>
                          </div>
                        )}

                        {parsedRecon.business_model?.target_customers && (
                          <div>
                            <span className="text-[0.6875rem] font-semibold text-ui-muted uppercase block">Target Customers</span>
                            <p className="text-xs text-ui-body mt-0.5 leading-relaxed">{parsedRecon.business_model.target_customers}</p>
                          </div>
                        )}

                        {parsedRecon.business_model?.value_proposition && (
                          <div>
                            <span className="text-[0.6875rem] font-semibold text-ui-muted uppercase block">Value Proposition & Moat</span>
                            <p className="text-xs text-ui-body mt-0.5 leading-relaxed">{parsedRecon.business_model.value_proposition}</p>
                          </div>
                        )}

                        {parsedRecon.business_model?.macro_challenges && (
                          <div className="bg-ui-fill-amber-950/20 p-3 rounded-lg border border-ui-line-amber-900/40 text-xs text-ui-ink-amber-200/90 leading-relaxed">
                            <span className="font-bold text-ui-ink-amber-300 block mb-1">⚠️ Macro Bottlenecks & Friction:</span>
                            {parsedRecon.business_model.macro_challenges}
                          </div>
                        )}
                      </div>

                      {parsedRecon.company_stage?.scale_and_momentum && (
                        <div className="pt-2 border-t border-ui-line-soft text-[0.6875rem] text-ui-muted">
                          <span className="font-medium text-ui-body">Scale & Momentum: </span>
                          {parsedRecon.company_stage.scale_and_momentum}
                        </div>
                      )}
                    </div>

                    {/* Card 2: Department Charter & Direct Supervisor */}
                    <div className="bg-ui-page/80 border border-ui-line-soft rounded-xl p-4 space-y-3 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-ui-line-soft">
                          <span className="text-xs font-bold text-ui-ink-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                            <Briefcase className="h-4 w-4 text-ui-ink-blue-500" />
                            Department Charter & Supervisor Pressure
                          </span>
                          {parsedRecon.department_intel?.role_archetype && (
                            <span className="text-[0.625rem] font-bold px-2 py-0.5 rounded bg-ui-fill-blue-500/20 text-ui-ink-blue-300 border border-ui-line-blue-500/30">
                              {parsedRecon.department_intel.role_archetype}
                            </span>
                          )}
                        </div>

                        {parsedRecon.department_intel?.team_name && (
                          <div>
                            <span className="text-[0.6875rem] font-semibold text-ui-muted uppercase block">Target Team / Unit</span>
                            <p className="text-xs font-mono font-semibold text-ui-ink-blue-200 mt-0.5">{parsedRecon.department_intel.team_name}</p>
                          </div>
                        )}

                        {parsedRecon.department_intel?.team_charter && (
                          <div>
                            <span className="text-[0.6875rem] font-semibold text-ui-muted uppercase block">Department Mission</span>
                            <p className="text-xs text-ui-secondary mt-0.5 leading-relaxed">{parsedRecon.department_intel.team_charter}</p>
                          </div>
                        )}

                        {parsedRecon.department_intel?.hiring_manager_profile && (
                          <div>
                            <span className="text-[0.6875rem] font-semibold text-ui-muted uppercase block">Deduced Direct Supervisor</span>
                            <p className="text-xs text-ui-body mt-0.5 font-medium">{parsedRecon.department_intel.hiring_manager_profile}</p>
                          </div>
                        )}

                        {parsedRecon.department_intel?.manager_core_pressure && (
                          <div className="bg-ui-fill-blue-950/20 p-3 rounded-lg border border-ui-line-blue-900/40 text-xs text-ui-ink-blue-200/90 leading-relaxed">
                            <span className="font-bold text-ui-ink-blue-300 block mb-1">🔥 Direct Supervisor Core Anxiety:</span>
                            {parsedRecon.department_intel.manager_core_pressure}
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-ui-line-soft text-[0.6875rem] text-ui-muted flex items-center justify-between">
                        <span>Injected into Knock Outreach</span>
                        <span className="text-ui-ink-emerald-400 font-semibold">Active Fuel</span>
                      </div>
                    </div>
                  </div>

                  {/* Strategic Alignment Card */}
                  {parsedRecon.strategic_positioning_for_candidate && (
                    <div className="bg-ui-page/60 border border-ui-line-soft rounded-xl p-4 space-y-2">
                      <div className="text-xs font-bold text-ui-body uppercase tracking-wider flex items-center gap-1.5">
                        <Target className="h-4 w-4 text-ui-ink-emerald-400" />
                        Downstream Document & Outreach Alignment
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        {parsedRecon.strategic_positioning_for_candidate.tailor_summary_angle && (
                          <div className="bg-ui-panel/70 p-3 rounded-lg border border-ui-line-soft space-y-1">
                            <span className="text-ui-ink-emerald-400 font-semibold block text-[0.6875rem]">📄 Tailor Summary Angle:</span>
                            <p className="text-ui-body leading-relaxed">{parsedRecon.strategic_positioning_for_candidate.tailor_summary_angle}</p>
                          </div>
                        )}
                        {parsedRecon.strategic_positioning_for_candidate.cover_letter_hook_angle && (
                          <div className="bg-ui-panel/70 p-3 rounded-lg border border-ui-line-soft space-y-1">
                            <span className="text-ui-ink-amber-400 font-semibold block text-[0.6875rem]">✉️ Cover Letter Problem-First Hook:</span>
                            <p className="text-ui-body leading-relaxed">{parsedRecon.strategic_positioning_for_candidate.cover_letter_hook_angle}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : activeTab === 'contacts' ? (
            <div className="space-y-6">
              {/* Header and Add Contact Trigger */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-ui-line-soft">
                <div>
                  <h3 className="text-sm font-bold text-ui-heading flex items-center gap-2">
                    <UserCheck className="h-4 w-4 text-ui-ink-blue-400" />
                    <span>Gatekeeper Recon & Outreach Console</span>
                  </h3>
                  <p className="text-xs text-ui-muted mt-0.5">
                    Target decision-makers at {job.company} with tailored Sepia-compliant outreach drafts.
                  </p>
                </div>

                <button
                  onClick={() => setShowAddContact(!showAddContact)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-ui-fill-blue-600 hover:bg-ui-fill-blue-500 text-ui-on-color transition shadow-sm"
                >
                  <UserPlus className="h-3.5 w-3.5" />
                  <span>{showAddContact ? 'Cancel' : 'Add Gatekeeper'}</span>
                </button>
              </div>

              {/* Agent Command Banner */}
              <div className="bg-gradient-to-r from-ui-fill-blue-950/40 via-ui-panel to-ui-page p-4 rounded-xl border border-ui-line-blue-500/30 space-y-2.5 shadow-md">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-ui-ink-blue-400 flex items-center gap-1.5">
                      <Sparkles className="h-4 w-4 text-ui-ink-blue-400" />
                      AI Agent Recon Instructions (LinkedIn MCP)
                    </span>
                    <span className="text-[0.625rem] font-mono px-2 py-0.5 rounded bg-ui-fill-blue-500/10 text-ui-ink-blue-300 border border-ui-line-blue-500/30">
                      doorknock-scout
                    </span>
                  </div>
                  <button
                    onClick={handleCopyAgentCommand}
                    className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-ui-fill-blue-600/30 hover:bg-ui-fill-blue-600/50 text-ui-ink-blue-200 border border-ui-line-blue-500/40 transition"
                  >
                    {copiedAgentCmd ? <Check className="h-3.5 w-3.5 text-ui-ink-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>{copiedAgentCmd ? 'Command Copied!' : 'Copy Agent Command'}</span>
                  </button>
                </div>
                <div className="bg-ui-page/80 p-2.5 rounded-lg border border-ui-line-soft flex items-center justify-between gap-3 text-xs font-mono text-ui-body select-text">
                  <span className="text-ui-ink-amber-300 truncate">{`scout gatekeepers for job ${activeJob?.id} (${activeJob?.company} - ${activeJob?.title})`}</span>
                  <span className="text-[0.625rem] text-ui-subtle font-sans shrink-0">Paste into Antigravity or Codex CLI</span>
                </div>
                <p className="text-[0.6875rem] text-ui-muted leading-relaxed">
                  💡 The AI Agent invokes <code className="text-ui-body">linkedin-mcp-server</code> safely, discovers Hiring Manager / Recruiter / Peer, and has full authority to rewrite/update the DoorKnock DB via <code className="text-ui-body">POST /api/jobs/{'{job_id}'}/contacts</code>.
                </p>
              </div>

              {/* Add Contact Inline Form */}
              {showAddContact && (
                <form onSubmit={handleAddContactSubmit} className="bg-ui-page p-4 rounded-xl border border-ui-line-soft space-y-3 animate-fadeIn">
                  <h4 className="text-xs font-bold text-ui-secondary uppercase tracking-wider">New Gatekeeper Record</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div>
                      <label className="text-ui-muted block mb-1">Full Name *</label>
                      <input
                        type="text"
                        required
                        value={newContact.name}
                        onChange={(e) => setNewContact({ ...newContact, name: e.target.value })}
                        placeholder="e.g. Alex Kowalski"
                        className="w-full bg-ui-panel border border-ui-line rounded-lg px-3 py-1.5 text-ui-primary focus:outline-none focus:border-ui-line-blue-500"
                      />
                    </div>
                    <div>
                      <label className="text-ui-muted block mb-1">Role Title *</label>
                      <input
                        type="text"
                        required
                        value={newContact.role_title}
                        onChange={(e) => setNewContact({ ...newContact, role_title: e.target.value })}
                        placeholder="e.g. Head of Engineering"
                        className="w-full bg-ui-panel border border-ui-line rounded-lg px-3 py-1.5 text-ui-primary focus:outline-none focus:border-ui-line-blue-500"
                      />
                    </div>
                    <div>
                      <label className="text-ui-muted block mb-1">Contact Type</label>
                      <select
                        value={newContact.contact_type}
                        onChange={(e) => setNewContact({ ...newContact, contact_type: e.target.value })}
                        className="w-full bg-ui-panel border border-ui-line rounded-lg px-3 py-1.5 text-ui-primary focus:outline-none focus:border-ui-line-blue-500"
                      >
                        <option value="hiring_manager">Hiring Manager</option>
                        <option value="recruiter">Recruiter / Talent Partner</option>
                        <option value="peer">Peer / Teammate</option>
                        <option value="alumni">Alumni / Insider</option>
                        <option value="other">Other Gatekeeper</option>
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div>
                      <label className="text-ui-muted block mb-1">LinkedIn Profile URL</label>
                      <input
                        type="url"
                        value={newContact.linkedin_url}
                        onChange={(e) => setNewContact({ ...newContact, linkedin_url: e.target.value })}
                        placeholder="https://linkedin.com/in/..."
                        className="w-full bg-ui-panel border border-ui-line rounded-lg px-3 py-1.5 text-ui-primary focus:outline-none focus:border-ui-line-blue-500"
                      />
                    </div>
                    <div>
                      <label className="text-ui-muted block mb-1">Email (Optional)</label>
                      <input
                        type="email"
                        value={newContact.email}
                        onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
                        placeholder="alex@company.com"
                        className="w-full bg-ui-panel border border-ui-line rounded-lg px-3 py-1.5 text-ui-primary focus:outline-none focus:border-ui-line-blue-500"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowAddContact(false)}
                      className="px-3 py-1.5 text-xs text-ui-muted hover:text-ui-heading"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isAddingContact}
                      className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-ui-fill-blue-600 hover:bg-ui-fill-blue-500 text-ui-on-color transition disabled:opacity-50"
                    >
                      {isAddingContact ? 'Saving...' : 'Save Gatekeeper'}
                    </button>
                  </div>
                </form>
              )}

              {/* Contacts List & Outreach Decks */}
              {(!activeJob?.contacts || activeJob.contacts.length === 0) ? (
                <div className="text-center py-12 border border-dashed border-ui-line-soft rounded-xl space-y-3 bg-ui-page/40">
                  <UserCheck className="h-10 w-10 text-ui-faint mx-auto" />
                  <div>
                    <p className="text-sm font-semibold text-ui-body">No gatekeepers recorded yet for this position.</p>
                    <p className="text-xs text-ui-subtle mt-1 max-w-md mx-auto">
                      Add the Hiring Manager, Recruiter, or Peer from LinkedIn to generate tailored outreach drafts.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowAddContact(true)}
                    className="px-4 py-2 text-xs font-bold rounded-xl bg-ui-fill-blue-600 hover:bg-ui-fill-blue-500 text-ui-on-color transition shadow-lg shadow-blue-950/50 inline-flex items-center gap-2"
                  >
                    <UserPlus className="h-4 w-4" />
                    <span>Add First Gatekeeper</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  {activeJob.contacts.map((contact) => (
                    <div key={contact.id} className="bg-ui-page rounded-xl border border-ui-line-soft overflow-hidden shadow-lg">
                      {/* Gatekeeper Card Header */}
                      <div className="p-4 bg-ui-panel/70 border-b border-ui-line-soft/80 flex flex-wrap items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-ui-heading">{contact.name}</span>
                            <span className="text-[0.625rem] uppercase font-semibold px-2 py-0.5 rounded bg-ui-raised text-ui-ink-amber-300 border border-ui-line">
                              {contact.contact_type.replace('_', ' ')}
                            </span>
                          </div>
                          <p className="text-xs text-ui-muted">{contact.role_title}</p>
                          <div className="flex items-center gap-3 text-xs text-ui-subtle pt-0.5">
                            {contact.linkedin_url && (
                              <a
                                href={contact.linkedin_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-ui-ink-blue-400 hover:underline flex items-center gap-1"
                              >
                                LinkedIn Profile <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                            {contact.email && (
                              <span className="text-ui-muted flex items-center gap-1 font-mono text-[0.6875rem]">
                                <Mail className="h-3 w-3 text-ui-subtle" /> {contact.email}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleGenerateOutreach(contact.id)}
                            disabled={generatingOutreach[contact.id]}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-ui-fill-emerald-500/10 hover:bg-ui-fill-emerald-500/20 text-ui-ink-emerald-300 border border-ui-line-emerald-500/40 transition shadow-sm disabled:opacity-50 cursor-pointer"
                            title="Generate Sepia De-AI outreach drafts"
                          >
                            <Sparkles className={`h-3.5 w-3.5 ${generatingOutreach[contact.id] ? 'animate-spin' : ''}`} />
                            <span>{generatingOutreach[contact.id] ? 'Generating Drafts...' : (contact.messages && contact.messages.length > 0) ? 'Regenerate Drafts' : 'Generate Outreach Drafts'}</span>
                          </button>

                          <button
                            onClick={() => handleDeleteContact(contact.id)}
                            className="p-1.5 text-ui-subtle hover:text-ui-ink-red-400 hover:bg-ui-fill-red-950/40 border border-transparent hover:border-ui-line-red-900/50 rounded-lg transition"
                            title="Delete gatekeeper and drafts from DB"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Outreach Messages List */}
                      <div className="p-4 space-y-4">
                        {(!contact.messages || contact.messages.length === 0) ? (
                          <div className="text-center py-6 text-ui-subtle text-xs">
                            No outreach messages drafted yet. Click "Generate Outreach Drafts" to create personalized messages.
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {contact.messages.map((msg) => {
                              const isConnect = msg.channel === 'linkedin_connect';
                              const charCount = msg.body.length;
                              const wordCount = msg.body.split(/\s+/).filter(Boolean).length;
                              const isCopied = copiedMsgId === msg.id;

                              return (
                                <div key={msg.id} className="bg-ui-panel/80 rounded-xl border border-ui-line-soft p-4 flex flex-col justify-between space-y-3">
                                  <div className="space-y-2">
                                    <div className="flex items-center justify-between pb-2 border-b border-ui-line-soft">
                                      <div>
                                        <span className="text-xs font-bold text-ui-heading capitalize">
                                          {isConnect ? 'LinkedIn Connection Note' : 'InMail / Cold Email'}
                                        </span>
                                        <span className="text-[0.625rem] text-ui-muted block mt-0.5">
                                          {isConnect ? 'Strictly ≤ 300 characters' : '80–120 words (Problem-First)'}
                                        </span>
                                      </div>
                                      <span className={`text-[0.625rem] font-mono px-2 py-0.5 rounded border ${
                                        isConnect
                                          ? (charCount <= 300 ? 'bg-ui-page text-ui-ink-emerald-400 border-ui-line-soft' : 'bg-ui-fill-red-950 text-ui-ink-red-400 border-ui-line-red-800')
                                          : 'bg-ui-page text-ui-ink-blue-400 border-ui-line-soft'
                                      }`}>
                                        {isConnect ? `${charCount}/300 chars` : `${wordCount} words`}
                                      </span>
                                    </div>

                                    {msg.subject && (
                                      <div className="text-xs font-mono text-ui-body bg-ui-page px-2.5 py-1.5 rounded border border-ui-line-soft/80">
                                        <span className="text-ui-subtle">Subject: </span>{msg.subject}
                                      </div>
                                    )}

                                    <div className="text-xs text-ui-secondary font-sans leading-relaxed whitespace-pre-wrap select-text bg-ui-page/70 p-3 rounded-lg border border-ui-line-soft/60 max-h-56 overflow-y-auto">
                                      {msg.body}
                                    </div>
                                  </div>

                                  <div className="pt-2 border-t border-ui-line-soft/80 flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-1.5 text-xs">
                                      <span className="text-ui-subtle text-[0.6875rem]">Status:</span>
                                      <select
                                        value={msg.status}
                                        onChange={(e) => handleUpdateMessageStatus(msg.id, e.target.value)}
                                        className="bg-ui-page border border-ui-line text-ui-body text-[0.6875rem] rounded px-2 py-0.5 focus:outline-none focus:border-ui-line-amber-500"
                                      >
                                        <option value="draft">Draft</option>
                                        <option value="ready_to_send">Ready to Send</option>
                                        <option value="sent">Sent</option>
                                        <option value="replied">Replied</option>
                                        <option value="ignored">Ignored</option>
                                      </select>
                                      {msg.sent_at && (
                                        <span className="text-[0.625rem] text-ui-ink-emerald-400">✓ Sent</span>
                                      )}
                                    </div>

                                    <button
                                      onClick={() => handleCopyMessage(msg.id, msg.body)}
                                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition ${
                                        isCopied
                                          ? 'bg-ui-fill-emerald-600 text-ui-on-color'
                                          : 'bg-ui-raised hover:bg-ui-hover text-ui-secondary'
                                      }`}
                                    >
                                      {isCopied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                                      <span>{isCopied ? 'Copied!' : 'Copy'}</span>
                                    </button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : activeTab === 'resume' ? (
            renderDocumentPreview('resume')
          ) : activeTab === 'cover_letter' ? (
            renderDocumentPreview('cover_letter')
          ) : (
            <div className="space-y-3">
              {timelineNotice && <p role="status" className="text-xs text-ui-body">{timelineNotice} {undoEventId && <button disabled={timelineBusy} onClick={() => void correctTimeline(undoEventId, true)} className="ml-2 text-ui-ink-amber-300 underline disabled:opacity-50">Undo</button>}</p>}
              {timelineError && <p role="alert" className="text-xs text-ui-ink-red-300">{timelineError}</p>}
              {(!activeJob?.timeline || activeJob.timeline.length === 0) ? (
                <div className="text-center py-10 border border-dashed border-ui-line-soft rounded-xl">
                  <Clock className="h-10 w-10 text-ui-faint mx-auto mb-2" />
                  <p className="text-sm text-ui-muted">No timeline events recorded yet.</p>
                </div>
              ) : (
                <div className="relative border-l border-ui-line-soft ml-4 space-y-6">
                  {activeJob.timeline.map((event) => (
                    <div key={event.id} className="relative pl-6">
                      <div className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full bg-ui-fill-amber-500 border-2 border-ui-line-subtle"></div>
                      <div className="flex items-center justify-between text-xs text-ui-muted">
                        <span className="font-semibold text-ui-secondary">{event.title}</span>
                        <span title={formatDateTime(event.occurred_at, settings.timezone)}>
                          {formatDate(event.occurred_at, settings.timezone)}
                          {hasUnknownTimeZone(event.occurred_at) && ' · time zone not recorded'}
                        </span>
                      </div>
                      <div className="mt-2 flex items-center gap-2 text-xs">
                        {deleteEventId === event.id ? <>
                          <span className="text-ui-muted">Delete this event? You can undo it.</span>
                          <button disabled={timelineBusy} onClick={() => void correctTimeline(event.id)} className="text-ui-ink-red-300 hover:text-ui-ink-red-200 disabled:opacity-50">Confirm delete</button>
                          <button disabled={timelineBusy} onClick={() => setDeleteEventId(null)} className="text-ui-muted hover:text-ui-heading">Cancel</button>
                        </> : <button disabled={timelineBusy} onClick={() => setDeleteEventId(event.id)} aria-label={`Delete timeline event: ${event.title}`} className="flex items-center gap-1 text-ui-subtle hover:text-ui-ink-red-300 disabled:opacity-50"><Trash2 className="h-3 w-3" />Delete</button>}
                      </div>
                      {event.description && (
                        <p className="text-xs text-ui-muted mt-1">{event.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {!!activeJob?.deleted_timeline?.length && <details className="border-t border-ui-line-soft pt-3 text-xs text-ui-subtle">
                <summary className="cursor-pointer">Deleted events ({activeJob.deleted_timeline.length})</summary>
                <div className="mt-3 space-y-2">{activeJob.deleted_timeline.map((event) => <div key={event.id} className="flex items-center justify-between gap-3"><span>{event.title} · {formatDate(event.occurred_at, settings.timezone)}</span><button disabled={timelineBusy} onClick={() => void correctTimeline(event.id, true)} className="text-ui-ink-amber-300 disabled:opacity-50">Restore</button></div>)}</div>
              </details>}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-ui-line-soft bg-ui-page/60 flex items-center justify-between">
          <div>
            {job && onDeleteJob && (
              confirmDelete ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-ui-ink-red-400 font-medium">Confirm delete?</span>
                  <button
                    onClick={() => { onDeleteJob(job.id); setConfirmDelete(false); }}
                    className="px-3 py-1 text-xs font-semibold bg-ui-fill-red-600 hover:bg-ui-fill-red-500 text-ui-on-color rounded-lg transition shadow-md shadow-red-950/50"
                  >
                    Yes, Delete
                  </button>
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="px-2 py-1 text-xs text-ui-muted hover:text-ui-heading transition"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-ui-ink-red-400 hover:text-ui-ink-red-300 hover:bg-ui-fill-red-950/40 border border-ui-line-red-900/50 rounded-lg transition"
                  title="Delete this job and associated records"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Delete Job</span>
                </button>
              )
            )}
          </div>

          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-ui-muted hover:text-ui-heading rounded-lg transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
