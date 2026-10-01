import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { readBarcode } from "../scan";

const FRAME_MS = 400;     // how often a camera frame is checked for a barcode

/** Read a packaged product's barcode with the live camera or from a photo (barcode only: owner,
 *  2026-10-01). The number only fills the search; the user still picks the product (src/scan.ts
 *  does the reading). */
export default function PackScanner({ onRead, onClose }: { onRead: (barcode: string) => void; onClose: () => void }) {
  const [mode, setMode] = useState<"pick" | "camera" | "reading">("pick");
  const [error, setError] = useState<string | null>(null);
  // An uploaded photo with no readable barcode: offer a close-up instead of a dead end.
  const [missed, setMissed] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  useEffect(() => { close.current = onClose; });
  const cameraOk = typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

  function stopCamera() {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }

  // Esc closes; the camera is always switched off on the way out.
  useEffect(() => {
    box.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close.current(); };
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); stopCamera(); };
  }, []);

  async function startCamera() {
    setError(null);
    setMissed(false);
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false,
      });
      setMode("camera");
    } catch {
      setError("The camera isn't available. Allow camera access for this site, or upload a photo instead.");
    }
  }

  // While the camera is open: attach it, and look for a barcode a few times a second.
  useEffect(() => {
    if (mode !== "camera" || !video.current || !stream.current) return;
    const v = video.current;
    v.srcObject = stream.current;
    void v.play().catch(() => undefined);
    const canvas = document.createElement("canvas");
    let busy = false;
    let done = false;
    const timer = setInterval(async () => {
      if (busy || done || v.readyState < 2) return;
      busy = true;
      try {
        canvas.width = v.videoWidth;
        canvas.height = v.videoHeight;
        const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
        ctx.drawImage(v, 0, 0);
        const code = await readBarcode(ctx.getImageData(0, 0, canvas.width, canvas.height));
        if (code && !done) {
          done = true;
          stopCamera();
          onRead(code);
        }
      } catch {
        /* a frame that can't be read: try the next one */
      } finally {
        busy = false;
      }
    }, FRAME_MS);
    return () => { done = true; clearInterval(timer); };
  }, [mode]); // eslint-disable-line react-hooks/exhaustive-deps

  /** An uploaded photo, read at full size (a small barcode in a wide shot needs every pixel). */
  async function readPhoto(photo: Blob) {
    setMode("reading");
    setError(null);
    setMissed(false);
    try {
      const code = await readBarcode(photo);
      if (code) return onRead(code);
      setMissed(true);
    } catch {
      setError("Couldn't open that photo. Try another one, or use the camera.");
    }
    setMode("pick");
  }

  // On <body>, so it isn't clipped by the chat window it may be opened from, and on a layer above
  // other dialogs: it opens from inside one (the chat's pack finder), whose portal comes later in
  // the page and would otherwise cover it.
  return createPortal(
    <div className="backdrop pack-scanner-layer">
      <div className="dialog card pack-scanner" role="dialog" aria-modal="true" aria-labelledby="pack-scan-title" ref={box}>
        <div className="dialog-head">
          <h3 id="pack-scan-title">Scan the barcode</h3>
          <button type="button" className="ghost icon-btn" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {mode === "camera" ? (
          <>
            <div className="pack-camera">
              <video ref={video} playsInline muted aria-label="Camera view" />
              <span className="pack-camera-frame" aria-hidden="true" />
            </div>
            <p className="muted small">Point at the <b>barcode</b> and hold still: it's read on its own.</p>
            <div className="pack-actions">
              <button type="button" className="ghost" onClick={() => { stopCamera(); setMode("pick"); }}>Back</button>
            </div>
          </>
        ) : mode === "reading" ? (
          <p className="pack-reading" role="status"><span className="spinner" aria-hidden="true" /> Looking for the barcode…</p>
        ) : (
          <>
            {missed ? (
              <div className="scan-tip" role="status">
                <b>Couldn't spot the barcode in that photo.</b>
                <span>Try a close-up of just the barcode: fill the photo with it, keep it sharp and in good light (no glare on
                  the lines), and upload it again.</span>
              </div>
            ) : (
              <p className="muted small">
                Scan the <b>barcode</b> on the pack, or upload a photo of it. For packaged products; for cooked or loose
                food (a curry, a thali), just tell MacBro.
              </p>
            )}
            <div className="pack-actions">
              {missed && <button type="button" className="primary" onClick={() => file.current?.click()}>🖼 Upload a close-up</button>}
              {cameraOk && <button type="button" className={missed ? "" : "primary"} onClick={startCamera}>📷 Use camera</button>}
              {!missed && <button type="button" className={cameraOk ? "" : "primary"} onClick={() => file.current?.click()}>🖼 Upload a photo</button>}
              <input ref={file} type="file" accept="image/*" hidden
                     onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) void readPhoto(f); }} />
            </div>
            <p className="muted tiny">The photo is read on your device and isn't uploaded. Only the barcode number is searched.</p>
          </>
        )}
        {error && <p className="error small">{error}</p>}
      </div>
    </div>,
    document.body,
  );
}
