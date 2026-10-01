/** Reading a product pack from a photo or the camera, in the browser (2026-10-01). Nothing is
 *  uploaded: the photo stays on the phone; only the barcode or the words read go on to the
 *  Open Food Facts search, as if they had been typed.
 *
 *  - Barcodes: zxing-wasm (MIT, ZXing-C++), its .wasm bundled with the app.
 *  - Words on the front of the pack (brand and product name): Tesseract.js (Apache-2.0), served
 *    from /ocr/ (vite.config.ts copies it from node_modules). It is only downloaded (about 6 MB)
 *    the first time a photo has no barcode.
 *  Both libraries load on first use, so they cost nothing for anyone who never scans. */

const BARCODE = /^\d{8,14}$/;
const MAX_SIDE = 1600;           // big phone photos are shrunk first: faster, and no less readable

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

/** The product barcode (EAN/UPC digits) in an image or camera frame, or null. */
export async function readBarcode(image: Blob | ImageData): Promise<string | null> {
  const m = await loadZXing();
  const found = await m.readBarcodes(image, {
    formats: ["EAN13", "EAN8", "UPCA", "UPCE"], tryHarder: true, maxNumberOfSymbols: 1,
  });
  return found.find((r) => r.isValid && BARCODE.test(r.text))?.text ?? null;
}

/** A photo, shrunk so its longer side is at most MAX_SIDE pixels. */
export async function shrink(photo: Blob): Promise<Blob> {
  const bitmap = await createImageBitmap(photo);
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  if (scale === 1) { bitmap.close(); return photo; }
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return new Promise((ok, fail) => canvas.toBlob((b) => (b ? ok(b) : fail(new Error("Couldn't read the photo"))), "image/jpeg", 0.9));
}

// Print that is on most packs but never part of the product's name.
const NOT_A_NAME = new Set(["net", "wt", "weight", "veg", "non", "new", "pack", "mrp", "rs", "fssai", "lic", "no",
  "ingredients", "nutrition", "best", "before", "mfd", "use", "by", "per", "serving", "approx", "contains"]);

type OcrWord = { text: string; confidence: number; bbox: { x0: number; y0: number; x1: number; y1: number } };

/** The words most likely to be the brand and product name: the largest clear print on the pack. */
export function packWords(words: OcrWord[]): string {
  const clean = words
    .map((w) => ({ ...w, text: w.text.replace(/[^\p{L}\p{N}&'-]/gu, "") }))
    .filter((w) => w.confidence >= 55 && /\p{L}{2,}/u.test(w.text) && !NOT_A_NAME.has(w.text.toLowerCase()));
  if (!clean.length) return "";
  const height = (w: OcrWord) => w.bbox.y1 - w.bbox.y0;
  const tallest = Math.max(...clean.map(height));
  return clean
    .filter((w) => height(w) >= 0.45 * tallest)
    .sort((a, b) => height(b) - height(a))
    .slice(0, 6)
    .sort((a, b) => a.bbox.y0 - b.bbox.y0 || a.bbox.x0 - b.bbox.x0)   // back in reading order
    .map((w) => w.text)
    .join(" ");
}

/** Brand and product name read off the front of a pack ("Modern Multigrain Bread"), or "". */
export async function readPackWords(photo: Blob): Promise<string> {
  const { createWorker } = await import("tesseract.js");
  const worker = await createWorker("eng", 1, {
    workerPath: "/ocr/worker.min.js", corePath: "/ocr/", langPath: "/ocr/", gzip: true,
    workerBlobURL: false,          // a same-origin worker file: the CSP allows no blob: scripts
  });
  try {
    const { data } = await worker.recognize(photo, {}, { blocks: true });
    const words = (data.blocks ?? []).flatMap((b) => b.paragraphs.flatMap((p) => p.lines.flatMap((l) => l.words)));
    return packWords(words);
  } finally {
    await worker.terminate();
  }
}
