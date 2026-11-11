// A run that failed without a result, in the run dock: the fixed sentence
// `runFailureText` gives the failure, never the server's own text, and
// never a score or a pass or fail the run didn't earn (ROUNDS-00A-L03).

export function RunErrorOutput({ message }: { message: string }) {
  return (
    <pre
      className="mono"
      style={{
        fontSize: 12,
        color: 'var(--plum)',
        background: 'var(--bg-sunken)',
        padding: 10,
        borderRadius: 'var(--radius)',
        margin: 0,
        whiteSpace: 'pre-wrap',
      }}
    >
      {message}
    </pre>
  );
}
