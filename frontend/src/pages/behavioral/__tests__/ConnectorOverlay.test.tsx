import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ConnectorOverlay } from '../ConnectorOverlay';

describe('ConnectorOverlay onTop', () => {
  it('sits behind the grid by default (z-index 1)', () => {
    const { container } = render(<ConnectorOverlay connectors={[]} />);
    expect(container.querySelector('svg')?.getAttribute('style')).toContain('z-index: 1');
  });

  it('raises above the grid when onTop is set (z-index 5)', () => {
    const { container } = render(<ConnectorOverlay connectors={[]} onTop />);
    expect(container.querySelector('svg')?.getAttribute('style')).toContain('z-index: 5');
  });
});
