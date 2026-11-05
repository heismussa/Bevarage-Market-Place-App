import { formatMoney, paymentMethodLabel } from "@beverage/api";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "@/components/common";
import type { DailySales, PaymentMethodShare } from "@/lib/types";

const PALETTE = [
  "var(--color-primary)",
  "var(--color-secondary)",
  "#7DA0CA",
  "#5483B3",
  "var(--color-warning)",
  "var(--color-success)",
  "var(--color-danger)",
];

const tooltipStyle = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: 12,
  color: "var(--color-foreground)",
  fontSize: 12,
} as const;

function compact(value: number): string {
  return new Intl.NumberFormat("en", { notation: "compact" }).format(value);
}

function shortDay(iso: string): string {
  const date = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" }).format(
    date,
  );
}

/** Daily sales bars. Plot values only; money labels come from the server strings. */
export function DailySalesChart({
  data,
  height = 260,
}: {
  data: DailySales[];
  height?: number;
}) {
  const points = data.map((row) => ({
    date: row.date,
    sales: Number(row.sales),
    salesLabel: formatMoney(row.sales),
    orders: row.orders,
  }));

  return (
    <div style={{ height }} role="img" aria-label="Daily sales chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--color-border)" />
          <XAxis
            dataKey="date"
            tickFormatter={shortDay}
            tick={{ fill: "var(--color-muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            minTickGap={16}
          />
          <YAxis
            tickFormatter={compact}
            tick={{ fill: "var(--color-muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip
            cursor={{ fill: "var(--color-surface-muted)" }}
            contentStyle={tooltipStyle}
            labelFormatter={(label) => shortDay(String(label))}
            formatter={(_value, _name, item) => {
              const payload = item.payload as (typeof points)[number];
              return [`${payload.salesLabel} (${payload.orders} orders)`, "Sales"];
            }}
          />
          <Bar dataKey="sales" fill="var(--color-primary)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Payment methods donut. Slice size = completed orders; percent text is the server's. */
export function PaymentDonut({
  data,
  height = 220,
}: {
  data: PaymentMethodShare[];
  height?: number;
}) {
  const hasSales = data.some((row) => row.orders > 0);
  if (data.length === 0 || !hasSales) {
    return (
      <EmptyState
        title="No completed orders yet"
        description="Payment methods appear once orders are completed."
      />
    );
  }

  const slices = data.map((row) => ({
    name: paymentMethodLabel(row.payment_method),
    value: row.orders,
    percent: row.orders_percent,
    sales: row.sales,
  }));

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div style={{ height, width: height }} role="img" aria-label="Payment methods donut chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="name"
              innerRadius="62%"
              outerRadius="92%"
              paddingAngle={2}
              stroke="none"
            >
              {slices.map((slice, index) => (
                <Cell key={slice.name} fill={PALETTE[index % PALETTE.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(_value, name, item) => {
                const payload = item.payload as (typeof slices)[number];
                return [`${payload.percent}% · ${formatMoney(payload.sales)}`, String(name)];
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="w-full flex-1 space-y-2 text-sm">
        {slices.map((slice, index) => (
          <li key={slice.name} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2">
              <span
                className="h-3 w-3 rounded-full"
                style={{ background: PALETTE[index % PALETTE.length] }}
              />
              {slice.name}
            </span>
            <span className="text-muted">
              {Number(slice.percent).toFixed(1).replace(/\.0$/, "")}% · {slice.value}{" "}
              {slice.value === 1 ? "order" : "orders"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Horizontal bars for top products by quantity sold. */
export function TopProductsChart({
  data,
}: {
  data: { name: string; quantity: number }[];
}) {
  const height = Math.max(180, data.length * 36 + 24);
  return (
    <div style={{ height }} role="img" aria-label="Top products chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
        >
          <CartesianGrid horizontal={false} stroke="var(--color-border)" />
          <XAxis
            type="number"
            tick={{ fill: "var(--color-muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={120}
            tick={{ fill: "var(--color-foreground)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "var(--color-surface-muted)" }}
            contentStyle={tooltipStyle}
            formatter={(value) => [String(value), "Units sold"]}
          />
          <Bar dataKey="quantity" fill="var(--color-secondary)" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
