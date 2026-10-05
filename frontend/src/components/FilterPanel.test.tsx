import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { FilterPanel } from './FilterPanel.tsx';

afterEach(() => {
  cleanup();
});

function renderPanel(overrides = {}) {
  const props = {
    cuisine: '',
    hasWebsite: false,
    hasPhone: false,
    hasHours: false,
    lat: '',
    lon: '',
    radius: '',
    onCuisineChange: vi.fn(),
    onHasWebsiteChange: vi.fn(),
    onHasPhoneChange: vi.fn(),
    onHasHoursChange: vi.fn(),
    onLatChange: vi.fn(),
    onLonChange: vi.fn(),
    onRadiusChange: vi.fn(),
    onClear: vi.fn(),
    ...overrides,
  };
  render(<FilterPanel {...props} />);
  return props;
}

describe('FilterPanel', () => {
  it('lists verified cuisine tags including coffee_shop', () => {
    renderPanel();
    const options = Array.from(
      (screen.getByLabelText(/cuisine/i) as HTMLSelectElement).options,
    ).map((option) => option.value);
    expect(options).toContain('coffee_shop');
    expect(options).toContain('tea_shop');
    expect(options[0]).toBe('');
  });

  it('reports cuisine selection', () => {
    const props = renderPanel();
    fireEvent.change(screen.getByLabelText(/cuisine/i), { target: { value: 'tea' } });
    expect(props.onCuisineChange).toHaveBeenCalledWith('tea');
  });

  it('reports boolean filter toggles', () => {
    const props = renderPanel();
    fireEvent.click(screen.getByLabelText(/website/i));
    expect(props.onHasWebsiteChange).toHaveBeenCalledWith(true);
    fireEvent.click(screen.getByLabelText(/phone/i));
    expect(props.onHasPhoneChange).toHaveBeenCalledWith(true);
    fireEvent.click(screen.getByLabelText(/opening hours/i));
    expect(props.onHasHoursChange).toHaveBeenCalledWith(true);
  });

  it('states that filters combine with AND logic', () => {
    renderPanel();
    expect(screen.getByText(/AND logic/i)).toBeInTheDocument();
  });

  it('reports location input and offers clear filters', () => {
    const props = renderPanel();
    fireEvent.change(screen.getByLabelText(/latitude/i), { target: { value: '26.8' } });
    expect(props.onLatChange).toHaveBeenCalledWith('26.8');
    fireEvent.click(screen.getByRole('button', { name: /clear filters/i }));
    expect(props.onClear).toHaveBeenCalledTimes(1);
  });
});
