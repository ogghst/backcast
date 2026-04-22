import { useState } from "react";

interface UseEntityDetailActions<T> {
  editModalOpen: boolean;
  selectedEntity: T | null;
  deleteModalOpen: boolean;
  historyOpen: boolean;
  openEdit: (entity: T) => void;
  closeEdit: () => void;
  openDelete: () => void;
  closeDelete: () => void;
  openHistory: () => void;
  closeHistory: () => void;
}

export function useEntityDetailActions<T>(): UseEntityDetailActions<T> {
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<T | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  const openEdit = (entity: T) => {
    setSelectedEntity(entity);
    setEditModalOpen(true);
  };

  const closeEdit = () => {
    setEditModalOpen(false);
    setSelectedEntity(null);
  };

  const openDelete = () => setDeleteModalOpen(true);
  const closeDelete = () => setDeleteModalOpen(false);
  const openHistory = () => setHistoryOpen(true);
  const closeHistory = () => setHistoryOpen(false);

  return {
    editModalOpen,
    selectedEntity,
    deleteModalOpen,
    historyOpen,
    openEdit,
    closeEdit,
    openDelete,
    closeDelete,
    openHistory,
    closeHistory,
  };
}
