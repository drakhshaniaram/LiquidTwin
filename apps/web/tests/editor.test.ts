import { describe, expect, it } from 'vitest';

import { commitHistory, createHistory, redoHistory, undoHistory } from '../src/editor/history';

describe('editor history', () => {
  it('undoes and redoes immutable document changes', () => {
    const initial = createHistory({ nodes: [] as string[] });
    const withTank = commitHistory(initial, { nodes: ['tank-1'] });
    const withLine = commitHistory(withTank, { nodes: ['tank-1'], elements: ['line-1'] });

    expect(undoHistory(withLine).present).toEqual({ nodes: ['tank-1'] });
    expect(redoHistory(undoHistory(withLine)).present).toEqual(withLine.present);
  });

  it('caps undo depth at 200 snapshots', () => {
    let history = createHistory(0);
    for (let value = 1; value <= 250; value += 1) {
      history = commitHistory(history, value);
    }

    expect(history.past).toHaveLength(200);
    expect(history.present).toBe(250);
    expect(undoHistory(history).present).toBe(249);
  });

  it('clears redo after a new edit', () => {
    const history = commitHistory(commitHistory(createHistory(0), 1), 2);
    const undone = undoHistory(history);
    expect(undone.future).toEqual([2]);
    expect(commitHistory(undone, 3).future).toEqual([]);
  });
});
