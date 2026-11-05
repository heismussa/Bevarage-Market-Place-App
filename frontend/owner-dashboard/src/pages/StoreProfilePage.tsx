import { ApiError, applyFieldErrors, formatPhoneDisplay } from "@beverage/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router";
import { z } from "zod";

import { ImagePicker } from "@/components/ImagePicker";
import { EmptyState, ErrorState, PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input, Textarea } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { errorMessage, http } from "@/lib/api";
import { keys } from "@/lib/queries";
import { useStore } from "@/lib/store";
import { useToast } from "@/lib/toast";
import type { OwnerStore } from "@/lib/types";
import { decimalSchema, optionalDecimalCoord, phoneForApi, phoneSchema } from "@/lib/validation";

const schema = z
  .object({
    store_name: z.string().trim().min(2, "Enter a store name."),
    location: z.string().trim().min(4, "Enter a street address."),
    city: z.string().trim(),
    area: z.string().trim(),
    phone: phoneSchema,
    email: z
      .string()
      .trim()
      .refine((value) => value === "" || z.email().safeParse(value).success, {
        message: "Enter a valid email, or leave it blank.",
      }),
    description: z.string().max(2000, "Keep the description under 2000 characters."),
    delivery_fee: decimalSchema("Delivery fee"),
    latitude: optionalDecimalCoord("Latitude"),
    longitude: optionalDecimalCoord("Longitude"),
    acceptOrders: z.boolean(),
  })
  .refine(
    (values) =>
      (values.latitude === "" && values.longitude === "") ||
      (values.latitude !== "" && values.longitude !== ""),
    { message: "Send latitude and longitude together.", path: ["longitude"] },
  );

type Values = z.infer<typeof schema>;

function valuesFromStore(store?: OwnerStore | null): Values {
  return {
    store_name: store?.store_name ?? "",
    location: store?.location ?? "",
    city: store?.city ?? "",
    area: store?.area ?? "",
    phone: store?.phone ? formatPhoneDisplay(store.phone) : "",
    email: store?.email ?? "",
    description: store?.description ?? "",
    delivery_fee: store ? String(Number(store.delivery_fee ?? "0")) : "2000",
    latitude: store?.latitude ?? "",
    longitude: store?.longitude ?? "",
    acceptOrders: store ? store.status === "OPEN" : false,
  };
}

function fieldsFromValues(values: Values): Record<string, string> {
  const fields: Record<string, string> = {
    store_name: values.store_name.trim(),
    location: values.location.trim(),
    city: values.city.trim(),
    area: values.area.trim(),
    phone: phoneForApi(values.phone),
    email: values.email.trim(),
    description: values.description.trim(),
    delivery_fee: values.delivery_fee,
    status: values.acceptOrders ? "OPEN" : "CLOSED",
  };
  if (values.latitude && values.longitude) {
    fields.latitude = values.latitude;
    fields.longitude = values.longitude;
  }
  return fields;
}

export default function StoreProfilePage({ create = false }: { create?: boolean }) {
  const navigate = useNavigate();
  const { store, stores, isLoading, error, refetch, selectStore } = useStore();
  const creating = create || stores.length === 0;
  const target = creating ? null : store;

  if (isLoading && !target) {
    return (
      <>
        <PageHeader title={creating ? "Create your store" : "Store profile"} />
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted">Loading…</CardContent>
        </Card>
      </>
    );
  }

  if (error && !target && !creating) {
    return (
      <>
        <PageHeader title="Store profile" />
        <Card>
          <ErrorState error={error} onRetry={refetch} />
        </Card>
      </>
    );
  }

  if (!creating && !target) {
    return (
      <>
        <PageHeader title="Store profile" />
        <Card>
          <EmptyState
            title="No store yet"
            description="Create your first store to start selling."
            action={
              <Button type="button" onClick={() => navigate("/store/new")}>
                Create store
              </Button>
            }
          />
        </Card>
      </>
    );
  }

  return <StoreForm creating={creating} store={target} onCreated={selectStore} />;
}

