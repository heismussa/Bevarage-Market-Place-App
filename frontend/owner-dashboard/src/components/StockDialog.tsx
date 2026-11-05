import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import { useSetStock } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import type { OwnerProduct } from "@/lib/types";

/** Set (or restock) a product's stock via PATCH /owner/products/{id}/stock/. */
export function StockDialog({
  product,
  mode = "set",
  onClose,
}: {
  product: OwnerProduct | null;
  mode?: "set" | "restock";
  onClose: () => void;
}) {
  const toast = useToast();
  const setStock = useSetStock();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (product) {
      setValue(String(product.stock_quantity ?? 0));
      setError(null);
    }
  }, [product]);

  if (!product) return null;
  const current = product.stock_quantity ?? 0;

  const submit = async () => {
    const parsed = Number(value);
    if (!/^\d+$/.test(value.trim()) || !Number.isSafeInteger(parsed)) {
      setError("Enter a whole number, 0 or more.");
      return;
    }
    try {
      await setStock.mutateAsync({ productId: product.id, stock_quantity: parsed });
      toast.success(`${product.name} stock set to ${parsed}.`);
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const addQuick = (amount: number) => {
    const base = Number(value);
    setValue(String((Number.isFinite(base) ? base : current) + amount));
    setError(null);
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title={mode === "restock" ? `Restock ${product.name}` : `Update stock: ${product.name}`}
      description={`Current stock: ${current} · alert at ${product.low_stock_threshold ?? 0}`}
      className="max-w-md"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={setStock.isPending}>
            Cancel
          </Button>
          <Button onClick={() => void submit()} loading={setStock.isPending}>
            Save stock
          </Button>
        </>
      }
    >
      <Field label="New stock quantity" htmlFor="stock-qty" error={error ?? undefined}>
        <Input
          id="stock-qty"
          inputMode="numeric"
          autoFocus
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setError(null);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter") void submit();
          }}
        />
      </Field>
      <div className="mt-3 flex flex-wrap gap-2">
        {[10, 24, 50, 100].map((amount) => (
          <Button
            key={amount}
            type="button"
            variant="outline"
            size="sm"
            onClick={() => addQuick(amount)}
          >
            +{amount}
          </Button>
        ))}
      </div>
    </Dialog>
  );
}
