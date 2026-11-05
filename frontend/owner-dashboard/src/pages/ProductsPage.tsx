import { Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";

import { EmptyState, ErrorState, PageHeader, Pagination } from "@/components/common";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ProductFormDialog } from "@/components/ProductFormDialog";
import { ProductsTable } from "@/components/ProductsTable";
import { StockDialog } from "@/components/StockDialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { errorMessage } from "@/lib/api";
import { useCategories, useDeleteProduct, useProducts } from "@/lib/queries";
import { useStore } from "@/lib/store";
import { useToast } from "@/lib/toast";
import type { AvailabilityValue, OwnerProduct } from "@/lib/types";

const PAGE_SIZE = 20;

export default function ProductsPage() {
  const { store } = useStore();
  const toast = useToast();
  const categories = useCategories();
  const deleteProduct = useDeleteProduct();

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<number | "">("");
  const [availability, setAvailability] = useState<AvailabilityValue | "">("");
  const [page, setPage] = useState(1);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<OwnerProduct | null>(null);
  const [stockFor, setStockFor] = useState<OwnerProduct | null>(null);
  const [deleting, setDeleting] = useState<OwnerProduct | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const query = useProducts(store?.id, {
    search,
    category,
    availability,
    page,
    page_size: PAGE_SIZE,
  });
  const products = query.data?.results ?? [];
  const hasFilters = Boolean(search || category !== "" || availability);

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteProduct.mutateAsync(deleting.id);
      toast.success(`${deleting.name} deleted.`);
      setDeleting(null);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  return (
    <>
      <PageHeader
        title="Products"
        description="Manage what customers can buy from your store."
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus size={16} /> Add product
          </Button>
        }
      />

      <Card>
        <div className="space-y-3 border-b border-border p-4">
          <Tabs
            value={availability}
            onValueChange={(value) => {
              setAvailability(value as AvailabilityValue | "");
              setPage(1);
            }}
          >
            <TabsList>
              <TabsTrigger value="">All</TabsTrigger>
              <TabsTrigger value="AVAILABLE">Available</TabsTrigger>
              <TabsTrigger value="OUT_OF_STOCK">Out of stock</TabsTrigger>
              <TabsTrigger value="UNAVAILABLE">Unavailable</TabsTrigger>
            </TabsList>
          </Tabs>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="relative sm:col-span-2">
              <Search size={16} className="absolute top-3 left-3 text-muted" />
              <Input
                aria-label="Search products"
                className="pl-9"
                placeholder="Search by name"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </div>
            <Select
              aria-label="Category"
              value={String(category)}
              onChange={(event) => {
                setCategory(event.target.value ? Number(event.target.value) : "");
                setPage(1);
              }}
            >
              <option value="">All categories</option>
              {(categories.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </Select>
          </div>
        </div>

        {query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.isLoading ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : products.length === 0 ? (
          <EmptyState
            title={hasFilters ? "No products match" : "No products yet"}
            description={
              hasFilters
                ? "Try a different search or filter."
                : "Add your first product so customers can start ordering."
            }
            action={
              hasFilters ? undefined : (
                <Button
                  onClick={() => {
                    setEditing(null);
                    setFormOpen(true);
                  }}
                >
                  <Plus size={16} /> Add product
                </Button>
              )
            }
          />
        ) : (
          <>
            <ProductsTable
              products={products}
              onEdit={(product) => {
                setEditing(product);
                setFormOpen(true);
              }}
              onStock={setStockFor}
              onDelete={setDeleting}
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

      {store ? (
        <ProductFormDialog
          open={formOpen}
          storeId={store.id}
          product={editing}
          onClose={() => setFormOpen(false)}
        />
      ) : null}
      <StockDialog product={stockFor} onClose={() => setStockFor(null)} />
      <ConfirmDialog
        open={deleting !== null}
        title="Delete this product?"
        description={`${deleting?.name ?? "This product"} will disappear from your store and from customer lists. Past orders keep it.`}
        confirmLabel="Delete"
        destructive
        loading={deleteProduct.isPending}
        onConfirm={() => void confirmDelete()}
        onClose={() => setDeleting(null)}
      />
    </>
  );
}
