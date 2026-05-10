import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CheckpointStepper from '../../pages/ai-coding/CheckpointStepper';

describe('CheckpointStepper', () => {
  const cps = [
    { label: 'Bug fix', ai_allowed: false },
    { label: 'Feature', ai_allowed: true },
    { label: 'Optimize', ai_allowed: true },
  ];

  it('marks past checkpoints as done and current as active', () => {
    render(
      <CheckpointStepper
        checkpoints={cps}
        currentIndex={1}
        passed={[true, false, false]}
        onSelect={() => {}}
      />
    );
    expect(screen.getByText('Bug fix').className).toContain('done');
    expect(screen.getByText('Feature').className).toContain('active');
  });

  it('calls onSelect with the clicked index', () => {
    const onSelect = vi.fn();
    render(<CheckpointStepper checkpoints={cps} currentIndex={0} passed={[false, false, false]} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('Optimize'));
    expect(onSelect).toHaveBeenCalledWith(2);
  });
});
