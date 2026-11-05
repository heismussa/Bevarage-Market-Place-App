import { ApiError, applyFieldErrors } from "@beverage/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ImagePicker } from "@/components/ImagePicker";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { errorMessage, http } from "@/lib/api";
import { useCategories, useInvalidateCatalog } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import { UNITS, type OwnerProduct } from "@/lib/types";
import { decimalSchema } from "@/lib/validation";

const schema = z.object({
  name: z.string().trim().min(2, "Enter a product name."),
  category: z.string().min(1, "Choose a category."),
  unit: z.enum(["BOTTLE", "CAN", "CRATE", "CARTON", "PACK"]),
  price: decimalSchema("Price"),
  stock_quantity: z.string().trim().regex(/^\d+$/, "Enter a whole number, 0 or more."),
  low_stock_threshold: z.string().trim().regex(/^\d+$/, "Enter a whole number, 0 or more."),
  availability_status: z.enum(["AVAILABLE", "UNAVAILABLE"]),
  description: z.string().max(1000, "Keep the description under 1000 characters."),
});
type Values = z.infer<typeof schema>;

function defaults(product?: OwnerProduct | null): Values {
  return {
    name: product?.name ?? "",
    category: product ? String(product.category) : "",
    unit: product?.unit ?? "BOTTLE",
    price: product ? String(Number(product.price)) : "",
    stock_quantity: String(product?.stock_quantity ?? 0),
    low_stock_threshold: String(product?.low_stock_threshold ?? 5),
    // OUT_OF_STOCK is derived by the server from stock, so it shows as Available here.
    availability_status:
      product?.availability_status === "UNAVAILABLE" ? "UNAVAILABLE" : "AVAILABLE",
    description: product?.description ?? "",
  };
}

export function ProductFormDialog({
  open,
  storeId,
  product,
  onClose,
}: {
  open: boolean;
  storeId: number;
  product?: OwnerProduct | null;
  onClose: () => void;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const invalidate = useInvalidateCatalog();
  const categories = useCategories();
  const [image, setImage] = useState<File | null>(null);
  const editing = Boolean(product);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: defaults(product),
  });

  useEffect(() => {
    if (open) {
      reset(defaults(product));
      setImage(null);
    }
  }, [open, product, reset]);

  const onSubmit = handleSubmit(async (values) => {
    const fields: Record<string, string | number | null> = {
      name: values.name.trim(),
      category: Number(values.category),
      unit: values.unit,
      price: values.price,
      stock_quantity: Number(values.stock_quantity),
      low_stock_threshold: Number(values.low_stock_threshold),
      availability_status: values.availability_status,
      description: values.description.trim() || null,
    };

    let body: unknown = fields;
    if (image) {
      const form = new FormData();
      for (const [key, value] of Object.entries(fields)) {
        if (value !== null) form.append(key, String(value));
      }
      form.append("image", image);
      body = form;
    }

    try {
      if (product) {
        await http.patch<OwnerProduct>("/api/v1/owner/products/{id}/", {
          path: { id: product.id },
          body,
        });
      } else {
        await http.post<OwnerProduct>("/api/v1/owner/stores/{store_id}/products/", {
          path: { store_id: storeId },
          body,
        });
      }
      invalidate();
      void queryClient.invalidateQueries({ queryKey: ["owner", "products"] });
      toast.success(editing ? "Product updated." : "Product added.");
      onClose();
    } catch (error) {
      if (error instanceof ApiError) {
        applyFieldErrors(error, (name, err) => setError(name as keyof Values, err));
      }
      toast.error(errorMessage(error));
    }
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={editing ? "Edit product" : "Add product"}
      className="max-w-xl"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" form="product-form" loading={isSubmitting}>
            {editing ? "Save changes" : "Add product"}
          </Button>
        </>
      }
    >
      <form id="product-form" onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="Name" htmlFor="pf-name" error={errors.name?.message}>
          <Input id="pf-name" {...register("name")} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Category" htmlFor="pf-category" error={errors.category?.message}>
            <Select id="pf-category" {...register("category")}>
              <option value="">
                {categories.isLoading ? "Loading…" : "Choose a category"}
              </option>
              {(categories.data ?? []).map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Unit" htmlFor="pf-unit" error={errors.unit?.message}>
            <Select id="pf-unit" {...register("unit")}>
              {UNITS.map((unit) => (
                <option key={unit.value} value={unit.value}>
                  {unit.label}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Price (TSh)" htmlFor="pf-price" error={errors.price?.message}>
            <Input id="pf-price" inputMode="decimal" {...register("price")} />
          </Field>
          <Field label="Stock" htmlFor="pf-stock" error={errors.stock_quantity?.message}>
            <Input id="pf-stock" inputMode="numeric" {...register("stock_quantity")} />
          </Field>
          <Field
            label="Low-stock alert at"
            htmlFor="pf-threshold"
            error={errors.low_stock_threshold?.message}
          >
            <Input id="pf-threshold" inputMode="numeric" {...register("low_stock_threshold")} />
          </Field>
        </div>
        <Field
          label="Availability"
          htmlFor="pf-availability"
          error={errors.availability_status?.message}
          hint="Out of stock is set automatically when stock reaches 0."
        >
          <Select id="pf-availability" {...register("availability_status")}>
            <option value="AVAILABLE">Available</option>
            <option value="UNAVAILABLE">Unavailable (hidden from customers)</option>
          </Select>
        </Field>
        <Field label="Description" htmlFor="pf-description" error={errors.description?.message}>
          <Textarea id="pf-description" {...register("description")} />
        </Field>
        <ImagePicker
          label="Product image"
          currentUrl={product?.image}
          file={image}
          onFileChange={setImage}
        />
      </form>
    </Dialog>
  );
}
