/** The assistant's avatar: a bowl with a leaf, drawn inline so it follows the theme. */
export function AssistantAvatar({ size = 32 }: { size?: number }) {
  return (
    <span className="avatar assistant-avatar" style={{ width: size, height: size }} aria-hidden="true">
      <svg viewBox="0 0 32 32" width={size * 0.62} height={size * 0.62}>
        {/* leaf */}
        <path d="M17 4c5 0 8 3 8 7-4 1-8-1-8-7z" fill="currentColor" opacity="0.9" />
        <path d="M16.5 12c0-3 .5-5 1.5-7" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round" />
        {/* bowl */}
        <path d="M4 15h24c0 6.6-5.4 12-12 12S4 21.6 4 15z" fill="currentColor" />
        <path d="M10 19.5c1.5 2.5 4 3.5 6 3.5" stroke="var(--avatar-bg)" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export function initialsFor(name: string | null, email: string): string {
  const source = (name && name.trim()) || email.split("@")[0];
  const parts = source.split(/[\s._-]+/).filter(Boolean);
  const letters = parts.length > 1 ? parts[0][0] + parts[1][0] : source.slice(0, 2);
  return letters.toUpperCase();
}

export function UserAvatar({ name, email, size = 32 }: { name: string | null; email: string; size?: number }) {
  return (
    <span className="avatar user-avatar" style={{ width: size, height: size, fontSize: size * 0.4 }} aria-hidden="true">
      {initialsFor(name, email)}
    </span>
  );
}
