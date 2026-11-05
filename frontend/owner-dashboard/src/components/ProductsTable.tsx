import { formatMoney } from "@beverage/api";
import { ImageOff, Pencil, PackagePlus, Trash2 } from "lucide-react";

import { AvailabilityBadge } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { OwnerProduct } from "@/lib/types";

export function ProductThumb({ product }: { product: OwnerProduct }) {
  return (
    <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-surface-muted text-muted">
      {product.image ? (
        <img src={product.image} alt="" className="h-full w-full object-cover" />
      ) : (
        <ImageOff size={16} />
      )}
    </div>
  );
}

export function ProductsTable({
  products,
  onEdit,
  onStock,
  onDelete,
  stockLabel = "Stock",
  stockActionLabel = "Stock",
}: {
  products: OwnerProduct[];
  onEdit?: (product: OwnerProduct) => void;
  onStock: (product: OwnerProduct) => void;
  onDelete?: (product: OwnerProduct) => void;
  stockLabel?: string;
  stockActionLabel?: string;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Product</TableHead>
          <TableHead>Category</TableHead>
          <TableHead className="text-right">Price</TableHead>
          <TableHead className="text-right">{stockLabel}</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {products.map((product) => (
          <TableRow key={product.id}>
            <TableCell>
              <div className="flex items-center gap-3">
                <ProductThumb product={product} />
                <div className="min-w-0">
                  <p className="truncate font-medium">{product.name}</p>
                  <p className="text-xs text-muted capitalize">{product.unit.toLowerCase()}</p>
                </div>
              </div>
            </TableCell>
            <TableCell className="text-muted">{product.category_detail.name}</TableCell>
            <TableCell className="text-right">{formatMoney(product.price)}</TableCell>
            <TableCell className="text-right">
              <span className="font-medium">{product.stock_quantity ?? 0}</span>
              <span className="text-xs text-muted"> / alert {product.low_stock_threshold ?? 0}</span>
            </TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-1">
                <AvailabilityBadge status={product.availability_status ?? "AVAILABLE"} />
                {product.is_low_stock ? <Badge variant="warning">Low stock</Badge> : null}
              </div>
            </TableCell>
            <TableCell>
              <div className="flex justify-end gap-1">
                <Button
                  variant={stockActionLabel === "Restock" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => onStock(product)}
                  aria-label={`${stockActionLabel} ${product.name}`}
                >
                  <PackagePlus size={14} /> {stockActionLabel}
                </Button>
                {onEdit ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEdit(product)}
                    aria-label={`Edit ${product.name}`}
                  >
                    <Pencil size={14} /> Edit
                  </Button>
                ) : null}
                {onDelete ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-danger"
                    onClick={() => onDelete(product)}
                    aria-label={`Delete ${product.name}`}
                  >
                    <Trash2 size={14} />
                  </Button>
                ) : null}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
