import { formatPhoneDisplay } from "@beverage/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Pressable, Switch, Text, View } from "react-native";

import { Button } from "@/components/Button";
import { FormInput } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { Banner, ErrorView, LoadingView } from "@/components/StateViews";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { applyServerError } from "@/lib/forms";
import { useUserLocation } from "@/lib/location";
import { keys } from "@/lib/query";
import { useToast } from "@/lib/toast";
import { addressSchema, phoneForApi, type AddressForm } from "@/lib/validation";

export default function AddressFormScreen() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const addressId = id ? Number(id) : null;
  const editing = Number.isFinite(addressId) && addressId !== null;
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const location = useUserLocation();
  const [formError, setFormError] = useState<string | null>(null);
  const [setAsDefault, setSetAsDefault] = useState(!editing);

  const existing = useQuery({
    queryKey: keys.address(addressId ?? 0),
    enabled: editing && addressId !== null,
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/addresses/{id}/", { params: { path: { id: addressId! } } })),
  });

  const { control, handleSubmit, setError, setValue, watch, reset, formState } =
    useForm<AddressForm>({
      resolver: zodResolver(addressSchema),
      defaultValues: {
        address_name: "",
        address_line: "",
        city: "",
        area: "",
        phone: user?.phone ? formatPhoneDisplay(user.phone) : "",
        latitude: "",
        longitude: "",
      },
    });

  useEffect(() => {
    if (!existing.data) return;
    reset({
      address_name: existing.data.address_name,
      address_line: existing.data.address_line,
      city: existing.data.city,
      area: existing.data.area ?? "",
      phone: formatPhoneDisplay(existing.data.phone),
      latitude: existing.data.latitude ?? "",
      longitude: existing.data.longitude ?? "",
    });
    setSetAsDefault(existing.data.is_default);
  }, [existing.data, reset]);

  const latitude = watch("latitude");
  const longitude = watch("longitude");

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    const body = {
      address_name: values.address_name.trim(),
      address_line: values.address_line.trim(),
      city: values.city.trim(),
      area: values.area.trim() || null,
      phone: phoneForApi(values.phone),
      latitude: values.latitude.trim() || null,
      longitude: values.longitude.trim() || null,
    };
    try {
      const saved =
        editing && addressId
          ? unwrap(
              await api.PATCH("/api/v1/addresses/{id}/", {
                params: { path: { id: addressId } },
                body,
              }),
            )
          : unwrap(await api.POST("/api/v1/addresses/", { body }));
      if (setAsDefault && !saved.is_default) {
        unwrap(
          await api.POST("/api/v1/addresses/{id}/set-default/", {
            params: { path: { id: saved.id } },
          }),
        );
      }
      void queryClient.invalidateQueries({ queryKey: keys.addresses });
      toast.show(editing ? "Address updated." : "Address saved.", "success");
      router.back();
    } catch (error) {
      setFormError(
        applyServerError(error, setError, [
          "address_name",
          "address_line",
          "city",
          "area",
          "phone",
          "latitude",
          "longitude",
        ]),
      );
    }
  });

  const useCurrent = () => {
    if (!location.coords) {
      toast.show("Turn on location to pin this address.", "error");
      void location.refresh();
      return;
    }
    setValue("latitude", String(location.coords.lat));
    setValue("longitude", String(location.coords.lng));
    toast.show("Pinned to your current location.", "success");
  };

  return (
    <Screen title={editing ? "Edit address" : "New address"} back>
      {editing && existing.isLoading ? <LoadingView /> : null}
      {editing && existing.isError ? (
        <ErrorView error={existing.error} onRetry={() => void existing.refetch()} />
      ) : null}
      {!editing || existing.data ? (
        <View>
          {formError ? <Banner message={formError} /> : null}
          <FormInput
            control={control}
            name="address_name"
            label="Label"
            placeholder="Home, Office…"
            autoCapitalize="words"
          />
          <FormInput
            control={control}
            name="address_line"
            label="Street address"
            placeholder="House number, street, landmark"
            autoCapitalize="sentences"
          />
          <FormInput control={control} name="city" label="City" autoCapitalize="words" />
          <FormInput control={control} name="area" label="Area (optional)" autoCapitalize="words" />
          <FormInput
            control={control}
            name="phone"
            label="Phone at this address"
            keyboardType="phone-pad"
          />
          <Pressable
            onPress={useCurrent}
            className="mb-4 rounded-2xl border border-border bg-surface px-4 py-3"
          >
            <Text className="font-semibold text-primary">Use current location</Text>
            <Text className="mt-1 text-xs text-muted">
              {latitude && longitude
                ? `${latitude}, ${longitude}`
                : "Optional. Helps stores estimate distance."}
            </Text>
          </Pressable>
          <View className="mb-6 flex-row items-center justify-between">
            <Text className="text-base text-foreground">Default address</Text>
            <Switch
              value={setAsDefault}
              onValueChange={setSetAsDefault}
              disabled={existing.data?.is_default === true}
            />
          </View>
          <Button
            title={editing ? "Save address" : "Add address"}
            loading={formState.isSubmitting}
            onPress={() => void onSubmit()}
          />
        </View>
      ) : null}
    </Screen>
  );
}
