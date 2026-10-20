import React, { useState, useEffect, useCallback } from 'react';
import {
  X,
  Sparkles,
  Building2,
  MapPin,
  DollarSign,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  ShieldAlert,
  Globe,
  DownloadCloud,
  Edit3,
  Check,
  FilePlus,
} from 'lucide-react';
import type { JobAnalysisResult } from '../types';

interface ImportJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onJobImported: () => void;
}

export const ImportJobModal: React.FC<ImportJobModalProps> = ({
  isOpen,
  onClose,
  onJobImported,
}) => {
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [isFetchingUrl, setIsFetchingUrl] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<JobAnalysisResult | null>(null);

  // Metadata editing in analysis result view
  const [isEditingMeta, setIsEditingMeta] = useState(false);
  const [editedMeta, setEditedMeta] = useState({
    title: '',
    company: '',
    company_url: '',
    location: '',
    workplace_type: 'onsite',
    salary_min: '' as string | number,
    salary_max: '' as string | number,
    salary_currency: 'USD',
    salary_interval: 'year',
  });

  // Direct manual import (skip AI)
  const [showDirectImport, setShowDirectImport] = useState(false);
  const [directTitle, setDirectTitle] = useState('');
  const [directCompany, setDirectCompany] = useState('');
  const [directLocation, setDirectLocation] = useState('');
  const [directWorkplace, setDirectWorkplace] = useState('onsite');

  const resetForm = useCallback(() => {
    setUrlInput('');
    setTextInput('');
    setIsFetchingUrl(false);
    setIsAnalyzing(false);
    setIsSaving(false);
    setErrorMsg(null);
    setSuccessMsg(null);
    setAnalysis(null);
    setIsEditingMeta(false);
    setShowDirectImport(false);
    setDirectTitle('');
    setDirectCompany('');
    setDirectLocation('');
    setDirectWorkplace('onsite');
    setEditedMeta({
      title: '',
      company: '',
      company_url: '',
      location: '',
      workplace_type: 'onsite',
      salary_min: '',
      salary_max: '',
      salary_currency: 'USD',
      salary_interval: 'year',
    });
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onClose();
  }, [resetForm, onClose]);

  // Handle keyboard Escape key to close
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleClose]);

  if (!isOpen) return null;

  const handleFetchUrl = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);

    if (!urlInput.trim().startsWith('http')) {
      setErrorMsg('Please enter a valid URL starting with http:// or https://');
      return;
    }

    try {
      setIsFetchingUrl(true);
      const res = await fetch('/api/jobs/fetch-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || 'Failed to fetch webpage text.');
      } else {
        setTextInput(data.text);
        const method = data.extraction_method ? ` using ${data.extraction_method}` : '';
        setSuccessMsg(`Fetched ${data.text.length} characters${method}. Review or edit the job description below.`);
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Error connecting to URL fetcher.');
    } finally {
      setIsFetchingUrl(false);
    }
  };

  const handleAnalyze = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setAnalysis(null);

    if (textInput.trim().length < 30) {
      setErrorMsg('Job description is too short. Please paste JD text or use the "Fetch JD" button above.');
      return;
    }

    try {
      setIsAnalyzing(true);
      const res = await fetch('/api/jobs/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textInput.trim(),
          url: urlInput.trim() || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || 'Failed to analyze job posting.');
      } else {
        setAnalysis(data);
        setEditedMeta({
          title: data.title || '',
          company: data.company || '',
          company_url: data.company_url || '',
          location: data.location || '',
          workplace_type: data.workplace_type || 'onsite',
          salary_min: data.salary_min ?? '',
          salary_max: data.salary_max ?? '',
          salary_currency: data.salary_currency || 'USD',
          salary_interval: data.salary_interval || 'year',
        });
        setIsEditingMeta(false);
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Error communicating with analysis service.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSaveToDoorKnock = async () => {
    if (!analysis) return;
    try {
      setIsSaving(true);
      setErrorMsg(null);

      const titleToSave = (editedMeta.title || analysis.title || '').trim();
      const companyToSave = (editedMeta.company || analysis.company || '').trim();

      if (!titleToSave || !companyToSave) {
        setErrorMsg('Job Title and Company Name cannot be empty.');
        setIsSaving(false);
        return;
      }

      const salaryMinVal = editedMeta.salary_min !== '' ? Number(editedMeta.salary_min) : (analysis.salary_min ?? null);
      const salaryMaxVal = editedMeta.salary_max !== '' ? Number(editedMeta.salary_max) : (analysis.salary_max ?? null);

      const payload = {
        title: titleToSave,
        company: companyToSave,
        company_url: (editedMeta.company_url || analysis.company_url || '').trim() || null,
        location: (editedMeta.location || analysis.location || '').trim() || null,
        workplace_type: editedMeta.workplace_type || analysis.workplace_type || 'onsite',
        salary_min: salaryMinVal !== null && !isNaN(salaryMinVal) ? salaryMinVal : null,
        salary_max: salaryMaxVal !== null && !isNaN(salaryMaxVal) ? salaryMaxVal : null,
        salary_currency: editedMeta.salary_currency || analysis.salary_currency || 'USD',
        salary_interval: editedMeta.salary_interval || analysis.salary_interval || 'year',
        job_url: analysis.source_url || (urlInput.trim() ? urlInput.trim() : null),
        job_description: analysis.raw_text || textInput,
        job_brief: analysis.job_brief,
        suitability_score: analysis.suitability_score,
        suitability_reason: analysis.suitability_reason,
        analysis_json: JSON.stringify({
          ...analysis,
          title: titleToSave,
          company: companyToSave,
          location: (editedMeta.location || analysis.location || '').trim() || null,
          workplace_type: editedMeta.workplace_type || analysis.workplace_type || 'onsite',
          salary_min: salaryMinVal !== null && !isNaN(salaryMinVal) ? salaryMinVal : null,
          salary_max: salaryMaxVal !== null && !isNaN(salaryMaxVal) ? salaryMaxVal : null,
          salary_interval: editedMeta.salary_interval || analysis.salary_interval || 'year',
        }),
        source: 'direct_import',
      };

      const res = await fetch('/api/jobs/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        handleClose();
        onJobImported();
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || 'Failed to save job into database.');
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Error saving job.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDirectImport = async () => {
    setErrorMsg(null);
    const title = directTitle.trim();
    const company = directCompany.trim();

    if (!title || !company) {
      setErrorMsg('Job Title and Company Name are required for direct import.');
      return;
    }

    const jdText = textInput.trim() || (urlInput.trim() ? `Imported from ${urlInput.trim()}` : `Role: ${title} at ${company}`);

    try {
      setIsSaving(true);
      setErrorMsg(null);

      const res = await fetch('/api/jobs/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          company,
          location: directLocation.trim() || null,
          workplace_type: directWorkplace || 'onsite',
          job_url: urlInput.trim() || null,
          job_description: jdText,
          job_brief: `${title} at ${company}`,
          suitability_reason: 'Directly imported without AI analysis.',
          source: 'direct_import',
        }),
      });

      if (res.ok) {
        handleClose();
        onJobImported();
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || 'Failed to directly import job into database.');
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Error saving job.');
    } finally {
      setIsSaving(false);
    }
  };

  const score = analysis?.suitability_score ? Math.round(analysis.suitability_score) : null;

  const detectedDealbreakers = (analysis?.triage?.dealbreakers_detected || []).filter(
    (d) => d && d.trim().toLowerCase() !== 'none' && d.trim().toLowerCase() !== 'none detected'
  );
  const hasDealbreakers = detectedDealbreakers.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ui-overlay/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-ui-panel border border-ui-line rounded-2xl w-full max-w-3xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-ui-line-soft bg-ui-page/80 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-ui-fill-amber-500/20 border border-ui-line-amber-500/30 flex items-center justify-center text-ui-ink-amber-400">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-ui-heading">Import & Analyze Job</h2>
              <p className="text-xs text-ui-muted">
                Provide a Job URL or paste raw JD text, then analyze fit against your Master Resume.
              </p>
            </div>
          </div>

          <button
            onClick={handleClose}
            className="text-ui-muted hover:text-ui-heading p-1.5 rounded-lg hover:bg-ui-raised transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Global Error Banner */}
        {errorMsg && (
          <div className="mx-6 mt-4 bg-ui-fill-red-950/40 border border-ui-line-red-800/60 rounded-xl p-3 flex items-start justify-between gap-2 text-xs text-ui-ink-red-300 animate-fadeIn">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-ui-ink-red-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-semibold">Notice:</span>
                <p className="text-ui-body">{errorMsg}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setErrorMsg(null)}
              className="text-ui-muted hover:text-ui-heading p-0.5 rounded transition"
              aria-label="Dismiss error"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Input Controls (Unified Single Page) */}
        {!analysis && (
          <div className="p-6 overflow-y-auto flex-1 space-y-5">
            {/* 1. Job URL & Fetch Button */}
            <div className="space-y-1.5 bg-ui-page/70 p-4 rounded-xl border border-ui-line-soft">
              <label className="text-xs font-semibold text-ui-body flex items-center gap-1.5">
                <Globe className="h-3.5 w-3.5 text-ui-ink-amber-500" />
                <span>Job Posting URL (Optional)</span>
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="https://www.linkedin.com/jobs/view/... or Greenhouse/careers page"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  className="flex-1 bg-ui-panel border border-ui-line text-ui-secondary text-xs rounded-xl px-3.5 py-2 focus:outline-none focus:border-ui-line-amber-500"
                />
                <button
                  type="button"
                  onClick={handleFetchUrl}
                  disabled={isFetchingUrl || !urlInput.trim()}
                  className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold bg-ui-raised hover:bg-ui-hover text-ui-ink-amber-400 border border-ui-line rounded-xl transition disabled:opacity-50"
                  title="Extract JD text from this webpage"
                >
                  <DownloadCloud className={`h-3.5 w-3.5 ${isFetchingUrl ? 'animate-bounce text-ui-ink-amber-400' : ''}`} />
                  <span>{isFetchingUrl ? 'Fetching...' : 'Fetch JD'}</span>
                </button>
              </div>
              <p className="text-[0.6875rem] text-ui-subtle">
                Click "Fetch JD" to automatically crawl the link and populate the description below.
              </p>
            </div>

            {/* 2. Job Description Textarea */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-ui-body">
                  Job Description Text <span className="text-ui-ink-red-400">*</span>
                </label>
                {textInput && (
                  <span className="text-[0.6875rem] text-ui-subtle">
                    {textInput.length} chars
                  </span>
                )}
              </div>
              <textarea
                rows={8}
                placeholder="Paste the full job description here (or click 'Fetch JD' above)..."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                className="w-full bg-ui-page border border-ui-line text-ui-secondary text-xs rounded-xl p-3.5 focus:outline-none focus:border-ui-line-amber-500 font-mono resize-none leading-relaxed"
              />
            </div>

            {/* Direct Import Form (Expandable) */}
            <div className="border-t border-ui-line-soft pt-3">
              <button
                type="button"
                onClick={() => setShowDirectImport(!showDirectImport)}
                className="text-xs text-ui-ink-amber-400 hover:text-ui-ink-amber-300 font-medium flex items-center gap-1.5 transition"
              >
                <FilePlus className="h-3.5 w-3.5" />
                <span>{showDirectImport ? 'Hide Direct Import Options' : 'Need to skip AI? Import directly with manual details →'}</span>
              </button>

              {showDirectImport && (
                <div className="mt-3 p-4 bg-ui-page/70 border border-ui-line-soft rounded-xl space-y-3 animate-fadeIn">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[0.6875rem] font-semibold text-ui-body block mb-1">
                        Job Title <span className="text-ui-ink-red-400">*</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Senior Software Engineer"
                        value={directTitle}
                        onChange={(e) => setDirectTitle(e.target.value)}
                        className="w-full bg-ui-panel border border-ui-line text-ui-secondary text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                      />
                    </div>
                    <div>
                      <label className="text-[0.6875rem] font-semibold text-ui-body block mb-1">
                        Company Name <span className="text-ui-ink-red-400">*</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Acme Corp"
                        value={directCompany}
                        onChange={(e) => setDirectCompany(e.target.value)}
                        className="w-full bg-ui-panel border border-ui-line text-ui-secondary text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[0.6875rem] font-semibold text-ui-body block mb-1">
                        Location (Optional)
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. San Francisco, CA or Remote"
                        value={directLocation}
                        onChange={(e) => setDirectLocation(e.target.value)}
                        className="w-full bg-ui-panel border border-ui-line text-ui-secondary text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                      />
                    </div>
                    <div>
                      <label className="text-[0.6875rem] font-semibold text-ui-body block mb-1">
                        Workplace Type
                      </label>
                      <select
                        value={directWorkplace}
                        onChange={(e) => setDirectWorkplace(e.target.value)}
                        className="w-full bg-ui-panel border border-ui-line text-ui-secondary text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                      >
                        <option value="onsite">Onsite</option>
                        <option value="hybrid">Hybrid</option>
                        <option value="remote">Remote</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex justify-end pt-1">
                    <button
                      type="button"
                      onClick={handleDirectImport}
                      disabled={isSaving || !directTitle.trim() || !directCompany.trim()}
                      className="px-3.5 py-1.5 text-xs font-semibold bg-ui-raised hover:bg-ui-hover text-ui-secondary border border-ui-line rounded-lg transition disabled:opacity-50 flex items-center gap-1.5"
                    >
                      <Check className="h-3.5 w-3.5 text-ui-ink-emerald-400" />
                      <span>{isSaving ? 'Importing...' : 'Save Job Directly'}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Success Feedback */}
            {successMsg && (
              <div className="bg-ui-fill-emerald-950/40 border border-ui-line-emerald-800/60 rounded-xl p-2.5 flex items-center gap-2 text-xs text-ui-ink-emerald-300">
                <CheckCircle2 className="h-4 w-4 text-ui-ink-emerald-400 flex-shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}
          </div>
        )}

        {/* Analysis Results View */}
        {analysis && (
          <div className="p-6 overflow-y-auto flex-1 space-y-5">
            {/* Header Card with Editable Metadata */}
            <div className="bg-ui-page p-4 rounded-xl border border-ui-line-soft flex flex-col gap-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  {!isEditingMeta ? (
                    <div>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-ui-muted mb-1">
                        <Building2 className="h-3.5 w-3.5 text-ui-ink-amber-500" />
                        <span className="font-semibold text-ui-secondary">{editedMeta.company || analysis.company}</span>
                        {(editedMeta.location || analysis.location) && (
                          <span className="flex items-center gap-1">
                            • <MapPin className="h-3 w-3" /> {editedMeta.location || analysis.location}
                          </span>
                        )}
                        {(editedMeta.workplace_type || analysis.workplace_type) && (
                          <span className="capitalize px-1.5 py-0.5 bg-ui-raised rounded text-[0.6875rem]">
                            {editedMeta.workplace_type || analysis.workplace_type}
                          </span>
                        )}
                      </div>

                      <h3 className="text-lg font-bold text-ui-heading">{editedMeta.title || analysis.title}</h3>

                      {(editedMeta.salary_min || analysis.salary_min) && (
                        <p className="text-xs text-ui-ink-amber-400 font-medium mt-1 flex items-center gap-1">
                          <DollarSign className="h-3 w-3" />
                          ${Number(editedMeta.salary_min || analysis.salary_min).toLocaleString()}
                          {(editedMeta.salary_max || analysis.salary_max)
                            ? ` - $${Number(editedMeta.salary_max || analysis.salary_max).toLocaleString()}`
                            : ''}
                          /{editedMeta.salary_interval || analysis.salary_interval || 'yr'}
                        </p>
                      )}
                    </div>
                  ) : (
                    /* Inline Metadata Edit Form */
                    <div className="space-y-3 bg-ui-panel/90 p-3.5 rounded-xl border border-ui-line">
                      <div className="text-xs font-bold text-ui-ink-amber-400 flex items-center gap-1.5 mb-1">
                        <Edit3 className="h-3.5 w-3.5" />
                        <span>Edit Extracted Job Metadata</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        <div>
                          <label className="text-[0.6875rem] text-ui-muted block mb-1">Job Title</label>
                          <input
                            type="text"
                            value={editedMeta.title}
                            onChange={(e) => setEditedMeta({ ...editedMeta, title: e.target.value })}
                            className="w-full bg-ui-page border border-ui-line text-ui-secondary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                          />
                        </div>
                        <div>
                          <label className="text-[0.6875rem] text-ui-muted block mb-1">Company</label>
                          <input
                            type="text"
                            value={editedMeta.company}
                            onChange={(e) => setEditedMeta({ ...editedMeta, company: e.target.value })}
                            className="w-full bg-ui-page border border-ui-line text-ui-secondary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                          />
                        </div>
                        <div>
                          <label className="text-[0.6875rem] text-ui-muted block mb-1">Location</label>
                          <input
                            type="text"
                            value={editedMeta.location}
                            onChange={(e) => setEditedMeta({ ...editedMeta, location: e.target.value })}
                            className="w-full bg-ui-page border border-ui-line text-ui-secondary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                          />
                        </div>
                        <div>
                          <label className="text-[0.6875rem] text-ui-muted block mb-1">Workplace</label>
                          <select
                            value={editedMeta.workplace_type}
                            onChange={(e) => setEditedMeta({ ...editedMeta, workplace_type: e.target.value })}
                            className="w-full bg-ui-page border border-ui-line text-ui-secondary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                          >
                            <option value="onsite">Onsite</option>
                            <option value="hybrid">Hybrid</option>
                            <option value="remote">Remote</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-[0.6875rem] text-ui-muted block mb-1">Min Salary ($)</label>
                          <input
                            type="number"
                            value={editedMeta.salary_min}
                            onChange={(e) => setEditedMeta({ ...editedMeta, salary_min: e.target.value })}
                            className="w-full bg-ui-page border border-ui-line text-ui-secondary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                          />
                        </div>
                        <div>
                          <label className="text-[0.6875rem] text-ui-muted block mb-1">Max Salary ($)</label>
                          <input
                            type="number"
                            value={editedMeta.salary_max}
                            onChange={(e) => setEditedMeta({ ...editedMeta, salary_max: e.target.value })}
                            className="w-full bg-ui-page border border-ui-line text-ui-secondary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex flex-col items-end gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => setIsEditingMeta(!isEditingMeta)}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border border-ui-line bg-ui-panel text-ui-body hover:text-ui-ink-amber-300 hover:border-ui-line-amber-500/50 transition cursor-pointer"
                    title={isEditingMeta ? 'Done editing metadata' : 'Edit extracted metadata'}
                  >
                    {isEditingMeta ? (
                      <>
                        <Check className="h-3 w-3 text-ui-ink-emerald-400" />
                        <span>Done</span>
                      </>
                    ) : (
                      <>
                        <Edit3 className="h-3 w-3 text-ui-muted" />
                        <span>Edit Details</span>
                      </>
                    )}
                  </button>

                  {analysis.triage ? (
                    <div className={`px-3 py-1.5 rounded-xl border text-center ${
                      analysis.triage.decision === 'STRONG_KNOCK'
                        ? 'bg-ui-fill-emerald-950/60 border-ui-line-emerald-700 text-ui-ink-emerald-400'
                        : analysis.triage.decision === 'SELECTIVE_APPLY'
                        ? 'bg-ui-fill-blue-950/60 border-ui-line-blue-700 text-ui-ink-blue-400'
                        : analysis.triage.decision === 'HARD_PASS'
                        ? 'bg-ui-fill-red-950/60 border-ui-line-red-700 text-ui-ink-red-400'
                        : 'bg-ui-fill-amber-950/60 border-ui-line-amber-700 text-ui-ink-amber-400'
                    }`}>
                      <span className="block text-xs font-black uppercase tracking-wider">{analysis.triage.decision.replace('_', ' ')}</span>
                      <span className="text-[0.625rem] text-ui-muted">Triage Recommendation</span>
                    </div>
                  ) : score !== null && (
                    <div className={`px-4 py-2 rounded-xl border text-center ${
                      score >= 85
                        ? 'bg-ui-fill-emerald-950/60 border-ui-line-emerald-700 text-ui-ink-emerald-400'
                        : score >= 70
                        ? 'bg-ui-fill-amber-950/60 border-ui-line-amber-700 text-ui-ink-amber-400'
                        : 'bg-ui-raised border-ui-line text-ui-body'
                    }`}>
                      <span className="block text-2xl font-black">{score}%</span>
                      <span className="text-[0.625rem] font-semibold uppercase tracking-wider">Overall Fit</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* V2 Tactical Brief Presentation */}
            {analysis.triage ? (
              <div className="space-y-3">
                {/* Strategic Thesis & Dealbreaker Audit */}
                <div className="bg-ui-page/80 p-3.5 rounded-xl border border-ui-line-soft space-y-2">
                  <div className="text-xs text-ui-secondary leading-relaxed">
                    <span className="text-ui-ink-amber-400 font-semibold">Strategic Rationale: </span>
                    {analysis.triage.strategic_thesis}
                  </div>
                  <div className="text-[0.6875rem] text-ui-muted pt-1.5 border-t border-ui-line-soft flex items-center justify-between">
                    <span>Dealbreaker Audit:</span>
                    {hasDealbreakers ? (
                      <span className="text-ui-ink-rose-400 font-semibold flex items-center gap-1">
                        <span>⚠️</span>
                        <span>{detectedDealbreakers.join(', ')}</span>
                      </span>
                    ) : (
                      <span className="text-ui-ink-emerald-400 font-medium">✓ None detected</span>
                    )}
                  </div>
                </div>

                {/* Acute Friction & Value Hook */}
                {analysis.employer_mandate && (
                  <div className="bg-ui-page/80 p-3.5 rounded-xl border border-ui-line-soft space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[0.6875rem] font-bold text-ui-ink-amber-400 uppercase tracking-wider">Acute Employer Bottlenecks</span>
                      {analysis.employer_mandate.role_archetype && (
                        <span className="text-[0.625rem] font-bold px-2 py-0.5 rounded bg-ui-fill-blue-500/20 text-ui-ink-blue-300 border border-ui-line-blue-500/30">
                          Role: {analysis.employer_mandate.role_archetype}
                        </span>
                      )}
                    </div>
                    {analysis.employer_mandate.acute_operational_frictions?.length > 0 && (
                      <ul className="space-y-1">
                        {analysis.employer_mandate.acute_operational_frictions.map((f, i) => (
                          <li key={i} className="text-xs text-ui-body bg-ui-panel/80 p-2 rounded-lg border border-ui-line-soft/80 flex items-start gap-2">
                            <span className="text-ui-ink-amber-500">🔥</span>
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {analysis.employer_mandate.immediate_value_hook && (
                      <div className="text-xs text-ui-body bg-ui-fill-amber-950/20 p-2.5 rounded-lg border border-ui-line-amber-900/30">
                        <span className="text-ui-ink-amber-300 font-bold">Day-1 Antidote: </span>
                        {analysis.employer_mandate.immediate_value_hook}
                      </div>
                    )}
                  </div>
                )}

                {/* Gaps & Strategic Defense */}
                {analysis.gaps_and_mitigation && analysis.gaps_and_mitigation.length > 0 && (
                  <div className="bg-ui-page/80 p-3.5 rounded-xl border border-ui-line-soft space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[0.6875rem] font-bold text-ui-muted uppercase tracking-wider">Gaps & Strategic Defense</span>
                      <span className="text-[0.625rem] font-bold px-2 py-0.5 rounded bg-ui-fill-amber-500/10 text-ui-ink-amber-300 border border-ui-line-amber-500/30">
                        Risk Audit
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {analysis.gaps_and_mitigation.map((g, i) => (
                        <div key={i} className="bg-ui-panel/80 p-2.5 rounded-lg border border-ui-line-soft text-xs space-y-1">
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
              /* Legacy Fallback Presentation */
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-ui-page/80 p-3 rounded-xl border border-ui-line-soft text-center">
                    <span className="text-[0.6875rem] text-ui-muted block mb-1">Technical Stack</span>
                    <span className="text-sm font-bold text-ui-ink-amber-400">{analysis.technical_fit_score || score || 85}%</span>
                  </div>
                  <div className="bg-ui-page/80 p-3 rounded-xl border border-ui-line-soft text-center">
                    <span className="text-[0.6875rem] text-ui-muted block mb-1">Domain & Scope</span>
                    <span className="text-sm font-bold text-ui-ink-amber-400">{analysis.domain_fit_score || score || 90}%</span>
                  </div>
                  <div className="bg-ui-page/80 p-3 rounded-xl border border-ui-line-soft text-center">
                    <span className="text-[0.6875rem] text-ui-muted block mb-1">Work Eligibility</span>
                    <span className="text-sm font-bold text-ui-ink-emerald-400">{analysis.eligibility_fit_score || 100}%</span>
                  </div>
                </div>

                {analysis.suitability_reason && (
                  <div className="bg-ui-page/60 p-3.5 rounded-xl border border-ui-line-soft">
                    <span className="text-xs font-bold text-ui-ink-amber-400 block mb-1">Fit Verdict & Trade-offs:</span>
                    <p className="text-xs text-ui-body leading-relaxed">{analysis.suitability_reason}</p>
                  </div>
                )}

                {analysis.employer_pain_points && analysis.employer_pain_points.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-xs font-bold text-ui-ink-red-400 uppercase tracking-wider flex items-center gap-1">
                      <ShieldAlert className="h-3.5 w-3.5" />
                      Target Employer Pain Points (Outreach Hooks)
                    </span>
                    <ul className="space-y-1">
                      {analysis.employer_pain_points.map((pp, i) => (
                        <li key={i} className="text-xs text-ui-body bg-ui-page/80 p-2 rounded-lg border border-ui-line-soft/80 flex items-start gap-2">
                          <span className="text-ui-ink-amber-500 font-bold">•</span>
                          <span>{pp}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {analysis.key_strengths && analysis.key_strengths.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-xs font-bold text-ui-ink-emerald-400 uppercase tracking-wider flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Matched Candidate Evidence
                    </span>
                    <ul className="space-y-1">
                      {analysis.key_strengths.map((str, i) => (
                        <li key={i} className="text-xs text-ui-body bg-ui-page/80 p-2 rounded-lg border border-ui-line-soft/80 flex items-start gap-2">
                          <span className="text-ui-ink-emerald-500 font-bold">✓</span>
                          <span>{str}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Modal Footer */}
        <div className="p-4 border-t border-ui-line-soft bg-ui-page/80 flex items-center justify-between">
          <div>
            {analysis && (
              <button
                onClick={() => setAnalysis(null)}
                className="text-xs text-ui-muted hover:text-ui-heading px-2 py-1 transition cursor-pointer"
              >
                ← Back to Input
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 text-xs font-medium text-ui-muted hover:text-ui-heading rounded-lg transition cursor-pointer"
            >
              Cancel
            </button>

            {!analysis ? (
              <button
                onClick={handleAnalyze}
                disabled={isAnalyzing || textInput.trim().length < 30}
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-ui-fill-amber-600 hover:bg-ui-fill-amber-500 text-ui-on-action rounded-xl shadow-lg shadow-amber-950/50 transition disabled:opacity-50 cursor-pointer"
              >
                <Sparkles className={`h-3.5 w-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
                <span>{isAnalyzing ? 'Analyzing Match...' : 'Analyze Match'}</span>
              </button>
            ) : (
              <button
                onClick={handleSaveToDoorKnock}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-ui-fill-emerald-600 hover:bg-ui-fill-emerald-500 text-ui-on-color rounded-xl shadow-lg shadow-emerald-950/50 transition disabled:opacity-50 cursor-pointer"
              >
                <span>{isSaving ? 'Saving...' : 'Save & Start Company Recon'}</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImportJobModal;
