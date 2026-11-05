import { formatDateTime, formatMoney, paymentMethodLabel } from "@beverage/api";
import { AlertTriangle, Banknote, Clock, ShoppingBag } from "lucide-react";
import { useMemo } from "react";
import { Link, useNavigate } from "react-router";

import { DailySalesChart, PaymentDonut, TopProductsChart } from "@/components/charts";
import {
  EmptyState,
  ErrorState,
  OrderStatusBadge,
  PageHeader,
  PaymentStatusBadge,
  ChangeBadge,
} from "@/components/common";
import { StatCard } from "@/components/StatCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAnalytics, useDashboard } from "@/lib/queries";
import { useStore } from "@/lib/store";
import { toDateInput } from "@/lib/validation";

export default function DashboardPage() {
  const { store } = useStore();
  const navigate = useNavigate();
  const query = useDashboard(store?.id);
  const weekRange = useMemo(() => {
    const to = new Date();
    const from = new Date();
    from.setDate(from.getDate() - 6);
    return { from: toDateInput(from), to: toDateInput(to) };
  }, []);
  const analytics = useAnalytics(store?.id, weekRange);
  const data = query.data;

  if (query.isError) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <Card>
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        </Card>
      </>
    );
  }

  if (!data) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-80 lg:col-span-2" />
          <Skeleton className="h-80" />
        </div>
      </>
    );
  }

  const week = data.last_7_days_vs_previous;

  return (
    <>
      <PageHeader
        title="Dashboard"
        description={`${store?.store_name ?? ""} · last 7 days`}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Sales (last 7 days)"
          value={formatMoney(week.current.total_sales)}
          icon={<Banknote size={18} />}
          footer={<ChangeBadge percent={week.sales_change_percent} suffix="vs last week" />}
        />
        <StatCard
          label="Orders (last 7 days)"
          value={week.current.total_orders}
          icon={<ShoppingBag size={18} />}
          footer={<ChangeBadge percent={week.orders_change_percent} suffix="vs last week" />}
        />
        <StatCard
          label="Pending orders"
          value={data.pending_orders}
          tone="warning"
          icon={<Clock size={18} />}
          footer={
            <Link to="/orders?status=PENDING" className="text-xs font-medium text-primary hover:underline">
              Review pending orders
            </Link>
          }
        />
        <StatCard
          label="Low stock items"
          value={data.low_stock_count}
          tone={data.low_stock_count > 0 ? "danger" : "default"}
          icon={<AlertTriangle size={18} />}
          footer={
            <Link to="/low-stock" className="text-xs font-medium text-primary hover:underline">
              View low stock
            </Link>
          }
        />
      </div>

      <p className="mt-3 text-xs text-muted">
        All time: {data.total_orders} orders · {formatMoney(data.total_sales)} in completed sales
      </p>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Sales, last 7 days</CardTitle>
          </CardHeader>
          <CardContent>
            <DailySalesChart data={data.sales_last_7_days} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Payment methods</CardTitle>
          </CardHeader>
          <CardContent>
            <PaymentDonut data={data.payment_methods_last_7_days} height={180} />
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Top products, last 7 days</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => navigate("/analytics")}>
            Full analytics
          </Button>
        </CardHeader>
        <CardContent>
          {analytics.isError ? (
            <ErrorState error={analytics.error} onRetry={() => void analytics.refetch()} />
          ) : !analytics.data ? (
            <Skeleton className="h-40" />
          ) : analytics.data.top_products.length === 0 ? (
            <EmptyState
              title="No completed sales yet"
              description="Top products come from completed orders only."
            />
          ) : (
            <TopProductsChart
              data={analytics.data.top_products.map((row) => ({
                name: row.product_name,
                quantity: row.quantity_sold,
              }))}
            />
          )}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Recent orders</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => navigate("/orders")}>
            View all
          </Button>
        </CardHeader>
        <CardContent className="px-0 pb-0">
          {data.recent_orders.length === 0 ? (
            <EmptyState
              title="No orders yet"
              description="Orders from customers will appear here."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Order</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Payment</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead>Placed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.recent_orders.map((order) => (
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
                    <TableCell>{order.customer.full_name}</TableCell>
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
          )}
        </CardContent>
      </Card>
    </>
  );
}
