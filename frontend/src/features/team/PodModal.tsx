import React, { useState, useEffect } from 'react';
import { Modal, Button, Input, useToast } from '../../components/ui';
import { useCreatePodMutation, useUpdatePodMutation, useDeletePodMutation } from '../../api/team';
import { showApiErrorToast } from '../../api/errorMapping';
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
  const deleteMutation = useDeletePodMutation();

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
      showApiErrorToast(err, toast, 'Failed to save pod');
    }
  };

  const handleDelete = async () => {
    if (!pod || !window.confirm(`Are you sure you want to delete pod "${pod.name}"?`)) return;
    try {
      await deleteMutation.mutateAsync(pod.id);
      toast.success('Pod deleted', `Pod "${pod.name}" has been removed.`);
      onClose();
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to delete pod');
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Pod' : 'Create Pod'}
      description="Pods group employees and define management boundaries for leads."
      footer={
        <div className="flex items-center justify-between w-full">
          {isEditing && pod ? (
            <Button
              variant="destructive"
              size="sm"
              type="button"
              onClick={handleDelete}
              isLoading={deleteMutation.isPending}
            >
              Delete Pod
            </Button>
          ) : (
            <div />
          )}
          <div className="flex items-center gap-2">
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

