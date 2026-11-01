import React, { useState, useEffect } from 'react';
import { Modal, Button, Input, Select, useToast } from '../../components/ui';
import { useCreateBrandMutation, useUpdateBrandMutation } from '../../api/brands';
import { usePodsQuery } from '../../api/team';
import type { Brand } from '../../types/brands';

export interface BrandModalProps {
  isOpen: boolean;
  onClose: () => void;
  brand?: Brand | null;
  defaultPodId?: string;
}

export const BrandModal: React.FC<BrandModalProps> = ({
  isOpen,
  onClose,
  brand,
  defaultPodId,
}) => {
  const toast = useToast();
  const { data: podsData } = usePodsQuery();
  const createMutation = useCreateBrandMutation();
  const updateMutation = useUpdateBrandMutation();

  const isEditing = !!brand;
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [podId, setPodId] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (brand) {
      setName(brand.name);
      setCode(brand.code);
      setPodId(brand.pod_id || '');
    } else {
      setName('');
      setCode('');
      setPodId(defaultPodId || (podsData?.items?.[0]?.id ?? ''));
    }
    setErrorMsg(null);
  }, [brand, defaultPodId, podsData, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !code.trim()) {
      setErrorMsg('Brand name and code are required.');
      return;
    }

    try {
      if (isEditing && brand) {
        await updateMutation.mutateAsync({
          id: brand.id,
          data: {
            name: name.trim(),
            code: code.trim().toUpperCase(),
            pod_id: podId || null,
          },
        });
        toast.success('Brand updated', `Brand "${name}" updated successfully.`);
      } else {
        await createMutation.mutateAsync({
          name: name.trim(),
          code: code.trim().toUpperCase(),
          pod_id: podId || null,
        });
        toast.success('Brand created', `Brand "${name}" (${code}) created successfully.`);
      }
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Operation failed';
      setErrorMsg(msg);
      toast.error('Failed to save brand', msg);
    }
  };

  const podOptions = [
    { value: '', label: 'Unassigned / Company-wide' },
    ...(podsData?.items || []).map((p) => ({ value: p.id, label: p.name })),
  ];

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Brand' : 'Create New Brand'}
      description="Brands represent client accounts or operating portfolios assigned to pods."
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="brand-form"
            isLoading={isPending}
          >
            {isEditing ? 'Save Changes' : 'Create Brand'}
          </Button>
        </div>
      }
    >
      <form id="brand-form" onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="rounded-ctl border border-bad/30 bg-bad/10 p-2.5 text-xs text-bad">
            {errorMsg}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Brand Name"
            placeholder="e.g. Aurora"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <Input
            label="Brand Code"
            placeholder="e.g. AUR"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />
        </div>

        <Select
          label="Assigned Pod"
          value={podId}
          options={podOptions}
          onChange={setPodId}
        />
      </form>
    </Modal>
  );
};
