import {
  HIDDEN_ORDER_STATUSES,
  ORDER_STATUS_LABELS,
  PAYMENT_STATUS_LABELS,
  formatDateTime,
  formatMoney,
  paymentMethodLabel,
} from "@beverage/api";
import { Download, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import {
  EmptyState,
  ErrorState,
  OrderStatusBadge,
  PageHeader,
  Pagination,
  PaymentStatusBadge,
} from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { downloadOrdersCsv, errorMessage } from "@/lib/api";
import { useOrders } from "@/lib/queries";
import { useStore } from "@/lib/store";
import { useToast } from "@/lib/toast";
import type { OrderStatusValue, PaymentStatusValue } from "@/lib/types";

const PAGE_SIZE = 20;

const STATUS_OPTIONS = (Object.keys(ORDER_STATUS_LABELS) as OrderStatusValue[]).filter(
  (status) => !(HIDDEN_ORDER_STATUSES as readonly string[]).includes(status),
);
const PAYMENT_OPTIONS = Object.keys(PAYMENT_STATUS_LABELS) as PaymentStatusValue[];

export default function OrdersPage() {
  const { store } = useStore();
  const toast = useToast();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [exporting, setExporting] = useState(false);

  const status = (params.get("status") ?? "") as OrderStatusValue | "";
  const paymentStatus = (params.get("payment_status") ?? "") as PaymentStatusValue | "";
  const search = params.get("search") ?? "";
  const dateFrom = params.get("date_from") ?? "";
  const dateTo = params.get("date_to") ?? "";
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);

  const [searchInput, setSearchInput] = useState(search);
  useEffect(() => setSearchInput(search), [search]);

  const update = (changes: Record<string, string | null>, resetPage = true) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (resetPage) next.delete("page");
    setParams(next, { replace: true });
  };

  // Debounce the search box.
  useEffect(() => {
    if (searchInput === search) return;
    const timer = window.setTimeout(() => update({ search: searchInput.trim() || null }), 350);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  const filters = {
    status,
    payment_status: paymentStatus,
    search,
    date_from: dateFrom,
    date_to: dateTo,
    page,
    page_size: PAGE_SIZE,
  };
  const query = useOrders(store?.id, filters);

  const hasFilters = Boolean(status || paymentStatus || search || dateFrom || dateTo);
  const dateRangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo);

  const exportCsv = async () => {
    if (!store) return;
    setExporting(true);
    try {
      const filename = await downloadOrdersCsv(store.id, {
        status: status || undefined,
        payment_status: paymentStatus || undefined,
        search: search || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      toast.success(`Exported ${filename}`);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setExporting(false);
    }
  };

  const orders = query.data?.results ?? [];

  return (
    <>
      <PageHeader
        title="Orders"
        description="Mobile-money orders appear after payment succeeds; cash orders appear at once."
        actions={
          <Button variant="outline" onClick={exportCsv} loading={exporting}>
            <Download size={16} /> Export CSV
          </Button>
        }
      />

      <Card>
        <div className="grid gap-3 border-b border-border p-4 sm:grid-cols-2 lg:grid-cols-6">
          <div className="relative sm:col-span-2">
            <Search size={16} className="absolute top-3 left-3 text-muted" />
            <Input
              aria-label="Search orders"
              className="pl-9"
              placeholder="Order number or customer name"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>
          <Select
            aria-label="Order status"
            value={status}
            onChange={(event) => update({ status: event.target.value || null })}
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {ORDER_STATUS_LABELS[value]}
              </option>
            ))}
          </Select>
          <Select
            aria-label="Payment status"
            value={paymentStatus}
            onChange={(event) => update({ payment_status: event.target.value || null })}
          >
            <option value="">Any payment</option>
            {PAYMENT_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {PAYMENT_STATUS_LABELS[value].mobile}
              </option>
            ))}
          </Select>
          <Input
            type="date"
            aria-label="From date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(event) => update({ date_from: event.target.value || null })}
          />
          <Input
            type="date"
            aria-label="To date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(event) => update({ date_to: event.target.value || null })}
          />
        </div>
        {hasFilters ? (
          <div className="flex items-center justify-between border-b border-border px-4 py-2 text-sm">
            <span className="text-muted">
              {query.data ? `${query.data.count} matching orders` : "Filtering…"}
              {dateRangeInvalid ? " · From date is after To date" : ""}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchInput("");
                setParams(new URLSearchParams(), { replace: true });
              }}
            >
              <X size={14} /> Clear filters
            </Button>
          </div>
        ) : null}

        {query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.isLoading ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        ) : orders.length === 0 ? (
          <EmptyState
            title={hasFilters ? "No orders match these filters" : "No orders yet"}
            description={
              hasFilters
                ? "Try changing or clearing the filters."
                : "When customers order from your store, they will show up here."
            }
          />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Order</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Payment</TableHead>
                  <TableHead className="text-right">Items</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead>Placed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order) => (
                  <TableRow
                    key={order.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/orders/${order.id}`)}
                  >
                    <TableCell className="font-medium">
                      <Link
                        to={`/orders/${order.id}`}
                        className="text-primary hover:underline"
                        onClick={(event) => event.stopPropagation()}
                      >
                        {order.order_number}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <p>{order.customer.full_name}</p>
                      <p className="text-xs text-muted">{order.customer.phone}</p>
                    </TableCell>
                    <TableCell>
                      <OrderStatusBadge status={order.order_status} />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col items-start gap-1">
                        <PaymentStatusBadge
                          status={order.payment_status}
                          isCash={order.payment_method === "CASH"}
                        />
                        {order.payment_method ? (
                          <span className="text-xs text-muted">
                            {paymentMethodLabel(order.payment_method)}
                          </span>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">{order.item_count}</TableCell>
                    <TableCell className="text-right font-medium">
                      {formatMoney(order.total_amount)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted">
                      {formatDateTime(order.ordered_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              count={query.data?.count ?? 0}
              onPageChange={(next) => update({ page: next > 1 ? String(next) : null }, false)}
            />
          </>
        )}
      </Card>
    </>
  );
}
