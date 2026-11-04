import type { FactReviewRow } from './historyTypes';

export function firstInvalidReviewRow(rows: FactReviewRow[]) {
  const limits = [
    ['label', 'Name', 200], ['value', 'Recorded value', 800], ['unit', 'Printed unit', 80],
    ['occurred_on', 'Recorded date', 100], ['facility', 'Facility', 200],
    ['reference_range', 'Lab’s reference range', 400], ['specimen', 'Specimen', 200], ['test_method', 'Test method', 200],
  ] as const;
  for (const [index, row] of rows.entries()) {
    if (!row.keep) continue;
    for (const [field, control, max] of limits) {
      const value = row[field] || '';
      if ((field === 'label' || field === 'value') && !value.trim())
        return {id: row.id, index, control, message: `Entry ${index + 1} needs ${field === 'label' ? 'a name' : 'a recorded value'}. Enter it or exclude this entry.`};
      if (value.length > max)
        return {id: row.id, index, control, message: `Entry ${index + 1}: ${control.toLowerCase()} must be ${max} characters or fewer.`};
    }
  }
  return null;
}

export function reviewPage(rows: FactReviewRow[], selectedIndex: number) {
  const size = 30;
  const index = Math.min(Math.max(0, selectedIndex), Math.max(0, rows.length - 1));
  const start = Math.floor(index / size) * size;
  return {size, start, rows: rows.slice(start, start + size).map((row, offset) => ({row, index: start + offset}))};
}
