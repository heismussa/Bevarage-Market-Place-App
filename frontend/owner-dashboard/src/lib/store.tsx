import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { useStoresQuery } from "@/lib/queries";
import type { OwnerStore } from "@/lib/types";

const STORAGE_KEY = "beverage_owner_store_id";

type StoreContextValue = {
  stores: OwnerStore[];
  /** Currently selected store, or undefined when the owner has none yet. */
  store: OwnerStore | undefined;
  isLoading: boolean;
  error: unknown;
  refetch: () => void;
  selectStore: (id: number) => void;
};

const StoreContext = createContext<StoreContextValue | null>(null);

function readStoredId(): number | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value ? Number(value) : null;
  } catch {
    return null;
  }
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const query = useStoresQuery();
  const [selectedId, setSelectedId] = useState<number | null>(readStoredId);

  const stores = useMemo(() => query.data ?? [], [query.data]);
  const store = useMemo(
    () => stores.find((item) => item.id === selectedId) ?? stores[0],
    [stores, selectedId],
  );

  const selectStore = useCallback((id: number) => {
    setSelectedId(id);
    try {
      localStorage.setItem(STORAGE_KEY, String(id));
    } catch {
      /* ignore */
    }
  }, []);

  const refetch = useCallback(() => {
    void query.refetch();
  }, [query]);

  const value = useMemo<StoreContextValue>(
    () => ({
      stores,
      store,
      isLoading: query.isLoading,
      error: query.error,
      refetch,
      selectStore,
    }),
    [stores, store, query.isLoading, query.error, refetch, selectStore],
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreContextValue {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used inside StoreProvider");
  return ctx;
}
