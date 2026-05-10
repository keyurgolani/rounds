import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ModelSwitcher from '../../components/ai/ModelSwitcher';

describe('ModelSwitcher', () => {
  const models = [
    { provider_id: 'p1', provider_label: 'Anthropic', kind: 'anthropic', model: 'claude-opus-4-7' },
    { provider_id: 'p1', provider_label: 'Anthropic', kind: 'anthropic', model: 'claude-sonnet-4-6' },
    { provider_id: 'p2', provider_label: 'OpenAI', kind: 'openai', model: 'gpt-4o-mini' },
  ];

  it('lists every (provider, model) pair', () => {
    render(<ModelSwitcher models={models} value={null} onChange={() => {}} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    const options = screen.getAllByRole('option');
    // 3 model rows + the "Default" option at index 0.
    expect(options).toHaveLength(4);
    expect(options[1]).toHaveTextContent('claude-opus-4-7');
    expect(options[3]).toHaveTextContent('gpt-4o-mini');
  });

  it('emits {provider_id, model} on change', () => {
    const onChange = vi.fn();
    render(<ModelSwitcher models={models} value={null} onChange={onChange} />);
    fireEvent.change(screen.getByRole('combobox'), {
      target: { value: 'p2::gpt-4o-mini' },
    });
    expect(onChange).toHaveBeenCalledWith({ provider_id: 'p2', model: 'gpt-4o-mini' });
  });

  it('emits null when "Default" is picked', () => {
    const onChange = vi.fn();
    render(<ModelSwitcher models={models} value={{ provider_id: 'p1', model: 'claude-opus-4-7' }} onChange={onChange} />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '' } });
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
