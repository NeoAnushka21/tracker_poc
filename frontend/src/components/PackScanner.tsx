import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { readBarcode, readPackWords, shrink } from "../scan";

export type PackReading = { kind: "barcode" | "words"; text: string };

const FRAME_MS = 400;     // how often a camera frame is checked for a barcode

/** Read a packaged product with the live camera or from a photo: its barcode when one is in view,
 *  else the brand and name printed on the front. Only for packs: a cooked dish can't be read. The
 *  result only fills the search; the user still picks the product (src/scan.ts does the reading). */
export default function PackScanner({ onRead, onClose }: { onRead: (r: PackReading) => void; onClose: () => void }) {
  const [mode, setMode] = useState<"pick" | "camera" | "reading">("pick");
  const [error, setError] = useState<string | null>(null);
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
          onRead({ kind: "barcode", text: code });
        }
      } catch {
        /* a frame that can't be read: try the next one */
      } finally {
        busy = false;
      }
    }, FRAME_MS);
    return () => { done = true; clearInterval(timer); };
  }, [mode]); // eslint-disable-line react-hooks/exhaustive-deps

  /** Take the current camera frame as a photo (for the front of a pack, which has no barcode). */
  function takePhoto() {
    const v = video.current;
    if (!v || v.readyState < 2) return;
    const canvas = document.createElement("canvas");
    canvas.width = v.videoWidth;
    canvas.height = v.videoHeight;
    canvas.getContext("2d")!.drawImage(v, 0, 0);
    stopCamera();
    canvas.toBlob((b) => { if (b) void readPhoto(b); }, "image/jpeg", 0.92);
  }

  async function readPhoto(photo: Blob) {
    setMode("reading");
    setError(null);
    try {
      const small = await shrink(photo);
      const code = await readBarcode(small);
      if (code) return onRead({ kind: "barcode", text: code });
      const words = await readPackWords(small);
      if (words) return onRead({ kind: "words", text: words });
      setError("Couldn't read a barcode or a product name. Try again closer to the pack, in good light, or type the name.");
    } catch {
      setError("Couldn't read that photo. Try another one, or type the product name.");
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
          <h3 id="pack-scan-title">Scan a packaged product</h3>
          <button type="button" className="ghost icon-btn" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {mode === "camera" ? (
          <>
            <div className="pack-camera">
              <video ref={video} playsInline muted aria-label="Camera view" />
              <span className="pack-camera-frame" aria-hidden="true" />
            </div>
            <p className="muted small">
              Point at the <b>barcode</b>: it's read on its own. No barcode in view? Show the front of the pack with the
              brand and name, then <b>Take photo</b>.
            </p>
            <div className="pack-actions">
              <button type="button" className="primary" onClick={takePhoto}>Take photo</button>
              <button type="button" className="ghost" onClick={() => { stopCamera(); setMode("pick"); }}>Back</button>
            </div>
          </>
        ) : mode === "reading" ? (
          <p className="pack-reading" role="status"><span className="spinner" aria-hidden="true" /> Reading the pack…</p>
        ) : (
          <>
            <p className="muted small">
              For <b>packaged products</b> only: the barcode, or the front of the pack with the brand and name. Cooked or
              loose food (a curry, a thali) can't be read from a photo; tell MacBro about it instead.
            </p>
            <div className="pack-actions">
              {cameraOk && <button type="button" className="primary" onClick={startCamera}>📷 Use camera</button>}
              <button type="button" className={cameraOk ? "" : "primary"} onClick={() => file.current?.click()}>🖼 Upload a photo</button>
              <input ref={file} type="file" accept="image/*" hidden
                     onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) void readPhoto(f); }} />
            </div>
            <p className="muted tiny">The photo is read on your device and isn't uploaded. Only the barcode or the words read are searched.</p>
          </>
        )}
        {error && <p className="error small">{error}</p>}
      </div>
    </div>,
    document.body,
  );
}