function StoreForm({
  creating,
  store,
  onCreated,
}: {
  creating: boolean;
  store: OwnerStore | null | undefined;
  onCreated: (id: number) => void;
}) {
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [logo, setLogo] = useState<File | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: valuesFromStore(store),
  });

  useEffect(() => {
    reset(valuesFromStore(store));
    setLogo(null);
  }, [store, reset]);

  const acceptOrders = watch("acceptOrders");

  const onSubmit = handleSubmit(async (values) => {
    const fields = fieldsFromValues(values);
    let body: unknown = fields;
    if (logo) {
      const form = new FormData();
      for (const [key, value] of Object.entries(fields)) {
        form.append(key, value);
      }
      form.append("logo", logo);
      body = form;
    }

    try {
      if (creating) {
        const created = await http.post<OwnerStore>("/api/v1/owner/stores/", { body });
        await queryClient.invalidateQueries({ queryKey: keys.stores });
        onCreated(created.id);
        toast.success("Store created. You can add products next.");
        navigate("/", { replace: true });
      } else if (store) {
        await http.patch<OwnerStore>("/api/v1/owner/stores/{id}/", {
          path: { id: store.id },
          body,
        });
        await queryClient.invalidateQueries({ queryKey: keys.stores });
        toast.success("Store profile saved.");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        applyFieldErrors(err, (name, fieldError) =>
          setError(name as keyof Values, fieldError),
        );
      }
      toast.error(errorMessage(err));
    }
  });

  return (
    <>
      <PageHeader
        title={creating ? "Create your store" : "Store profile"}
        description={
          creating
            ? "New stores start closed. Turn on “Accept new orders” when you are ready."
            : "Customers see this name, location and open/closed status."
        }
      />
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={onSubmit} className="space-y-5" noValidate>
            <ImagePicker
              currentUrl={store?.logo}
              file={logo}
              onFileChange={setLogo}
              label="Store logo"
              shape="round"
            />

            <Field label="Store name" htmlFor="st-name" error={errors.store_name?.message}>
              <Input id="st-name" {...register("store_name")} />
            </Field>
            <Field label="Address" htmlFor="st-location" error={errors.location?.message}>
              <Input id="st-location" {...register("location")} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="City" htmlFor="st-city" error={errors.city?.message}>
                <Input id="st-city" {...register("city")} />
              </Field>
              <Field label="Area" htmlFor="st-area" error={errors.area?.message}>
                <Input id="st-area" {...register("area")} />
              </Field>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Phone" htmlFor="st-phone" error={errors.phone?.message}>
                <Input id="st-phone" type="tel" {...register("phone")} />
              </Field>
              <Field label="Email" htmlFor="st-email" error={errors.email?.message}>
                <Input id="st-email" type="email" {...register("email")} />
              </Field>
            </div>
            <Field
              label="Description"
              htmlFor="st-description"
              error={errors.description?.message}
            >
              <Textarea id="st-description" rows={3} {...register("description")} />
            </Field>
            <Field
              label="Delivery fee (TSh)"
              htmlFor="st-fee"
              error={errors.delivery_fee?.message}
            >
              <Input id="st-fee" inputMode="decimal" {...register("delivery_fee")} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Latitude"
                htmlFor="st-lat"
                error={errors.latitude?.message}
                hint="Optional. Send both together."
              >
                <Input id="st-lat" {...register("latitude")} />
              </Field>
              <Field label="Longitude" htmlFor="st-lng" error={errors.longitude?.message}>
                <Input id="st-lng" {...register("longitude")} />
              </Field>
            </div>

            <div className="flex items-center justify-between rounded-xl border border-border px-4 py-3">
              <div>
                <p className="text-sm font-medium">Accept new orders</p>
                <p className="text-xs text-muted">
                  Maps to store status OPEN / CLOSED. Customers see “Open now” or “Closed”.
                </p>
              </div>
              <Switch
                checked={acceptOrders}
                onCheckedChange={(checked) => setValue("acceptOrders", checked)}
                label="Accept new orders"
              />
            </div>

            <div className="flex justify-end">
              <Button type="submit" loading={isSubmitting}>
                {creating ? "Create store" : "Save changes"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </>
  );
}
