import { useCallback } from 'react';
import { api } from '../../api/client';
import { useCampaign } from '../../campaign/CampaignContext';
import TodoForm, { type TodoFormValue } from '../../todos/TodoForm';

export default function AddTodoView({ onComplete }: { onComplete: () => void }) {
  const { currentId, currentCampaign } = useCampaign();

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
      onCancel={onComplete}
      campaignName={currentCampaign?.name}
      campaignMissing={!currentId}
      submitLabel="Add todo"
    />
  );
}
