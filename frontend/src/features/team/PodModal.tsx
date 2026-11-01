import React, { useState, useEffect } from 'react';
import { Modal, Button, Input, useToast } from '../../components/ui';
import { useCreatePodMutation, useUpdatePodMutation } from '../../api/team';
import type { Pod } from '../../types/team';

export interface PodModalProps {
  isOpen: boolean;
  onClose: () => void;
  pod?: Pod | null;
}

export const PodModal: React.FC<PodModalProps> = ({ isOpen, onClose, pod }) => {
  const toast = useToast();
  const createMutation = useCreatePodMutation();
  const updateMutation = useUpdatePodMutation();

  const isEditing = !!pod;
  const [name, setName] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (pod) {
      setName(pod.name);
      setIsActive(pod.is_active);
    } else {
      setName('');
      setIsActive(true);
    }
    setErrorMsg(null);
  }, [pod, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg('Pod name is required.');
      return;
    }

    try {
      if (isEditing && pod) {
        await updateMutation.mutateAsync({
          id: pod.id,
          data: { name: name.trim(), is_active: isActive },
        });
        toast.success('Pod updated', `Pod "${name}" updated successfully.`);
      } else {
        await createMutation.mutateAsync({
          name: name.trim(),
        });
        toast.success('Pod created', `Pod "${name}" created successfully.`);
      }
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Operation failed';
      setErrorMsg(msg);
      toast.error('Failed to save pod', msg);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Pod' : 'Create Pod'}
      description="Pods group employees and define management boundaries for leads."
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="pod-form"
            isLoading={isPending}
          >
            {isEditing ? 'Save Changes' : 'Create Pod'}
          </Button>
        </div>
      }
    >
      <form id="pod-form" onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="rounded-ctl border border-bad/30 bg-bad/10 p-2.5 text-xs text-bad">
            {errorMsg}
          </div>
        )}

        <Input
          label="Pod Name"
          placeholder="e.g. Pod Alpha"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />

        {isEditing && (
          <label className="flex items-center gap-2 pt-1 text-xs text-ink cursor-pointer select-none">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="rounded-ctl border-border-strong text-accent-600 focus:ring-accent-600"
            />
            <span className="font-medium">Pod is active</span>
          </label>
        )}
      </form>
    </Modal>
  );
};
