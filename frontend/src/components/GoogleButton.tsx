import { useEffect, useRef } from "react";

/** The parts of Google Identity Services (accounts.google.com/gsi/client) we use. */
type Gsi = {
  accounts: {
    id: {
      initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void;
      renderButton: (el: HTMLElement, o: Record<string, string | number>) => void;
    };
  };
};
declare global {
  interface Window { google?: Gsi }
}

const GSI_SRC = "https://accounts.google.com/gsi/client";
let loading: Promise<Gsi> | null = null;

function loadGsi(): Promise<Gsi> {
  if (window.google?.accounts?.id) return Promise.resolve(window.google);
  loading ??= new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = GSI_SRC;
    s.async = true;
    s.onload = () => (window.google ? resolve(window.google) : reject(new Error("Google sign-in didn't load")));
    s.onerror = () => { loading = null; reject(new Error("Couldn't reach Google. Check your connection.")); };
    document.head.appendChild(s);
  });
  return loading;
}

/** Google's own "Continue with Google" button. It hands us an ID token that the backend verifies. */
export default function GoogleButton({ clientId, onCredential, onError }: {
  clientId: string; onCredential: (credential: string) => void; onError: (message: string) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const latest = useRef(onCredential);
  latest.current = onCredential;

  useEffect(() => {
    let cancelled = false;
    loadGsi()
      .then((g) => {
        if (cancelled || !box.current) return;
        g.accounts.id.initialize({ client_id: clientId, callback: (r) => latest.current(r.credential) });
        g.accounts.id.renderButton(box.current, {
          type: "standard", theme: "outline", size: "large", shape: "pill", text: "continue_with",
          width: Math.min(400, Math.max(200, box.current.offsetWidth)),
        });
      })
      .catch((e: Error) => onError(e.message));
    return () => { cancelled = true; };
  }, [clientId]); // eslint-disable-line react-hooks/exhaustive-deps

  return <div ref={box} className="google-btn" />;
}
