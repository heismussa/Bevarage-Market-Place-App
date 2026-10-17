/**
 * Human labels for enums (FRONTEND_HANDOFF.md section 3).
 * Never invent statuses the server did not send.
 */

export const ORDER_STATUS_LABELS = {
  PENDING: "Pending",
  ACCEPTED: "Accepted",
  REJECTED: "Rejected",
  PREPARING: "Preparing",
  READY: "Ready",
  ASSIGNED: "Assigned",
  OUT_FOR_DELIVERY: "Out for delivery",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
} as const;

export type OrderStatus = keyof typeof ORDER_STATUS_LABELS;

export const PAYMENT_STATUS_LABELS = {
  PENDING: {
    cash: "Pay on delivery",
    mobile: "Not paid yet",
  },
  PROCESSING: {
    cash: "Processing",
    mobile: "Waiting for approval on your phone",
  },
  SUCCESS: {
    cash: "Paid",
    mobile: "Paid",
  },
  FAILED: {
    cash: "Payment failed",
    mobile: "Payment failed",
  },
  CANCELLED: {
    cash: "Not charged",
    mobile: "Not charged",
  },
  REFUNDED: {
    cash: "Refunded",
    mobile: "Refunded",
  },
} as const;

export type PaymentStatus = keyof typeof PAYMENT_STATUS_LABELS;

export const PAYMENT_METHOD_LABELS = {
  CASH: "Cash",
  MPESA: "M-Pesa",
  TIGO_PESA: "Tigo Pesa",
  AIRTEL_MONEY: "Airtel Money",
  CARD: "Card",
  BANK: "Bank",
} as const;

export type PaymentMethod = keyof typeof PAYMENT_METHOD_LABELS;

export function orderStatusLabel(status: string | null | undefined): string {
  if (!status) return "";
  return ORDER_STATUS_LABELS[status as OrderStatus] ?? status;
}

/**
 * Payment status label. Pass isCash=true for cash orders so PENDING reads
 * "Pay on delivery" instead of "Not paid yet".
 */
export function paymentStatusLabel(
  status: string | null | undefined,
  options: { isCash?: boolean } = {},
): string {
  if (!status) return "";
  const entry = PAYMENT_STATUS_LABELS[status as PaymentStatus];
  if (!entry) return status;
  return options.isCash ? entry.cash : entry.mobile;
}

export function paymentMethodLabel(method: string | null | undefined): string {
  if (!method) return "";
  return PAYMENT_METHOD_LABELS[method as PaymentMethod] ?? method;
}

/** Statuses the customer UI should not offer as filters or steps today. */
export const HIDDEN_ORDER_STATUSES = [
  "ASSIGNED",
  "OUT_FOR_DELIVERY",
] as const;

/** Payment methods checkout must not offer. */
export const HIDDEN_PAYMENT_METHODS = ["CARD", "BANK"] as const;
