import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Textarea } from "@/components/ui/input";

/** Collects the reason required to reject or cancel an order (shown to the customer). */
export function ReasonDialog({
  open,
  title,
  confirmLabel,
  loading,
  onConfirm,
  onClose,
  serverError,
}: {
  open: boolean;
  title: string;
  confirmLabel: string;
  loading?: boolean;
  serverError?: string | null;
  onConfirm: (reason: string) => void;
  onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (open) {
      setReason("");
      setTouched(false);
    }
  }, [open]);

  const trimmed = reason.trim();
  const error =
    (touched && !trimmed ? "A reason is required." : undefined) ??
    serverError ??
    undefined;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      description="The customer will see this reason. Stock is returned to the store."
      className="max-w-md"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Keep order
          </Button>
          <Button
            variant="destructive"
            loading={loading}
            onClick={() => {
              setTouched(true);
              if (trimmed) onConfirm(trimmed);
            }}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <Field label="Reason" htmlFor="order-reason" error={error}>
        <Textarea
          id="order-reason"
          value={reason}
          maxLength={500}
          placeholder="e.g. Item is out of stock"
          onChange={(event) => setReason(event.target.value)}
        />
      </Field>
    </Dialog>
  );
}
