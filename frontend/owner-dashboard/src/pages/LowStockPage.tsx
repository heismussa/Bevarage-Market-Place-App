import { CheckCircle2 } from "lucide-react";
import { useState } from "react";

import { EmptyState, ErrorState, PageHeader, Pagination } from "@/components/common";
import { ProductsTable } from "@/components/ProductsTable";
import { StockDialog } from "@/components/StockDialog";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useProducts } from "@/lib/queries";
import { useStore } from "@/lib/store";
import type { OwnerProduct } from "@/lib/types";

const PAGE_SIZE = 20;

export default function LowStockPage() {
  const { store } = useStore();
  const [page, setPage] = useState(1);
  const [restocking, setRestocking] = useState<OwnerProduct | null>(null);

  const query = useProducts(store?.id, {
    low_stock: true,
    page,
    page_size: PAGE_SIZE,
  });
  const products = query.data?.results ?? [];

  return (
    <>
      <PageHeader
        title="Low stock"
        description="Products at or below their low-stock alert level."
      />
      <Card>
        {query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.isLoading ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : products.length === 0 ? (
          <EmptyState
            icon={<CheckCircle2 size={24} />}
            title="Everything is well stocked"
            description="Products that run low will be listed here so you can restock them."
          />
        ) : (
          <>
            <ProductsTable
              products={products}
              onStock={setRestocking}
              stockActionLabel="Restock"
            />
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              count={query.data?.count ?? 0}
              onPageChange={setPage}
            />
          </>
        )}
      </Card>
      <StockDialog product={restocking} mode="restock" onClose={() => setRestocking(null)} />
    </>
  );
}
