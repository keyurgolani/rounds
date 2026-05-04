import { useCallback } from 'react';
import { api } from '../../api/client';
import { useCampaign } from '../../campaign/CampaignContext';
import { useCommandCenter } from '../CommandCenterProvider';
import TodoForm, { type TodoFormValue } from '../../todos/TodoForm';

export default function AddTodoView({ onComplete }: { onComplete: () => void }) {
  const { currentId, currentCampaign } = useCampaign();
  const cc = useCommandCenter();

  const handleSubmit = useCallback(
    async (value: TodoFormValue) => {
      // Mirror the create call signature used in todos/FAB.tsx so the
      // Command Center's "Add todo" produces an identical record.
      if (!currentId) throw new Error('Pick an active campaign first.');
      await api.post('/api/todos', {
        campaign_id: currentId,
        body: value.body,
        mentions: value.mentions,
        due_date: value.due_date,
        priority: value.priority,
      });
      window.dispatchEvent(new CustomEvent('rounds:todos-changed'));
      onComplete();
    },
    [currentId, onComplete],
  );

  return (
    <TodoForm
      onSubmit={handleSubmit}
      // Cancel/Escape inside the view returns to the Command Center
      // hub instead of dismissing the modal entirely — matches how the
      // other CC views behave (their Cancel button also bubbles up
      // an Escape that the global handler maps to cc.back()).
      onCancel={cc.back}
      campaignName={currentCampaign?.name}
      campaignMissing={!currentId}
      submitLabel="Add todo"
    />
  );
}
