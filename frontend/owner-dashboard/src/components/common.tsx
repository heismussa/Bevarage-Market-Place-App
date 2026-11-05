import {
  orderStatusLabel,
  paymentStatusLabel,
} from "@beverage/api";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Inbox,
  Minus,
} from "lucide-react";
import type { ReactNode } from "react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api";
import { AVAILABILITY_LABELS, type AvailabilityValue } from "@/lib/types";
import { cn } from "@/lib/utils";

/* ------------------------------- Headers --------------------------------- */

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description ? <p className="mt-1 text-sm text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

/* -------------------------------- States --------------------------------- */

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <div className="rounded-full bg-surface-muted p-3 text-muted">
        {icon ?? <Inbox size={24} />}
      </div>
      <p className="font-semibold">{title}</p>
      {description ? <p className="max-w-sm text-sm text-muted">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <div className="rounded-full bg-danger-soft p-3 text-danger">
        <AlertTriangle size={24} />
      </div>
      <p className="font-semibold">Could not load this</p>
      <p className="max-w-sm text-sm text-muted">{errorMessage(error)}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          Try again
        </Button>
      ) : null}
    </div>
  );
}

/* -------------------------------- Badges --------------------------------- */

const ORDER_VARIANTS: Record<string, BadgeProps["variant"]> = {
  PENDING: "warning",
  ACCEPTED: "info",
  PREPARING: "info",
  READY: "primary",
  ASSIGNED: "info",
  OUT_FOR_DELIVERY: "info",
  COMPLETED: "success",
  REJECTED: "danger",
  CANCELLED: "danger",
};

export function OrderStatusBadge({ status }: { status: string }) {
  return <Badge variant={ORDER_VARIANTS[status] ?? "default"}>{orderStatusLabel(status)}</Badge>;
}

const PAYMENT_VARIANTS: Record<string, BadgeProps["variant"]> = {
  PENDING: "warning",
  PROCESSING: "info",
  SUCCESS: "success",
  FAILED: "danger",
  CANCELLED: "default",
  REFUNDED: "default",
};

export function PaymentStatusBadge({
  status,
  isCash,
}: {
  status: string;
  isCash?: boolean;
}) {
  return (
    <Badge variant={PAYMENT_VARIANTS[status] ?? "default"}>
      {paymentStatusLabel(status, { isCash })}
    </Badge>
  );
}

export function AvailabilityBadge({ status }: { status: AvailabilityValue }) {
  const variant: BadgeProps["variant"] =
    status === "AVAILABLE" ? "success" : status === "OUT_OF_STOCK" ? "danger" : "default";
  return <Badge variant={variant}>{AVAILABILITY_LABELS[status]}</Badge>;
}

/**
 * "+12.5%" pill driven only by the server's change percent string.
 * null means the previous period had no data, so we say so instead of inventing a number.
 */
export function ChangeBadge({
  percent,
  suffix = "vs previous",
}: {
  percent: string | null | undefined;
  suffix?: string;
}) {
  if (percent === null || percent === undefined || percent === "") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-muted">
        <Minus size={12} /> No previous data
      </span>
    );
  }
  const value = Number(percent);
  if (!Number.isFinite(value)) return null;
  const up = value > 0;
  const down = value < 0;
  const Icon = up ? ArrowUpRight : down ? ArrowDownRight : Minus;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span
        className={cn(
          "inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 font-semibold",
          up && "bg-success-soft text-success",
          down && "bg-danger-soft text-danger",
          !up && !down && "bg-surface-muted text-muted",
        )}
      >
        <Icon size={12} />
        {up ? "+" : ""}
        {value.toFixed(1).replace(/\.0$/, "")}%
      </span>
      <span className="text-muted">{suffix}</span>
    </span>
  );
}

/* ------------------------------- Pagination ------------------------------ */

export function Pagination({
  page,
  pageSize,
  count,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  count: number;
  onPageChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  if (count <= pageSize) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, count);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3 text-sm">
      <p className="text-muted">
        {from}-{to} of {count}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft size={14} /> Previous
        </Button>
        <span className="text-muted">
          Page {page} of {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next <ChevronRight size={14} />
        </Button>
      </div>
    </div>
  );
}
