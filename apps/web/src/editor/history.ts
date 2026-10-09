export type EditorHistory<T> = {
  past: T[];
  present: T;
  future: T[];
  limit: number;
};

export function createHistory<T>(present: T, limit = 200): EditorHistory<T> {
  return { past: [], present, future: [], limit };
}

export function commitHistory<T>(history: EditorHistory<T>, present: T): EditorHistory<T> {
  return {
    past: [...history.past, history.present].slice(-history.limit),
    present,
    future: [],
    limit: history.limit,
  };
}

export function undoHistory<T>(history: EditorHistory<T>): EditorHistory<T> {
  if (history.past.length === 0) return history;
  const present = history.past.at(-1)!;
  return {
    past: history.past.slice(0, -1),
    present,
    future: [history.present, ...history.future],
    limit: history.limit,
  };
}

export function redoHistory<T>(history: EditorHistory<T>): EditorHistory<T> {
  if (history.future.length === 0) return history;
  const [present, ...future] = history.future;
  return {
    past: [...history.past, history.present].slice(-history.limit),
    present,
    future,
    limit: history.limit,
  };
}
