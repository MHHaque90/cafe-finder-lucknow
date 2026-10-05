interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="field">
      <label htmlFor="cafe-search">Search</label>
      <input
        id="cafe-search"
        name="search"
        type="search"
        autoComplete="off"
        placeholder="Search cafes by name…"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}
