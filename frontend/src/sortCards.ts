export type CardSort = 'newest' | 'oldest' | 'company-asc' | 'company-desc' | 'score-desc' | 'score-asc';

type SortableCard = {
  company: string;
  suitability_score?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export function sortCards<T extends SortableCard>(
  cards: T[],
  sort: CardSort,
  dateField: 'created_at' | 'updated_at',
): T[] {
  return [...cards].sort((a, b) => {
    if (sort === 'company-asc' || sort === 'company-desc') {
      const comparison = a.company.localeCompare(b.company, undefined, { sensitivity: 'base' });
      return sort === 'company-asc' ? comparison : -comparison;
    }

    if (sort === 'score-desc' || sort === 'score-asc') {
      const aScore = a.suitability_score;
      const bScore = b.suitability_score;
      if (aScore == null) return bScore == null ? 0 : 1;
      if (bScore == null) return -1;
      return sort === 'score-desc' ? bScore - aScore : aScore - bScore;
    }

    const aDate = a[dateField] ? Date.parse(a[dateField]) : NaN;
    const bDate = b[dateField] ? Date.parse(b[dateField]) : NaN;
    if (Number.isNaN(aDate)) return Number.isNaN(bDate) ? 0 : 1;
    if (Number.isNaN(bDate)) return -1;
    return sort === 'newest' ? bDate - aDate : aDate - bDate;
  });
}
