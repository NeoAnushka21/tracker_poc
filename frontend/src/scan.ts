/** Reading a product's barcode from the camera or a photo, in the browser (2026-10-01). Nothing is
 *  uploaded: the photo stays on the phone; only the barcode number goes on to the Open Food Facts
 *  search, as if it had been typed.
 *
 *  Barcode only (owner, 2026-10-01): every packaged product has one, and reading the brand and name
 *  off the front of a pack (tried with Tesseract.js) failed on real photos.
 *
 *  - The browser's own BarcodeDetector where there is one (Chrome on Android), first.
 *  - zxing-wasm (MIT, ZXing-C++) everywhere, its .wasm bundled with the app. Loaded on first use,
 *    so it costs nothing for anyone who never scans. */

const BARCODE = /^\d{8,14}$/;

type ZXing = typeof import("zxing-wasm/reader");
let zxing: Promise<ZXing> | null = null;

function loadZXing(): Promise<ZXing> {
  zxing ??= Promise.all([import("zxing-wasm/reader"), import("zxing-wasm/reader/zxing_reader.wasm?url")])
    .then(([m, wasm]) => {
      // Our own copy of the .wasm, not the library's default CDN (the CSP allows only our files).
      m.prepareZXingModule({
        overrides: { locateFile: (path: string, prefix: string) => (path.endsWith(".wasm") ? wasm.default : prefix + path) },
      });
      return m;
    });
  return zxing;
}

type Detector = { detect: (image: ImageBitmapSource) => Promise<{ rawValue: string }[]> };
type DetectorClass = { new (o: { formats: string[] }): Detector; getSupportedFormats(): Promise<string[]> };
let native: Promise<Detector | null> | null = null;

function nativeDetector(): Promise<Detector | null> {
  native ??= (async () => {
    const BD = (globalThis as { BarcodeDetector?: DetectorClass }).BarcodeDetector;
    if (!BD) return null;
    try {
      const supported = await BD.getSupportedFormats();
      const formats = ["ean_13", "ean_8", "upc_a", "upc_e"].filter((f) => supported.includes(f));
      return formats.length ? new BD({ formats }) : null;
    } catch {
      return null;
    }
  })();
  return native;
}

/** The product barcode (EAN/UPC digits) in a photo or camera frame, or null. Photos are read at
 *  full size: shrinking one first made a small barcode in a wide shot unreadable (owner's test,
 *  2026-10-01). zxing scales big images down itself when that helps. */
export async function readBarcode(image: Blob | ImageData): Promise<string | null> {
  const detector = await nativeDetector();
  if (detector) {
    try {
      const hits = await detector.detect(image instanceof Blob ? await createImageBitmap(image) : image);
      const hit = hits.find((h) => BARCODE.test(h.rawValue));
      if (hit) return hit.rawValue;
    } catch {
      /* fall through to zxing */
    }
  }
  const m = await loadZXing();
  const found = await m.readBarcodes(image, {
    formats: ["EAN13", "EAN8", "UPCA", "UPCE"], tryHarder: true, tryRotate: true, tryInvert: true,
    tryDownscale: true, tryDenoise: true, maxNumberOfSymbols: 1,
  });
  return found.find((r) => r.isValid && BARCODE.test(r.text))?.text ?? null;
}
