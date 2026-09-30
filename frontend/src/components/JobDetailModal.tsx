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

interface JobDetailModalProps {
  job: Job | null;
  onClose: () => void;
  onMoveStage?: (applicationId: string, toStage: string, outcome?: string) => void;
  onDeleteJob?: (jobId: string) => void;
  isLoading: boolean;
}

const STAGES_LIST = [
  { key: 'saved', label: 'Saved' },
  { key: 'applied', label: 'Applied' },
  { key: 'knocked', label: 'Knocked' },
  { key: 'recruiter_screen', label: 'Recruiter Screen' },
  { key: 'assessment', label: 'Assessment' },
  { key: 'team_match', label: 'Team Match' },
  { key: 'technical_interview', label: 'Tech Interview' },
  { key: 'final_round', label: 'Final Round' },
  { key: 'offer', label: 'Offer 🎉' },
  { key: 'closed', label: 'Closed' },
];

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  job,
  onClose,
  onMoveStage,
  onDeleteJob,
  isLoading,
}) => {
  const { settings } = useTimeSettings();
  const [activeTab, setActiveTab] = useState<'jd' | 'recon' | 'contacts' | 'resume' | 'cover_letter' | 'timeline'>('jd');
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false);
  const [copiedJobIdentifier, setCopiedJobIdentifier] = useState<string | null>(null);

  const [currentJob, setCurrentJob] = useState<Job | null>(job);
  const [isRematching, setIsRematching] = useState<boolean>(false);

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

  const [isReconning, setIsReconning] = useState<boolean>(false);

  const handleRunRecon = async () => {
    if (!activeJob?.id) return;
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
        <div className="flex flex-col items-center justify-center py-12 px-6 bg-slate-950/40 border border-dashed border-slate-800 rounded-2xl text-center">
          <div className="p-3.5 bg-slate-800/80 rounded-2xl text-slate-400 mb-3 border border-slate-700">
            {type === 'resume' ? <FileText className="h-8 w-8 text-amber-500/80" /> : <Mail className="h-8 w-8 text-amber-500/80" />}
          </div>
          <h3 className="text-base font-semibold text-white mb-1">
            No {docTitle} Generated Yet
          </h3>
          <p className="text-xs text-slate-400 max-w-md mb-4 leading-relaxed">
            Create this document with DoorKnock's Typst engine, or ask your AI Agent to draft it in chat.
          </p>

          {/* Workflow Awareness: Company Recon Status */}
          {parsedRecon ? (
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-emerald-300 text-xs mb-4 max-w-lg w-full text-left">
              <Sparkles className="h-4 w-4 text-emerald-400 shrink-0" />
              <span className="text-[11px] leading-relaxed">
                <strong>Recon Active:</strong> Tailoring will automatically align with {parsedRecon.department_intel?.team_name || 'department'} frictions and business model hooks.
              </span>
            </div>
          ) : (
            <div className="flex items-center justify-between gap-3 px-3.5 py-2 rounded-xl bg-amber-950/30 border border-amber-800/40 text-amber-200 text-xs mb-4 max-w-lg w-full text-left">
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-amber-400 shrink-0" />
                <span className="text-[11px] text-amber-200/90 leading-relaxed">
                  Tip: Run <strong>Company Recon</strong> first to feed strategic business model & department hooks into your documents.
                </span>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('recon')}
                className="text-[11px] font-semibold text-amber-400 hover:text-amber-300 underline shrink-0 cursor-pointer"
              >
                Go to Recon
              </button>
            </div>
          )}

          <button
            onClick={() => handleTailorDocs(type)}
            disabled={isTailoring}
            className="flex items-center gap-2 px-5 py-2.5 text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white rounded-xl shadow-lg shadow-amber-950/50 transition mb-4 disabled:opacity-50 cursor-pointer"
          >
            <Sparkles className={`h-4 w-4 ${isTailoring ? 'animate-spin text-amber-200' : 'text-amber-200'}`} />
            <span>{isTailoring ? 'Tailoring with Typst...' : `✨ Tailor ${docTitle} Now`}</span>
          </button>

          {/* AI Prompt Box: Option 1 (Chat with Agent) */}
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl p-3 text-left mb-4 shadow-inner">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Ask Agent in Chat (Option 1)
              </span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(agentChatPrompt);
                  setCopiedPrompt(true);
                  setTimeout(() => setCopiedPrompt(false), 2000);
                }}
                className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition cursor-pointer"
              >
                {copiedPrompt ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copiedPrompt ? 'Copied' : 'Copy Prompt'}</span>
              </button>
            </div>
            <p className="text-xs text-slate-200 bg-slate-950 p-2.5 rounded border border-slate-800/80 select-all leading-relaxed font-sans">
              {agentChatPrompt}
            </p>
          </div>

          <button
            onClick={handleRefreshDocs}
            disabled={isLoadingDocs || isTailoring}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white rounded-xl border border-slate-700 transition shadow cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoadingDocs ? 'animate-spin text-amber-400' : ''}`} />
            <span>Check for Generated PDF</span>
          </button>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* Document Header Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-950/80 border border-slate-800 rounded-xl">
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-400 font-medium">Version:</label>
            <select
              value={selectedVersion}
              onChange={(e) => setSelectedVersion(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-amber-500 font-mono font-medium"
            >
              {docInfo.versions.map((v) => (
                <option key={v.version} value={v.version}>
                  {v.version} {v.version === docInfo.latest_version ? '(Latest)' : ''}
                </option>
              ))}
            </select>

            {activeVersionData && (
              <span className="text-[11px] text-slate-400 hidden sm:inline font-mono">
                {(activeVersionData.size_bytes / 1024).toFixed(1)} KB • {activeVersionData.download_filename || activeVersionData.filename}
              </span>
            )}

            {parsedRecon ? (
              <span className="hidden lg:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-800/60" title="Tailored using Company Recon business model and department hooks">
                <Sparkles className="h-3 w-3 text-emerald-400" />
                <span>Recon Intel Synced</span>
              </span>
            ) : (
              <button
                type="button"
                onClick={() => setActiveTab('recon')}
                className="hidden lg:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-amber-950/40 text-amber-300/80 border border-amber-900/60 hover:text-amber-200 hover:border-amber-700 transition cursor-pointer"
                title="Run Company Recon to unlock deeper business model hooks"
              >
                <Building2 className="h-3 w-3 text-amber-400" />
                <span>Run Recon for Deep Hooks</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleTailorDocs(type)}
              disabled={isTailoring}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 font-medium rounded-lg transition border border-amber-900/40 disabled:opacity-50 cursor-pointer"
              title={`Re-tailor ${docTitle} with Typst`}
            >
              <Sparkles className={`h-3.5 w-3.5 ${isTailoring ? 'animate-spin' : ''}`} />
              <span>{isTailoring ? 'Tailoring...' : `Re-tailor ${docTitle}`}</span>
            </button>

            <button
              onClick={handleRefreshDocs}
              disabled={isLoadingDocs || isTailoring}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition border border-slate-700"
              title="Refresh document status"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoadingDocs ? 'animate-spin text-amber-400' : ''}`} />
              <span>Refresh</span>
            </button>

            <a
              href={previewUrl}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition border border-slate-700"
              title="Open full PDF in new tab"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>Open Tab</span>
            </a>

            <a
              href={downloadUrl}
              download={downloadFileName}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-amber-600 hover:bg-amber-500 text-white font-medium rounded-lg transition shadow shadow-amber-950/40"
              title={`Download as ${downloadFileName}`}
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download PDF</span>
            </a>
          </div>
        </div>

        {/* Embedded PDF iframe */}
        <div className="relative w-full h-[66vh] rounded-xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl flex flex-col">
          <iframe
            src={previewUrl}
            className="w-full h-full border-0 bg-slate-900"
            title={`${docTitle} Preview`}
          />
        </div>
      </div>
    );
  };

  if (!job && !isLoading) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-6xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-800 bg-slate-950/80 flex items-start justify-between gap-4">
          {isLoading || !job ? (
            <div className="animate-pulse space-y-2 w-full">
              <div className="h-6 bg-slate-800 rounded w-1/3"></div>
              <div className="h-4 bg-slate-800 rounded w-1/4"></div>
            </div>
          ) : (
            <div className="w-full">
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-300 flex items-center gap-1.5">
                    <Building2 className="h-4 w-4 text-amber-500" />
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
                      STRONG_KNOCK: { label: 'STRONG KNOCK', icon: '🎯', style: 'bg-emerald-950/80 text-emerald-400 border-emerald-700/70' },
                      SELECTIVE_APPLY: { label: 'SELECTIVE APPLY', icon: '⚡', style: 'bg-amber-950/80 text-amber-400 border-amber-700/70' },
                      HIGH_RISK_LOW_ROI: { label: 'HIGH RISK', icon: '⚠️', style: 'bg-rose-950/80 text-rose-400 border-rose-800/70' },
                      HARD_PASS: { label: 'HARD PASS', icon: '⛔', style: 'bg-slate-900 text-slate-400 border-slate-700' },
                      DO_NOT_APPLY: { label: 'HARD PASS', icon: '⛔', style: 'bg-slate-900 text-slate-400 border-slate-700' },
                    }[decision] || { label: decision.replace(/_/g, ' '), icon: '📋', style: 'bg-slate-800 text-slate-300 border-slate-700' };

                    return (
                      <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border flex items-center gap-1.5 shadow-sm ${config.style}`}>
                        <span>{config.icon}</span>
                        <span>{config.label}</span>
                      </span>
                    );
                  })()}
                </div>

                {job.application && onMoveStage && (
                  <div className="flex items-center gap-2 text-xs mr-6">
                    <span className="text-slate-400 font-medium">Stage:</span>
                    <select
                      value={
                        job.application.current_stage === 'closed' && job.application.outcome === 'rejected'
                          ? 'closed:rejected'
                          : job.application.current_stage
                      }
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === 'closed:rejected') {
                          onMoveStage(job.application.id, 'closed', 'rejected');
                        } else if (val === 'closed') {
                          onMoveStage(job.application.id, 'closed', job.application?.outcome === 'rejected' ? 'clear' : undefined);
                        } else {
                          onMoveStage(job.application.id, val);
                        }
                      }}
                      className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2 py-1 focus:outline-none focus:border-amber-500 font-medium"
                    >
                      {STAGES_LIST.filter((s) => s.key !== 'closed').map((s) => (
                        <option key={s.key} value={s.key}>{s.label}</option>
                      ))}
                      <option value="closed">Closed</option>
                      <option value="closed:rejected">Closed (Rejected ❌)</option>
                    </select>

                    {job.application.current_stage === 'closed' && (
                      <button
                        type="button"
                        onClick={() => {
                          const newOutcome = job.application?.outcome === 'rejected' ? 'clear' : 'rejected';
                          onMoveStage(job.application.id, 'closed', newOutcome);
                        }}
                        className={`px-2 py-1 rounded-lg text-xs font-semibold border transition flex items-center gap-1.5 ${
                          job.application.outcome === 'rejected'
                            ? 'bg-red-950 text-red-300 border-red-800 hover:bg-red-900/60'
                            : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-red-300 hover:border-red-900'
                        }`}
                        title={job.application.outcome === 'rejected' ? 'Click to clear Rejected outcome' : 'Click to mark as Rejected'}
                      >
                        <span className={job.application.outcome === 'rejected' ? 'text-red-400 font-bold' : 'text-slate-500'}>
                          {job.application.outcome === 'rejected' ? '✕' : '+'}
                        </span>
                        <span>{job.application.outcome === 'rejected' ? 'Rejected' : 'Mark Rejected'}</span>
                      </button>
                    )}
                  </div>
                )}
              </div>

              <h2 className="text-xl font-bold text-white">{job.title}</h2>

              <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-slate-400">
                {job.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3 text-slate-500" />
                    {job.location}
                  </span>
                )}
                {job.workplace_type && (
                  <span className="capitalize bg-slate-800 px-2 py-0.5 rounded">
                    {job.workplace_type}
                  </span>
                )}
                {job.salary_min && (
                  <span className="text-amber-400 flex items-center gap-1 font-medium">
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
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-slate-200 hover:text-white bg-slate-800/90 hover:bg-slate-700 border border-slate-700/80 hover:border-amber-500/50 rounded-lg transition-all shadow-sm group"
                    title="Open original job posting"
                  >
                    <span>Original Posting</span>
                    <ExternalLink className="h-3 w-3 text-slate-400 group-hover:text-amber-400 transition-colors" />
                  </a>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-[11px] text-slate-500">
                {getJobIdentifierItems(job).map(({ label, value }) => {
                  const isCopied = copiedJobIdentifier === value;

                  return (
                    <span key={label} className="inline-flex items-center gap-1.5">
                      <span className="font-medium text-slate-400">{label}:</span>
                      <code className="font-mono text-slate-300 select-text">{value}</code>
                      <button
                        type="button"
                        onClick={() => handleCopyJobIdentifier(value)}
                        className="inline-flex items-center rounded p-0.5 text-slate-500 hover:bg-slate-800 hover:text-amber-300 transition"
                        title={`Copy ${label}`}
                        aria-label={`Copy ${label}`}
                      >
                        {isCopied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                      </button>
                      {isCopied && <span className="text-emerald-400">Copied</span>}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Tabs - Modern Segmented Control (Zero Horizontal Scroll) */}
        <div className="px-6 py-2.5 border-b border-slate-800 bg-slate-950/70 shrink-0">
          <nav className="grid grid-cols-3 sm:grid-cols-6 gap-1 p-1 bg-slate-900/90 border border-slate-800/90 rounded-xl" aria-label="Job details tabs">
            {/* 1. Job Brief */}
            <button
              type="button"
              onClick={() => setActiveTab('jd')}
              title="Tactical Match Brief & Job Description"
              className={`flex items-center justify-center gap-1.5 py-2 px-1.5 text-[11px] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'jd'
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
              }`}
            >
              <FileText className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'jd' ? 'text-amber-400' : 'text-slate-400'}`} />
              <span className="whitespace-nowrap">Job Brief</span>
            </button>

            {/* 2. Company & Team Recon */}
            <button
              type="button"
              onClick={() => setActiveTab('recon')}
              title="Company Business Model & Team Intelligence Recon"
              className={`flex items-center justify-center gap-1.5 py-2 px-1.5 text-[11px] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'recon'
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
              }`}
            >
              <Building2 className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'recon' ? 'text-amber-400' : 'text-slate-400'}`} />
              <span className="whitespace-nowrap">Company Recon</span>
              {parsedRecon ? (
                <span className="px-1 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/80 shrink-0">
                  Active
                </span>
              ) : (
                <span className="px-1 py-0.5 rounded text-[9px] font-mono bg-slate-800 text-slate-500 border border-slate-700/60 shrink-0">
                  Ready
                </span>
              )}
            </button>

            {/* 3. Gatekeeper & Outreach */}
            <button
              type="button"
              onClick={() => setActiveTab('contacts')}
              title="Gatekeeper Recon & Cold Outreach Launchpad"
              className={`flex items-center justify-center gap-1.5 py-2 px-1.5 text-[11px] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'contacts'
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
              }`}
            >
              <UserCheck className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'contacts' ? 'text-blue-400' : 'text-slate-400'}`} />
              <span className="whitespace-nowrap">Gatekeepers</span>
              <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700 shrink-0">
                {activeJob?.contacts?.length || 0}
              </span>
            </button>

            {/* 4. Tailored Resume */}
            <button
              type="button"
              onClick={() => setActiveTab('resume')}
              title="Typst Tailored ATS Resume"
              className={`flex items-center justify-center gap-1.5 py-2 px-1.5 text-[11px] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'resume'
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
              }`}
            >
              <FileCheck className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'resume' ? 'text-emerald-400' : 'text-slate-400'}`} />
              <span className="whitespace-nowrap">Resume</span>
              {documentsInfo?.resume?.available ? (
                <span className="px-1 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/80 shrink-0">
                  {documentsInfo.resume.latest_version}
                </span>
              ) : (
                <span className="px-1 py-0.5 rounded text-[9px] font-mono bg-slate-800/80 text-slate-500 border border-slate-700/50 shrink-0">
                  None
                </span>
              )}
            </button>

            {/* 5. Tailored Cover Letter */}
            <button
              type="button"
              onClick={() => setActiveTab('cover_letter')}
              title="Sepia De-AI Problem-First Cover Letter"
              className={`flex items-center justify-center gap-1.5 py-2 px-1.5 text-[11px] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'cover_letter'
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
              }`}
            >
              <Mail className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'cover_letter' ? 'text-indigo-400' : 'text-slate-400'}`} />
              <span className="whitespace-nowrap">Cover Letter</span>
              {documentsInfo?.cover_letter?.available ? (
                <span className="px-1 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/80 shrink-0">
                  {documentsInfo.cover_letter.latest_version}
                </span>
              ) : (
                <span className="px-1 py-0.5 rounded text-[9px] font-mono bg-slate-800/80 text-slate-500 border border-slate-700/50 shrink-0">
                  None
                </span>
              )}
            </button>

            {/* 6. Timeline Events */}
            <button
              type="button"
              onClick={() => setActiveTab('timeline')}
              title="Application Stage Event History"
              className={`flex items-center justify-center gap-1.5 py-2 px-1.5 text-[11px] xl:text-xs font-semibold rounded-lg transition-all select-none cursor-pointer ${
                activeTab === 'timeline'
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-950/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
              }`}
            >
              <Clock className={`h-3.5 w-3.5 shrink-0 ${activeTab === 'timeline' ? 'text-amber-400' : 'text-slate-400'}`} />
              <span className="whitespace-nowrap">Timeline</span>
              <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700 shrink-0">
                {job?.timeline?.length || 0}
              </span>
            </button>
          </nav>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {isLoading || !job ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500"></div>
            </div>
          ) : activeTab === 'jd' ? (
            <div className="space-y-6">
              {(activeJob?.suitability_reason || parsedAnalysis) && (
                <div className="bg-amber-950/20 border border-amber-800/40 rounded-xl p-5 space-y-4 shadow-lg">
                  <div className="flex items-center justify-between border-b border-amber-900/40 pb-3">
                    <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Sparkles className="h-4 w-4" />
                      Tactical Match Brief
                    </h4>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleRematch}
                        disabled={isRematching}
                        className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-slate-900 hover:bg-slate-800 text-amber-300 font-medium rounded-lg transition border border-amber-800/40 disabled:opacity-50 cursor-pointer shadow-sm"
                        title="Re-run Match Analysis with V2 Tactical Brief"
                      >
                        <RefreshCw className={`h-3 w-3 ${isRematching ? 'animate-spin text-amber-400' : ''}`} />
                        <span>{isRematching ? 'Re-matching...' : 'Rematch Analysis'}</span>
                      </button>
                      {parsedAnalysis?.triage ? (
                        <span className={`text-xs font-bold px-2.5 py-1 rounded-full border flex items-center gap-1.5 ${
                          parsedAnalysis.triage.decision === 'STRONG_KNOCK'
                            ? 'bg-emerald-950/80 text-emerald-400 border-emerald-700/70'
                            : parsedAnalysis.triage.decision === 'SELECTIVE_APPLY'
                            ? 'bg-amber-950/80 text-amber-400 border-amber-700/70'
                            : parsedAnalysis.triage.decision === 'HIGH_RISK_LOW_ROI'
                            ? 'bg-rose-950/80 text-rose-400 border-rose-800/70'
                            : 'bg-slate-900 text-slate-400 border-slate-700'
                        }`}>
                          <span>{parsedAnalysis.triage.decision === 'STRONG_KNOCK' ? '🎯' : parsedAnalysis.triage.decision === 'SELECTIVE_APPLY' ? '⚡' : parsedAnalysis.triage.decision === 'HIGH_RISK_LOW_ROI' ? '⚠️' : '⛔'}</span>
                          <span>{parsedAnalysis.triage.decision.replace(/_/g, ' ')}</span>
                        </span>
                      ) : activeJob?.suitability_score !== undefined && activeJob?.suitability_score !== null && (
                        <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-900 text-slate-300 border border-slate-700 flex items-center gap-1.5">
                          <span>{activeJob.suitability_score >= 90 ? '🎯' : activeJob.suitability_score >= 75 ? '⚡' : '⚠️'}</span>
                          <span>{activeJob.suitability_score >= 90 ? 'STRONG KNOCK' : activeJob.suitability_score >= 75 ? 'SELECTIVE APPLY' : 'HIGH RISK'}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {parsedAnalysis?.triage ? (
                    <div className="space-y-3.5">
                      {/* Card 1: Strategic Rationale & Dealbreaker Audit */}
                      <div className="bg-slate-950/70 p-3.5 rounded-xl border border-slate-800/80 space-y-2">
                        <div className="text-xs text-slate-200 leading-relaxed font-sans">
                          <span className="font-bold text-amber-400">Strategic Rationale: </span>
                          {parsedAnalysis.triage.strategic_thesis}
                        </div>
                        <div className="text-[11px] text-slate-400 pt-1.5 border-t border-slate-800/80 flex items-center justify-between">
                          <span>Dealbreaker Audit:</span>
                          {(() => {
                            const detected = (parsedAnalysis.triage.dealbreakers_detected || []).filter(
                              (d) => d && d.trim().toLowerCase() !== 'none' && d.trim().toLowerCase() !== 'none detected'
                            );
                            if (detected.length > 0) {
                              return (
                                <span className="text-rose-400 font-semibold flex items-center gap-1">
                                  <span>⚠️</span>
                                  <span>{detected.join(', ')}</span>
                                </span>
                              );
                            }
                            return <span className="text-emerald-400 font-medium">✓ None detected</span>;
                          })()}
                        </div>
                      </div>

                      {/* Card 2: Acute Employer Bottlenecks & Day-1 Antidote */}
                      {parsedAnalysis.employer_mandate && (
                        <div className="bg-slate-950/70 p-3.5 rounded-xl border border-slate-800/80 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                              <Target className="h-3.5 w-3.5 text-amber-500" />
                              Acute Employer Bottlenecks
                            </span>
                            {parsedAnalysis.employer_mandate.role_archetype && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                                Role: {parsedAnalysis.employer_mandate.role_archetype}
                              </span>
                            )}
                          </div>
                          {parsedAnalysis.employer_mandate.acute_operational_frictions?.length > 0 && (
                            <ul className="space-y-1.5">
                              {parsedAnalysis.employer_mandate.acute_operational_frictions.map((pt, i) => (
                                <li key={i} className="text-xs text-slate-300 flex items-start gap-2 bg-slate-900/60 p-2 rounded-md border border-slate-800">
                                  <span className="text-amber-500 font-bold">🔥</span>
                                  <span>{pt}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                          {parsedAnalysis.employer_mandate.immediate_value_hook && (
                            <div className="text-xs text-slate-300 bg-amber-950/20 p-2.5 rounded-lg border border-amber-900/30">
                              <span className="text-amber-300 font-bold">Day-1 Antidote: </span>
                              {parsedAnalysis.employer_mandate.immediate_value_hook}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Card 3: Gaps & Strategic Defense */}
                      {parsedAnalysis.gaps_and_mitigation && parsedAnalysis.gaps_and_mitigation.length > 0 && (
                        <div className="bg-slate-950/70 p-3.5 rounded-xl border border-slate-800/80 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                              <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                              Identified Gaps & Strategic Defense
                            </span>
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                              Risk Audit
                            </span>
                          </div>
                          <div className="space-y-1.5">
                            {parsedAnalysis.gaps_and_mitigation.map((g, i) => (
                              <div key={i} className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800 text-xs space-y-1">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-amber-400 flex items-center gap-1">
                                    <span>▲ Gap:</span> <span>{g.gap}</span>
                                  </span>
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">{g.severity}</span>
                                </div>
                                <div className="text-slate-300 text-[11px] bg-slate-950/60 p-2 rounded border border-slate-800/80 leading-relaxed">
                                  <span className="text-emerald-400 font-semibold">🛡️ Defense: </span>
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
                          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-center">
                            <div className="text-[11px] text-slate-400 uppercase font-medium">Technical Fit</div>
                            <div className="text-lg font-bold text-emerald-400 mt-0.5">
                              {parsedAnalysis.technical_fit_score ? `${Math.round(parsedAnalysis.technical_fit_score)}%` : 'N/A'}
                            </div>
                          </div>
                          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-center">
                            <div className="text-[11px] text-slate-400 uppercase font-medium">Domain Fit</div>
                            <div className="text-lg font-bold text-blue-400 mt-0.5">
                              {parsedAnalysis.domain_fit_score ? `${Math.round(parsedAnalysis.domain_fit_score)}%` : 'N/A'}
                            </div>
                          </div>
                          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-center">
                            <div className="text-[11px] text-slate-400 uppercase font-medium">Work Auth / Eligibility</div>
                            <div className="text-lg font-bold text-amber-400 mt-0.5">
                              {parsedAnalysis.eligibility_fit_score ? `${Math.round(parsedAnalysis.eligibility_fit_score)}%` : 'N/A'}
                            </div>
                          </div>
                        </div>
                      )}

                      {(job.suitability_reason || parsedAnalysis?.suitability_reason) && (
                        <div>
                          <p className="text-xs text-slate-300 leading-relaxed font-sans">
                            {job.suitability_reason || parsedAnalysis?.suitability_reason}
                          </p>
                        </div>
                      )}

                      {parsedAnalysis?.employer_pain_points && parsedAnalysis.employer_pain_points.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-amber-900/30">
                          <div className="text-[11px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                            <Target className="h-3.5 w-3.5 text-amber-500" />
                            Target Employer Pain Points (DoorKnock Hooks)
                          </div>
                          <ul className="space-y-1.5">
                            {parsedAnalysis.employer_pain_points.map((pt, i) => (
                              <li key={i} className="text-xs text-slate-300 flex items-start gap-2 bg-slate-950/40 p-2 rounded-md border border-amber-950/50">
                                <span className="text-amber-500 font-bold">•</span>
                                <span>{pt}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {parsedAnalysis?.key_strengths && parsedAnalysis.key_strengths.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-amber-900/30">
                          <div className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                            Candidate Evidence Highlights
                          </div>
                          <ul className="space-y-1.5">
                            {parsedAnalysis.key_strengths.map((str, i) => (
                              <li key={i} className="text-xs text-slate-300 flex items-start gap-2 bg-slate-950/40 p-2 rounded-md border border-emerald-950/50">
                                <span className="text-emerald-500 font-bold">✓</span>
                                <span>{str}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {parsedAnalysis?.gaps_or_risks && parsedAnalysis.gaps_or_risks.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-amber-900/30">
                          <div className="text-[11px] font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                            <AlertTriangle className="h-3.5 w-3.5 text-rose-500" />
                            Identified Gaps & Interview Risks
                          </div>
                          <ul className="space-y-1.5">
                            {parsedAnalysis.gaps_or_risks.map((gap, i) => (
                              <li key={i} className="text-xs text-slate-300 flex items-start gap-2 bg-slate-950/40 p-2 rounded-md border border-rose-950/50">
                                <span className="text-rose-500 font-bold">!</span>
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
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                    Executive Brief
                  </h4>
                  <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                    {job.job_brief}
                  </p>
                </div>
              )}

              <div>
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                  Full Job Description
                </h4>
                <div className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed bg-slate-950/80 p-5 rounded-xl border border-slate-800 max-h-96 overflow-y-auto select-text font-mono">
                  {job.job_description || 'No job description text available.'}
                </div>
              </div>
            </div>
          ) : activeTab === 'recon' ? (
            <div className="space-y-6">
              {/* Recon Header & Action Bar */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-md">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                    <Building2 className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>Company & Department Recon Intelligence</span>
                      {parsedRecon && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                          Verified
                        </span>
                      )}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Strategic business model, department charter, and direct supervisor pain points.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleRunRecon}
                    disabled={isReconning}
                    className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/40 transition shadow-sm disabled:opacity-50 cursor-pointer"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${isReconning ? 'animate-spin text-amber-400' : ''}`} />
                    <span>{isReconning ? 'Executing Recon...' : parsedRecon ? 'Re-run Recon' : 'Run Recon Now'}</span>
                  </button>
                </div>
              </div>

              {!parsedRecon ? (
                <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl space-y-3 bg-slate-950/40">
                  <Building2 className="h-10 w-10 text-slate-600 mx-auto" />
                  <div>
                    <p className="text-sm font-semibold text-slate-300">No company reconnaissance performed yet.</p>
                    <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                      Analyze employer monetization, macro headwinds, target department charter, and hiring manager anxieties to power high-conversion outreach.
                    </p>
                  </div>
                  <button
                    onClick={handleRunRecon}
                    disabled={isReconning}
                    className="px-4 py-2 text-xs font-bold rounded-xl bg-amber-600 hover:bg-amber-500 text-white transition shadow-lg shadow-amber-950/50 inline-flex items-center gap-2"
                  >
                    <Sparkles className="h-4 w-4" />
                    <span>Run Strategic Recon Now</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Meta badges */}
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                    <span className="font-semibold text-slate-200">{parsedRecon.company_name}</span>
                    {parsedRecon.company_stage?.funding_or_tier && (
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {parsedRecon.company_stage.funding_or_tier}
                      </span>
                    )}
                    {parsedRecon.company_stage?.market_standing && (
                      <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
                        {parsedRecon.company_stage.market_standing}
                      </span>
                    )}
                    {parsedRecon.researched_at && (
                      <span className="text-slate-500 text-[11px] font-mono ml-auto">
                        Analyzed: {formatDateTime(parsedRecon.researched_at, settings.timezone)}
                      </span>
                    )}
                  </div>

                  {/* 2-Column Core Intelligence Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Card 1: Business Model & Revenue Engine */}
                    <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                          <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                            <DollarSign className="h-4 w-4 text-amber-500" />
                            Business Model & Revenue Engine
                          </span>
                        </div>

                        {parsedRecon.business_model?.revenue_engine && (
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Monetization Engine</span>
                            <p className="text-xs text-slate-200 mt-0.5 leading-relaxed">{parsedRecon.business_model.revenue_engine}</p>
                          </div>
                        )}

                        {parsedRecon.business_model?.target_customers && (
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Target Customers</span>
                            <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">{parsedRecon.business_model.target_customers}</p>
                          </div>
                        )}

                        {parsedRecon.business_model?.value_proposition && (
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Value Proposition & Moat</span>
                            <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">{parsedRecon.business_model.value_proposition}</p>
                          </div>
                        )}

                        {parsedRecon.business_model?.macro_challenges && (
                          <div className="bg-amber-950/20 p-3 rounded-lg border border-amber-900/40 text-xs text-amber-200/90 leading-relaxed">
                            <span className="font-bold text-amber-300 block mb-1">⚠️ Macro Bottlenecks & Friction:</span>
                            {parsedRecon.business_model.macro_challenges}
                          </div>
                        )}
                      </div>

                      {parsedRecon.company_stage?.scale_and_momentum && (
                        <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400">
                          <span className="font-medium text-slate-300">Scale & Momentum: </span>
                          {parsedRecon.company_stage.scale_and_momentum}
                        </div>
                      )}
                    </div>

                    {/* Card 2: Department Charter & Direct Supervisor */}
                    <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                          <span className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                            <Briefcase className="h-4 w-4 text-blue-500" />
                            Department Charter & Supervisor Pressure
                          </span>
                          {parsedRecon.department_intel?.role_archetype && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                              {parsedRecon.department_intel.role_archetype}
                            </span>
                          )}
                        </div>

                        {parsedRecon.department_intel?.team_name && (
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Target Team / Unit</span>
                            <p className="text-xs font-mono font-semibold text-blue-200 mt-0.5">{parsedRecon.department_intel.team_name}</p>
                          </div>
                        )}

                        {parsedRecon.department_intel?.team_charter && (
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Department Mission</span>
                            <p className="text-xs text-slate-200 mt-0.5 leading-relaxed">{parsedRecon.department_intel.team_charter}</p>
                          </div>
                        )}

                        {parsedRecon.department_intel?.hiring_manager_profile && (
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Deduced Direct Supervisor</span>
                            <p className="text-xs text-slate-300 mt-0.5 font-medium">{parsedRecon.department_intel.hiring_manager_profile}</p>
                          </div>
                        )}

                        {parsedRecon.department_intel?.manager_core_pressure && (
                          <div className="bg-blue-950/20 p-3 rounded-lg border border-blue-900/40 text-xs text-blue-200/90 leading-relaxed">
                            <span className="font-bold text-blue-300 block mb-1">🔥 Direct Supervisor Core Anxiety:</span>
                            {parsedRecon.department_intel.manager_core_pressure}
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
                        <span>Injected into Knock Outreach</span>
                        <span className="text-emerald-400 font-semibold">Active Fuel</span>
                      </div>
                    </div>
                  </div>

                  {/* Strategic Alignment Card */}
                  {parsedRecon.strategic_positioning_for_candidate && (
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                      <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                        <Target className="h-4 w-4 text-emerald-400" />
                        Downstream Document & Outreach Alignment
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        {parsedRecon.strategic_positioning_for_candidate.tailor_summary_angle && (
                          <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-800 space-y-1">
                            <span className="text-emerald-400 font-semibold block text-[11px]">📄 Tailor Summary Angle:</span>
                            <p className="text-slate-300 leading-relaxed">{parsedRecon.strategic_positioning_for_candidate.tailor_summary_angle}</p>
                          </div>
                        )}
                        {parsedRecon.strategic_positioning_for_candidate.cover_letter_hook_angle && (
                          <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-800 space-y-1">
                            <span className="text-amber-400 font-semibold block text-[11px]">✉️ Cover Letter Problem-First Hook:</span>
                            <p className="text-slate-300 leading-relaxed">{parsedRecon.strategic_positioning_for_candidate.cover_letter_hook_angle}</p>
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
              <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-slate-800">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <UserCheck className="h-4 w-4 text-blue-400" />
                    <span>Gatekeeper Recon & Outreach Console</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Target decision-makers at {job.company} with tailored Sepia-compliant outreach drafts.
                  </p>
                </div>

                <button
                  onClick={() => setShowAddContact(!showAddContact)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition shadow-sm"
                >
                  <UserPlus className="h-3.5 w-3.5" />
                  <span>{showAddContact ? 'Cancel' : 'Add Gatekeeper'}</span>
                </button>
              </div>

              {/* Agent Command Banner */}
              <div className="bg-gradient-to-r from-blue-950/40 via-slate-900 to-slate-950 p-4 rounded-xl border border-blue-500/30 space-y-2.5 shadow-md">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-blue-400 flex items-center gap-1.5">
                      <Sparkles className="h-4 w-4 text-blue-400" />
                      AI Agent Recon Instructions (LinkedIn MCP)
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30">
                      doorknock-scout
                    </span>
                  </div>
                  <button
                    onClick={handleCopyAgentCommand}
                    className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-200 border border-blue-500/40 transition"
                  >
                    {copiedAgentCmd ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>{copiedAgentCmd ? 'Command Copied!' : 'Copy Agent Command'}</span>
                  </button>
                </div>
                <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800 flex items-center justify-between gap-3 text-xs font-mono text-slate-300 select-text">
                  <span className="text-amber-300 truncate">{`scout gatekeepers for job ${activeJob?.id} (${activeJob?.company} - ${activeJob?.title})`}</span>
                  <span className="text-[10px] text-slate-500 font-sans shrink-0">Paste into Antigravity or Codex CLI</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  💡 The AI Agent invokes <code className="text-slate-300">linkedin-mcp-server</code> safely, discovers Hiring Manager / Recruiter / Peer, and has full authority to rewrite/update the DoorKnock DB via <code className="text-slate-300">POST /api/jobs/{'{job_id}'}/contacts</code>.
                </p>
              </div>

              {/* Add Contact Inline Form */}
              {showAddContact && (
                <form onSubmit={handleAddContactSubmit} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 animate-fadeIn">
                  <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">New Gatekeeper Record</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div>
                      <label className="text-slate-400 block mb-1">Full Name *</label>
                      <input
                        type="text"
                        required
                        value={newContact.name}
                        onChange={(e) => setNewContact({ ...newContact, name: e.target.value })}
                        placeholder="e.g. Alex Kowalski"
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-100 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Role Title *</label>
                      <input
                        type="text"
                        required
                        value={newContact.role_title}
                        onChange={(e) => setNewContact({ ...newContact, role_title: e.target.value })}
                        placeholder="e.g. Head of Engineering"
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-100 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Contact Type</label>
                      <select
                        value={newContact.contact_type}
                        onChange={(e) => setNewContact({ ...newContact, contact_type: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-100 focus:outline-none focus:border-blue-500"
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
                      <label className="text-slate-400 block mb-1">LinkedIn Profile URL</label>
                      <input
                        type="url"
                        value={newContact.linkedin_url}
                        onChange={(e) => setNewContact({ ...newContact, linkedin_url: e.target.value })}
                        placeholder="https://linkedin.com/in/..."
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-100 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Email (Optional)</label>
                      <input
                        type="email"
                        value={newContact.email}
                        onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
                        placeholder="alex@company.com"
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-100 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowAddContact(false)}
                      className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isAddingContact}
                      className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition disabled:opacity-50"
                    >
                      {isAddingContact ? 'Saving...' : 'Save Gatekeeper'}
                    </button>
                  </div>
                </form>
              )}

              {/* Contacts List & Outreach Decks */}
              {(!activeJob?.contacts || activeJob.contacts.length === 0) ? (
                <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl space-y-3 bg-slate-950/40">
                  <UserCheck className="h-10 w-10 text-slate-600 mx-auto" />
                  <div>
                    <p className="text-sm font-semibold text-slate-300">No gatekeepers recorded yet for this position.</p>
                    <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                      Add the Hiring Manager, Recruiter, or Peer from LinkedIn to generate tailored outreach drafts.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowAddContact(true)}
                    className="px-4 py-2 text-xs font-bold rounded-xl bg-blue-600 hover:bg-blue-500 text-white transition shadow-lg shadow-blue-950/50 inline-flex items-center gap-2"
                  >
                    <UserPlus className="h-4 w-4" />
                    <span>Add First Gatekeeper</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  {activeJob.contacts.map((contact) => (
                    <div key={contact.id} className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden shadow-lg">
                      {/* Gatekeeper Card Header */}
                      <div className="p-4 bg-slate-900/70 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-white">{contact.name}</span>
                            <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-slate-800 text-amber-300 border border-slate-700">
                              {contact.contact_type.replace('_', ' ')}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">{contact.role_title}</p>
                          <div className="flex items-center gap-3 text-xs text-slate-500 pt-0.5">
                            {contact.linkedin_url && (
                              <a
                                href={contact.linkedin_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-blue-400 hover:underline flex items-center gap-1"
                              >
                                LinkedIn Profile <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                            {contact.email && (
                              <span className="text-slate-400 flex items-center gap-1 font-mono text-[11px]">
                                <Mail className="h-3 w-3 text-slate-500" /> {contact.email}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleGenerateOutreach(contact.id)}
                            disabled={generatingOutreach[contact.id]}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 transition shadow-sm disabled:opacity-50 cursor-pointer"
                            title="Generate Sepia De-AI outreach drafts"
                          >
                            <Sparkles className={`h-3.5 w-3.5 ${generatingOutreach[contact.id] ? 'animate-spin' : ''}`} />
                            <span>{generatingOutreach[contact.id] ? 'Generating Drafts...' : (contact.messages && contact.messages.length > 0) ? 'Regenerate Drafts' : 'Generate Outreach Drafts'}</span>
                          </button>

                          <button
                            onClick={() => handleDeleteContact(contact.id)}
                            className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-950/40 border border-transparent hover:border-red-900/50 rounded-lg transition"
                            title="Delete gatekeeper and drafts from DB"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Outreach Messages List */}
                      <div className="p-4 space-y-4">
                        {(!contact.messages || contact.messages.length === 0) ? (
                          <div className="text-center py-6 text-slate-500 text-xs">
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
                                <div key={msg.id} className="bg-slate-900/80 rounded-xl border border-slate-800 p-4 flex flex-col justify-between space-y-3">
                                  <div className="space-y-2">
                                    <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                                      <div>
                                        <span className="text-xs font-bold text-white capitalize">
                                          {isConnect ? 'LinkedIn Connection Note' : 'InMail / Cold Email'}
                                        </span>
                                        <span className="text-[10px] text-slate-400 block mt-0.5">
                                          {isConnect ? 'Strictly ≤ 300 characters' : '80–120 words (Problem-First)'}
                                        </span>
                                      </div>
                                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                                        isConnect
                                          ? (charCount <= 300 ? 'bg-slate-950 text-emerald-400 border-slate-800' : 'bg-red-950 text-red-400 border-red-800')
                                          : 'bg-slate-950 text-blue-400 border-slate-800'
                                      }`}>
                                        {isConnect ? `${charCount}/300 chars` : `${wordCount} words`}
                                      </span>
                                    </div>

                                    {msg.subject && (
                                      <div className="text-xs font-mono text-slate-300 bg-slate-950 px-2.5 py-1.5 rounded border border-slate-800/80">
                                        <span className="text-slate-500">Subject: </span>{msg.subject}
                                      </div>
                                    )}

                                    <div className="text-xs text-slate-200 font-sans leading-relaxed whitespace-pre-wrap select-text bg-slate-950/70 p-3 rounded-lg border border-slate-800/60 max-h-56 overflow-y-auto">
                                      {msg.body}
                                    </div>
                                  </div>

                                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-1.5 text-xs">
                                      <span className="text-slate-500 text-[11px]">Status:</span>
                                      <select
                                        value={msg.status}
                                        onChange={(e) => handleUpdateMessageStatus(msg.id, e.target.value)}
                                        className="bg-slate-950 border border-slate-700 text-slate-300 text-[11px] rounded px-2 py-0.5 focus:outline-none focus:border-amber-500"
                                      >
                                        <option value="draft">Draft</option>
                                        <option value="ready_to_send">Ready to Send</option>
                                        <option value="sent">Sent</option>
                                        <option value="replied">Replied</option>
                                        <option value="ignored">Ignored</option>
                                      </select>
                                      {msg.sent_at && (
                                        <span className="text-[10px] text-emerald-400">✓ Sent</span>
                                      )}
                                    </div>

                                    <button
                                      onClick={() => handleCopyMessage(msg.id, msg.body)}
                                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition ${
                                        isCopied
                                          ? 'bg-emerald-600 text-white'
                                          : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
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
              {(!job.timeline || job.timeline.length === 0) ? (
                <div className="text-center py-10 border border-dashed border-slate-800 rounded-xl">
                  <Clock className="h-10 w-10 text-slate-600 mx-auto mb-2" />
                  <p className="text-sm text-slate-400">No timeline events recorded yet.</p>
                </div>
              ) : (
                <div className="relative border-l border-slate-800 ml-4 space-y-6">
                  {job.timeline.map((event) => (
                    <div key={event.id} className="relative pl-6">
                      <div className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full bg-amber-500 border-2 border-slate-900"></div>
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span className="font-semibold text-slate-200">{event.title}</span>
                        <span title={formatDateTime(event.occurred_at, settings.timezone)}>
                          {formatDate(event.occurred_at, settings.timezone)}
                          {hasUnknownTimeZone(event.occurred_at) && ' · time zone not recorded'}
                        </span>
                      </div>
                      {event.description && (
                        <p className="text-xs text-slate-400 mt-1">{event.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div>
            {job && onDeleteJob && (
              confirmDelete ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-red-400 font-medium">Confirm delete?</span>
                  <button
                    onClick={() => { onDeleteJob(job.id); setConfirmDelete(false); }}
                    className="px-3 py-1 text-xs font-semibold bg-red-600 hover:bg-red-500 text-white rounded-lg transition shadow-md shadow-red-950/50"
                  >
                    Yes, Delete
                  </button>
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="px-2 py-1 text-xs text-slate-400 hover:text-white transition"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-red-950/40 border border-red-900/50 rounded-lg transition"
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
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-lg transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
