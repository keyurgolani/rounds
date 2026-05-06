// Export pipeline entry point. Each format owns its own builder; this
// file just hosts the small download helper they all share.

export type ExportFormat = 'pdf' | 'docx' | 'html' | 'markdown' | 'text' | 'json';

export type ExportTarget = {
  filenameBase: string; // resume slug or sanitized name
};

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Revoke after a short delay so the browser has time to start the download.
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

export function downloadString(content: string, filename: string, mime: string): void {
  downloadBlob(new Blob([content], { type: mime }), filename);
}
