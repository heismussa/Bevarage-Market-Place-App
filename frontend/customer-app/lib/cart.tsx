import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState, type ReactElement } from "react";

import { ConfirmDialog } from "@/components/ConfirmDialog";

import { api, unwrap } from "./api";
import { errorMessage, isApiError } from "./errors";
import { keys } from "./query";
import { useToast } from "./toast";
import type { Cart } from "./types";

export function useCart(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: keys.cart,
    queryFn: async () => unwrap(await api.GET("/api/v1/cart/")),
    enabled: options.enabled ?? true,
  });
}

/** Item count for the tab badge. Shares the cart query cache. */
export function useCartCount(): number {
  const { data } = useQuery({
    queryKey: keys.cart,
    queryFn: async () => unwrap(await api.GET("/api/v1/cart/")),
    select: (cart: Cart) => cart.item_count,
  });
  return data ?? 0;
}

export function useCartMutations() {
  const queryClient = useQueryClient();
  const setCart = (cart: Cart) => queryClient.setQueryData(keys.cart, cart);

  const updateQuantity = useMutation({
    mutationFn: async ({ id, quantity }: { id: number; quantity: number }) =>
      unwrap(
        await api.PATCH("/api/v1/cart/items/{id}/", {
          params: { path: { id, pk: id } },
          body: { quantity },
        }),
      ),
    onSuccess: setCart,
  });

  const removeItem = useMutation({
    mutationFn: async (id: number) =>
      unwrap(
        await api.DELETE("/api/v1/cart/items/{id}/", {
          params: { path: { id, pk: id } },
        }),
      ),
    onSuccess: setCart,
  });

  const clearCart = useMutation({
    mutationFn: async () => unwrap(await api.DELETE("/api/v1/cart/")),
    onSuccess: setCart,
  });

  return { updateQuantity, removeItem, clearCart };
}

type Pending = { productId: number; quantity: number };

/**
 * Add-to-cart with the CART_STORE_CONFLICT flow: the server answers 409, we ask
 * the customer, and on confirm retry with ?replace=true.
 * Render `conflictDialog` somewhere in the screen.
 */
export function useAddToCart(): {
  addToCart: (productId: number, quantity?: number) => Promise<boolean>;
  isAdding: boolean;
  conflictDialog: ReactElement;
} {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [pending, setPending] = useState<Pending | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  const send = useCallback(
    async (productId: number, quantity: number, replace: boolean) => {
      const cart = unwrap(
        await api.POST("/api/v1/cart/items/", {
          params: { query: replace ? { replace: true } : {} },
          body: { product_id: productId, quantity },
        }),
      );
      queryClient.setQueryData(keys.cart, cart);
    },
    [queryClient],
  );

  const addToCart = useCallback(
    async (productId: number, quantity = 1) => {
      setIsAdding(true);
      try {
        await send(productId, quantity, false);
        toast.show("Added to cart", "success");
        return true;
      } catch (error) {
        if (isApiError(error, "CART_STORE_CONFLICT")) {
          setPending({ productId, quantity });
        } else {
          toast.show(errorMessage(error), "error");
        }
        return false;
      } finally {
        setIsAdding(false);
      }
    },
    [send, toast],
  );

  const confirmReplace = useCallback(async () => {
    if (!pending) return;
    setIsAdding(true);
    try {
      await send(pending.productId, pending.quantity, true);
      toast.show("Started a new cart", "success");
    } catch (error) {
      toast.show(errorMessage(error), "error");
    } finally {
      setIsAdding(false);
      setPending(null);
    }
  }, [pending, send, toast]);

  const conflictDialog = (
    <ConfirmDialog
      visible={pending !== null}
      title="Start a new cart?"
      message="Your cart has items from another store. Adding this will clear it and start a new cart."
      confirmLabel="Start new cart"
      loading={isAdding}
      onConfirm={() => void confirmReplace()}
      onCancel={() => setPending(null)}
    />
  );

  return { addToCart, isAdding, conflictDialog };
}
