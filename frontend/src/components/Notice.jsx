export default function Notice({ note, onDismiss }) {
  if (!note) return null;
  return (
    <div className={`notice ${note.kind === 'error' ? 'error' : ''}`} role={note.kind === 'error' ? 'alert' : 'status'}>
      <span>{note.text}</span>
      <button type="button" className="ghost" aria-label="Dismiss message" onClick={onDismiss}>
        ×
      </button>
    </div>
  );
}
