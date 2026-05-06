// Minimal ambient type for the browser entry of `mammoth`. We only
// use extractRawText({ arrayBuffer }) and read .value.

declare module 'mammoth/mammoth.browser' {
  export function extractRawText(options: {
    arrayBuffer: ArrayBuffer;
  }): Promise<{ value: string; messages: unknown[] }>;
}
