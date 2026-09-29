import type { Job } from './types';

export interface JobIdentifierItem {
  label: 'Job ID' | 'Source ID';
  value: string;
}

export const getJobIdentifierItems = (
  job: Pick<Job, 'id' | 'source_job_id'>,
): JobIdentifierItem[] => {
  const items: JobIdentifierItem[] = [{ label: 'Job ID', value: job.id }];

  if (job.source_job_id) {
    items.push({ label: 'Source ID', value: job.source_job_id });
  }

  return items;
};
