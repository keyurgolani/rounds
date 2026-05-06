// Client-side text extraction. Used by the AI import flow: drop in a
// PDF / DOCX / MD / TXT, get back plain text, post that to
// /api/ai/import.
//
// PDF parsing uses pdfjs-dist with its bundled worker. We feed the
// fast text path first; if the result is suspiciously short (under
// 100 non-whitespace characters) we treat the document as scanned and
// surface a clear error — server-side OCR fallback is wired in a
// later phase.

import * as pdfjsLib from 'pdfjs-dist';
// pdfjs requires a worker; Vite resolves the URL at build time.
import workerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

const MIN_USEFUL_CHARS = 100;

export type ExtractedText = {
  text: string;
  source: 'pdf' | 'docx' | 'text' | 'markdown';
};

export async function extractText(file: File): Promise<ExtractedText> {
  const name = file.name.toLowerCase();
  const type = file.type;

  if (type === 'application/pdf' || name.endsWith('.pdf')) {
    return { text: await extractPdf(file), source: 'pdf' };
  }
  if (
    type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    name.endsWith('.docx')
  ) {
    return { text: await extractDocx(file), source: 'docx' };
  }
  if (name.endsWith('.md') || name.endsWith('.markdown')) {
    return { text: await file.text(), source: 'markdown' };
  }
  // Plain text fallback covers .txt and any unrecognized text-like file.
  return { text: await file.text(), source: 'text' };
}

async function extractPdf(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  const doc = await pdfjsLib.getDocument({ data: new Uint8Array(buf) }).promise;
  const chunks: string[] = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    const items = content.items as Array<{ str?: string }>;
    chunks.push(items.map((it) => it.str ?? '').join(' '));
  }
  const text = chunks.join('\n').replace(/[ \t]+/g, ' ').trim();
  if (text.replace(/\s+/g, '').length < MIN_USEFUL_CHARS) {
    throw new Error(
      "Couldn't extract text from this PDF (it may be a scanned image). " +
        'Save it from a text-based source, or paste the text into a .txt file.',
    );
  }
  return text;
}

async function extractDocx(file: File): Promise<string> {
  // mammoth is a heavyweight import — pull it in lazily so the studio
  // doesn't pay for it on every page load.
  const mammoth = await import('mammoth/mammoth.browser');
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer });
  const text = (result?.value ?? '').trim();
  if (!text) {
    throw new Error("Couldn't extract text from this DOCX.");
  }
  return text;
}
