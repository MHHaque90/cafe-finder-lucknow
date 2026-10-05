import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { SearchBar } from './SearchBar.tsx';

afterEach(() => {
  cleanup();
});

describe('SearchBar', () => {
  it('associates the visible label with the search input', () => {
    render(<SearchBar value="" onChange={() => undefined} />);
    expect(screen.getByLabelText(/search/i)).toHaveAttribute('type', 'search');
  });

  it('reports typed text through onChange', () => {
    const onChange = vi.fn();
    render(<SearchBar value="" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText(/search/i), { target: { value: 'cafe' } });
    expect(onChange).toHaveBeenCalledWith('cafe');
  });

  it('reflects the controlled value', () => {
    render(<SearchBar value="coffee" onChange={() => undefined} />);
    expect(screen.getByLabelText(/search/i)).toHaveValue('coffee');
  });
});
