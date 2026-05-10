import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ModelSwitcher from '../../components/ai/ModelSwitcher';

// ModelSwitcher was redesigned from a native <select> into a custom
// button + listbox dropdown so it can render full-width inside the
// chat rail and group items by provider. The trigger has
// aria-haspopup="listbox" and the menu only mounts when open.

describe('ModelSwitcher', () => {
  const models = [
    { provider_id: 'p1', provider_label: 'Anthropic', kind: 'anthropic', model: 'claude-opus-4-7' },
    { provider_id: 'p1', provider_label: 'Anthropic', kind: 'anthropic', model: 'claude-sonnet-4-6' },
    { provider_id: 'p2', provider_label: 'OpenAI', kind: 'openai', model: 'gpt-4o-mini' },
  ];

  function openMenu() {
    fireEvent.click(screen.getByRole('button', { name: /AI model/i }));
  }

  it('lists every (provider, model) pair plus a Default entry', () => {
    render(<ModelSwitcher models={models} value={null} onChange={() => {}} />);
    openMenu();
    const options = screen.getAllByRole('option');
    // 3 model rows + the "Default model" option at index 0.
    expect(options).toHaveLength(4);
    expect(options[0]).toHaveTextContent(/Default model/);
    expect(options[1]).toHaveTextContent('claude-opus-4-7');
    expect(options[3]).toHaveTextContent('gpt-4o-mini');
  });

  it('emits {provider_id, model} when a model is picked', () => {
    const onChange = vi.fn();
    render(<ModelSwitcher models={models} value={null} onChange={onChange} />);
    openMenu();
    fireEvent.click(screen.getByRole('option', { name: /gpt-4o-mini/ }));
    expect(onChange).toHaveBeenCalledWith({ provider_id: 'p2', model: 'gpt-4o-mini' });
  });

  it('emits null when "Default model" is picked', () => {
    const onChange = vi.fn();
    render(
      <ModelSwitcher
        models={models}
        value={{ provider_id: 'p1', model: 'claude-opus-4-7' }}
        onChange={onChange}
      />,
    );
    openMenu();
    fireEvent.click(screen.getByRole('option', { name: /Default model/ }));
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
