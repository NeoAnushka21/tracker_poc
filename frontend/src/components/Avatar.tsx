import { APP_LOGO, APP_NAME } from "../brand";
import { useId } from "react";

/** MacBro: a cartoon boy in an "MB" t-shirt. Drawn inline so it scales cleanly. */
export function MacBroAvatar({ size = 32 }: { size?: number }) {
  const clipId = `mb-clip-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  return (
    <span className="avatar macbro-avatar" style={{ width: size, height: size }} aria-hidden="true">
      <svg viewBox="0 0 64 64" width={size} height={size}>
        <defs>
          <clipPath id={clipId}><circle cx="32" cy="32" r="32" /></clipPath>
        </defs>
        <g clipPath={`url(#${clipId})`}>
          <circle cx="32" cy="32" r="32" className="mb-bg" />
          {/* t-shirt */}
          <path d="M6 64c0-11 7-18 15-20l5-2h12l5 2c8 2 15 9 15 20z" className="mb-shirt" />
          <path d="M26 42c1.5 3 3.5 4.5 6 4.5s4.5-1.5 6-4.5" className="mb-collar" />
          <text x="32" y="59" textAnchor="middle" className="mb-letters">MB</text>
          {/* neck, ears, head */}
          <rect x="28" y="36" width="8" height="8" rx="3" className="mb-skin" />
          <circle cx="18.5" cy="27" r="3.2" className="mb-skin" />
          <circle cx="45.5" cy="27" r="3.2" className="mb-skin" />
          <circle cx="32" cy="26" r="13.5" className="mb-skin" />
          {/* hair with a little front flick */}
          <path d="M18.5 25c-.5-8.5 5.5-14 13.5-14 8.5 0 14 5.5 13.5 13.5-2.5-4-6-6-10.5-6.3 1 1.3 1.3 2.8.8 4-3-2.8-7.8-4-12.3-2.6-2.6.8-4 2.6-5 5.4z" className="mb-hair" />
          {/* face */}
          <circle cx="26.8" cy="27.5" r="1.7" className="mb-ink" />
          <circle cx="37.2" cy="27.5" r="1.7" className="mb-ink" />
          <path d="M27 32.5c2.8 3 7.2 3 10 0" className="mb-smile" />
          <circle cx="23.5" cy="31.5" r="1.8" className="mb-cheek" />
          <circle cx="40.5" cy="31.5" r="1.8" className="mb-cheek" />
        </g>
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

/** App logo: the Tandurust emblem (transparent PNG, sharp at 2x). Decorative unless `label`. */
export function AppLogo({ size = 32, label = false }: { size?: number; label?: boolean }) {
  const big = size > 48;   // the 96 px file is enough up to 48 px on a 2x screen
  return (
    <img className="app-logo" src={big ? APP_LOGO.src2x : APP_LOGO.src}
         srcSet={big ? undefined : `${APP_LOGO.src} 1x, ${APP_LOGO.src2x} 2x`}
         width={size} height={size} alt={label ? APP_NAME : ""} aria-hidden={label ? undefined : true}
         decoding="async" draggable={false} />
  );
}
