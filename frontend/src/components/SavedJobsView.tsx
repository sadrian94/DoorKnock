import React, { useState } from 'react';
import { Search, MapPin, DollarSign, Building2, Briefcase, Sparkles, Plus } from 'lucide-react';
import type { Job } from '../types';
import { sortCards, type CardSort } from '../sortCards';

interface SavedJobsViewProps {
  jobs: Job[];
  onSelectJob: (jobId: string) => void;
  onStartApplication?: (jobId: string) => void;
  onOpenImport?: () => void;
  isLoading: boolean;
}

export const SavedJobsView: React.FC<SavedJobsViewProps> = ({
  jobs,
  onSelectJob,
  onOpenImport,
  isLoading,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [workplaceFilter, setWorkplaceFilter] = useState<string>('all');
  const [sortOrder, setSortOrder] = useState<CardSort>('score-desc');

  const filteredJobs = sortCards(jobs.filter((job) => {
    const matchesSearch =
      job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (job.location && job.location.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesWorkplace =
      workplaceFilter === 'all' || job.workplace_type === workplaceFilter;

    return matchesSearch && matchesWorkplace;
  }), sortOrder, 'created_at');

  const formatSalary = (job: Job) => {
    if (job.salary_min && job.salary_max) {
      return `$${job.salary_min.toLocaleString()} - $${job.salary_max.toLocaleString()}/${job.salary_interval || 'yr'}`;
    }
    if (job.salary_min) {
      return `From $${job.salary_min.toLocaleString()}/${job.salary_interval || 'yr'}`;
    }
    return null;
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Saved & Ready Targets</h2>
          <p className="text-sm text-slate-400 mt-1">
            Jobs prepared for application & outreach. Tailor documents and scout gatekeepers.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search title, company, or city..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl pl-10 pr-4 py-2 w-64 md:w-80 focus:outline-none focus:border-amber-500 transition shadow-sm"
            />
          </div>

          <select
            value={workplaceFilter}
            onChange={(e) => setWorkplaceFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl px-3 py-2 focus:outline-none focus:border-amber-500"
          >
            <option value="all">All Workplace</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">Onsite</option>
          </select>
          <select
            aria-label="Sort saved jobs"
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as CardSort)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl px-3 py-2 focus:outline-none focus:border-amber-500"
          >
            <option value="newest">Newest added</option>
            <option value="oldest">Oldest added</option>
            <option value="company-asc">Company A–Z</option>
            <option value="company-desc">Company Z–A</option>
            <option value="score-desc">Match score: high to low</option>
            <option value="score-asc">Match score: low to high</option>
          </select>
        </div>
      </div>

      {/* Grid of Jobs */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64 text-slate-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500"></div>
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-12 text-center">
          <Briefcase className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-slate-300">No saved jobs found</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
            {jobs.length === 0
              ? 'Import a job posting to begin tailoring documents and scouting gatekeepers.'
              : 'Try adjusting your search criteria or workplace filter to find what you need.'}
          </p>
          {jobs.length === 0 && onOpenImport ? (
            <button
              type="button"
              onClick={onOpenImport}
              className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 rounded-xl shadow-md shadow-amber-950/40 transition cursor-pointer"
            >
              <Plus className="h-4 w-4" />
              <span>Import Your First Job</span>
            </button>
          ) : jobs.length > 0 && (searchTerm || workplaceFilter !== 'all') ? (
            <button
              type="button"
              onClick={() => {
                setSearchTerm('');
                setWorkplaceFilter('all');
              }}
              className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition cursor-pointer"
            >
              Clear filters
            </button>
          ) : null}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredJobs.map((job) => {
            const salary = formatSalary(job);
            const triageBadge = (() => {
              let decision: string | null = null;
              if (job.analysis_json) {
                try {
                  const parsed = typeof job.analysis_json === 'string' ? JSON.parse(job.analysis_json) : job.analysis_json;
                  decision = parsed?.triage?.decision || null;
                } catch {
                  // ignore parse error
                }
              }
              if (!decision && job.suitability_score !== undefined && job.suitability_score !== null) {
                const s = job.suitability_score;
                if (s >= 90) decision = 'STRONG_KNOCK';
                else if (s >= 75) decision = 'SELECTIVE_APPLY';
                else if (s >= 60) decision = 'HIGH_RISK_LOW_ROI';
                else decision = 'HARD_PASS';
              }
              if (!decision) return null;

              switch (decision) {
                case 'STRONG_KNOCK':
                  return { label: 'STRONG KNOCK', icon: '🎯', style: 'bg-emerald-950/80 text-emerald-400 border-emerald-700/70' };
                case 'SELECTIVE_APPLY':
                  return { label: 'SELECTIVE APPLY', icon: '⚡', style: 'bg-amber-950/80 text-amber-400 border-amber-700/70' };
                case 'HIGH_RISK_LOW_ROI':
                  return { label: 'HIGH RISK', icon: '⚠️', style: 'bg-rose-950/80 text-rose-400 border-rose-800/70' };
                case 'HARD_PASS':
                case 'DO_NOT_APPLY':
                  return { label: 'HARD PASS', icon: '⛔', style: 'bg-slate-900 text-slate-400 border-slate-700' };
                default:
                  return { label: decision.replace(/_/g, ' '), icon: '📋', style: 'bg-slate-800 text-slate-300 border-slate-700' };
              }
            })();

            const tacticalThesis = (() => {
              if (job.analysis_json) {
                try {
                  const parsed = typeof job.analysis_json === 'string' ? JSON.parse(job.analysis_json) : job.analysis_json;
                  if (parsed?.triage?.strategic_thesis) return parsed.triage.strategic_thesis;
                } catch {
                  // ignore
                }
              }
              return job.suitability_reason || null;
            })();

            return (
              <div
                key={job.id}
                onClick={() => onSelectJob(job.id)}
                className="group relative bg-slate-900 border border-slate-800 hover:border-amber-500/50 hover:shadow-xl hover:shadow-amber-950/20 rounded-2xl p-5 transition-all cursor-pointer flex flex-col justify-between"
              >
                <div>
                  {/* Top Bar: Company & Triage Verdict */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <div className="h-8 w-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300 border border-slate-700">
                        <Building2 className="h-4 w-4" />
                      </div>
                      <span className="text-sm font-semibold text-slate-300 truncate max-w-[150px]">
                        {job.company}
                      </span>
                    </div>

                    {triageBadge && (
                      <span className={`flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-full border shadow-sm ${triageBadge.style}`}>
                        <span>{triageBadge.icon}</span>
                        <span>{triageBadge.label}</span>
                      </span>
                    )}
                  </div>

                  {/* Title */}
                  <h3
                    className="text-base font-bold text-white group-hover:text-amber-400 transition line-clamp-2"
                  >
                    {job.title}
                  </h3>

                  {/* Tags: Location, Workplace, Salary */}
                  <div className="flex flex-wrap items-center gap-2 mt-3 text-xs text-slate-400">
                    {job.location && (
                      <span className="flex items-center gap-1 bg-slate-800/80 px-2 py-0.5 rounded-md border border-slate-700/60">
                        <MapPin className="h-3 w-3 text-slate-500" />
                        <span className="truncate max-w-[120px]">{job.location}</span>
                      </span>
                    )}

                    {job.workplace_type && (
                      <span className="capitalize bg-slate-800/80 px-2 py-0.5 rounded-md border border-slate-700/60">
                        {job.workplace_type}
                      </span>
                    )}

                    {salary && (
                      <span className="flex items-center gap-1 bg-amber-950/40 text-amber-300 px-2 py-0.5 rounded-md border border-amber-800/40 font-medium">
                        <DollarSign className="h-3 w-3" />
                        {salary}
                      </span>
                    )}
                  </div>

                  {/* Tactical Thesis or Suitability Reason */}
                  {tacticalThesis && (
                    <div className="mt-4 text-xs bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 group-hover:border-slate-700/80 transition-colors">
                      <div className="flex items-center gap-1.5 font-medium text-amber-400/90 mb-1.5">
                        <Sparkles className="h-3 w-3 text-amber-400" />
                        <span>Tactical Thesis</span>
                      </div>
                      <p className="text-slate-300/90 leading-relaxed line-clamp-5">
                        {tacticalThesis}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
