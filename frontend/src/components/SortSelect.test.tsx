import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { SortSelect } from './SortSelect.tsx';

afterEach(() => {
  cleanup();
});

describe('SortSelect', () => {
  it('offers the backend sort values with human-friendly labels', () => {
    render(<SortSelect value="score" onChange={() => undefined} />);
    const select = screen.getByLabelText(/sort/i) as HTMLSelectElement;
    const values = Array.from(select.options).map((option) => option.value);
    expect(values).toEqual(['score', 'distance', 'name', 'latitude', 'longitude']);
    expect(screen.getByRole('option', { name: 'Score' })).toBeInTheDocument();
  });

  it('reports the backend value, not the label', () => {
    const onChange = vi.fn();
    render(<SortSelect value="score" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText(/sort/i), { target: { value: 'distance' } });
    expect(onChange).toHaveBeenCalledWith('distance');
  });
});
