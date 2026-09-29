import { test } from 'node:test';
import assert from 'node:assert/strict';
import { getJobIdentifierItems } from '../src/jobIdentifiers.ts';

test('includes the internal Job ID and source ID when both are available', () => {
  assert.deepEqual(
    getJobIdentifierItems({ id: 'internal-job-123', source_job_id: 'source-job-456' }),
    [
      { label: 'Job ID', value: 'internal-job-123' },
      { label: 'Source ID', value: 'source-job-456' },
    ],
  );
});

test('omits the source ID when it is not available', () => {
  assert.deepEqual(
    getJobIdentifierItems({ id: 'internal-job-123', source_job_id: null }),
    [{ label: 'Job ID', value: 'internal-job-123' }],
  );
});
