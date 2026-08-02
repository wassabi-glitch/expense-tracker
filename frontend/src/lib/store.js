import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useSidebarStore = create(
  persist(
    (set) => ({
      isPinned: true,
      togglePin: () => set((state) => ({ isPinned: !state.isPinned })),
    }),
    {
      name: "sidebar-storage", // Key used in localStorage
    }
  )
);
