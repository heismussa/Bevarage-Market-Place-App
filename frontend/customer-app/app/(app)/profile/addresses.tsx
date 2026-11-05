import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { View } from "react-native";

import { AddressCard } from "@/components/AddressCard";
import { Button } from "@/components/Button";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorView, LoadingView } from "@/components/StateViews";
import { api, unwrap } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { keys } from "@/lib/query";
import { useToast } from "@/lib/toast";

export default function AddressesScreen() {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: keys.addresses,
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/addresses/", { params: { query: { page_size: 100 } } }))
        .results,
  });

  const remove = useMutation({
    mutationFn: async (id: number) => {
      await api.DELETE("/api/v1/addresses/{id}/", { params: { path: { id } } });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.addresses });
      toast.show("Address removed.", "success");
    },
    onError: (error) => toast.show(errorMessage(error), "error"),
  });

  const makeDefault = useMutation({
    mutationFn: async (id: number) =>
      unwrap(
        await api.POST("/api/v1/addresses/{id}/set-default/", {
          params: { path: { id } },
        }),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.addresses });
    },
    onError: (error) => toast.show(errorMessage(error), "error"),
  });

  const addresses = query.data ?? [];

  return (
    <Screen
      title="Addresses"
      back
      refreshing={query.isRefetching}
      onRefresh={() => void query.refetch()}
      footer={<Button title="Add address" onPress={() => router.push("/profile/address-form")} />}
    >
      {query.isLoading ? <LoadingView /> : null}
      {query.isError ? (
        <ErrorView error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {!query.isLoading && addresses.length === 0 ? (
        <EmptyState
          icon="location-outline"
          title="No addresses yet"
          message="Add one so we know where to deliver."
        />
      ) : null}
      {addresses.map((address) => (
        <AddressCard
          key={address.id}
          address={address}
          onPress={() => router.push(`/profile/address-form?id=${address.id}`)}
          actions={
            <View className="flex-row gap-2">
              {!address.is_default ? (
                <Button
                  title="Set default"
                  variant="secondary"
                  small
                  className="flex-1"
                  loading={makeDefault.isPending}
                  onPress={() => void makeDefault.mutateAsync(address.id)}
                />
              ) : null}
              <Button
                title="Remove"
                variant="ghost"
                small
                className="flex-1"
                loading={remove.isPending}
                onPress={() => void remove.mutateAsync(address.id)}
              />
            </View>
          }
        />
      ))}
    </Screen>
  );
}
