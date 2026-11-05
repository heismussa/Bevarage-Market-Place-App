import { formatMoney } from "@beverage/api";
import { useMemo, useState } from "react";

import { DailySalesChart, PaymentDonut, TopProductsChart } from "@/components/charts";
import { ChangeBadge, EmptyState, ErrorState, PageHeader } from "@/components/common";
import { StatCard } from "@/components/StatCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalytics } from "@/lib/queries";
import { useStore } from "@/lib/store";
import { toDateInput } from "@/lib/validation";

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function mondayOf(date: Date): Date {
  const next = new Date(date);
  const day = next.getDay();
  const offset = day === 0 ? 6 : day - 1;
  next.setDate(next.getDate() - offset);
  return next;
}

function last30(): { from: string; to: string } {
  const to = new Date();
  return { from: toDateInput(addDays(to, -29)), to: toDateInput(to) };
}

function thisWeek(): { from: string; to: string } {
  const to = new Date();
  return { from: toDateInput(mondayOf(to)), to: toDateInput(to) };
}

export default function AnalyticsPage() {
  const { store } = useStore();
  const defaults = last30();
  const [from, setFrom] = useState(defaults.from);
  const [to, setTo] = useState(defaults.to);
  const range = useMemo(() => ({ from, to }), [from, to]);
  const invalidRange = Boolean(from && to && from > to);
  const query = useAnalytics(invalidRange ? undefined : store?.id, range);
  const data = query.data;

  return (
    <>
      <PageHeader
        title="Sales analytics"
        description="Completed orders in the selected dates. Comparison is against the equally long period before it."
      />

      <Card className="mb-4">
        <CardContent className="flex flex-wrap items-end gap-3 pt-6">
          <Field label="From" htmlFor="an-from" className="w-40">
            <Input
              id="an-from"
              type="date"
              value={from}
              onChange={(event) => setFrom(event.target.value)}
            />
          </Field>
          <Field label="To" htmlFor="an-to" className="w-40">
            <Input
              id="an-to"
              type="date"
              value={to}
              onChange={(event) => setTo(event.target.value)}
            />
          </Field>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              const week = thisWeek();
              setFrom(week.from);
              setTo(week.to);
            }}
          >
            This week
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              const month = last30();
              setFrom(month.from);
              setTo(month.to);
            }}
          >
            Last 30 days
          </Button>
        </CardContent>
      </Card>

      {invalidRange ? (
        <Card>
          <EmptyState
            title="Check the dates"
            description="“From” must be on or before “To”."
          />
        </Card>
      ) : query.isError ? (
        <Card>
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        </Card>
      ) : !data ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Sales"
              value={formatMoney(data.total_sales)}
              footer={
                <ChangeBadge
                  percent={data.compared_to_previous.sales_change_percent}
                  suffix="vs previous period"
                />
              }
            />
            <StatCard
              label="Orders"
              value={data.total_orders}
              footer={
                <ChangeBadge
                  percent={data.compared_to_previous.orders_change_percent}
                  suffix="vs previous period"
                />
              }
            />
            <StatCard label="Completed" value={data.completed_orders} />
            <StatCard label="Pending" value={data.pending_orders} tone="warning" />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Daily sales</CardTitle>
              </CardHeader>
              <CardContent>
                <DailySalesChart data={data.daily_sales} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Payment methods</CardTitle>
              </CardHeader>
              <CardContent>
                <PaymentDonut data={data.payment_methods} height={180} />
              </CardContent>
            </Card>
          </div>

          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Top products</CardTitle>
            </CardHeader>
            <CardContent>
              {data.top_products.length === 0 ? (
                <EmptyState
                  title="No completed sales in this range"
                  description="Top products come from completed orders only."
                />
              ) : (
                <TopProductsChart
                  data={data.top_products.map((row) => ({
                    name: row.product_name,
                    quantity: row.quantity_sold,
                  }))}
                />
              )}
            </CardContent>
          </Card>
        </>
      )}
    </>
  );
}
