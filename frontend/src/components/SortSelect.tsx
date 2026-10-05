import { SORT_OPTIONS } from '../api/client.ts';
import type { SortMode } from '../api/types.ts';

interface SortSelectProps {
  value: SortMode;
  onChange: (value: SortMode) => void;
}

const SORT_VALUES: readonly string[] = SORT_OPTIONS.map((option) => option.value);

function isSortMode(value: string): value is SortMode {
  return (SORT_VALUES as readonly string[]).includes(value);
}

export function SortSelect({ value, onChange }: SortSelectProps) {
  return (
    <div className="field field-inline">
      <label htmlFor="sort-select">Sort</label>
      <select
        id="sort-select"
        value={value}
        onChange={(event) => {
          if (isSortMode(event.target.value)) onChange(event.target.value);
        }}
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
