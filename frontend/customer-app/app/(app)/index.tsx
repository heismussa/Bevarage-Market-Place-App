import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useMemo, useState } from "react";
import { FlatList, Pressable, Text, TextInput, View } from "react-native";

import { ChipRow } from "@/components/Chip";
import { NotificationBell } from "@/components/NotificationBell";
import { ProductCard } from "@/components/ProductCard";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorView, LoadingView } from "@/components/StateViews";
import { StoreCard } from "@/components/StoreCard";
import { api, unwrap } from "@/lib/api";
import { useAddToCart } from "@/lib/cart";
import { categoryOptions, useCategories } from "@/lib/catalog";
import { useDebouncedValue } from "@/lib/hooks";
import { useUserLocation } from "@/lib/location";
import { flattenPages, keys, nextPageParam } from "@/lib/query";
import type { PopularProduct, PublicStore } from "@/lib/types";

export default function HomeScreen() {
  const router = useRouter();
  const location = useUserLocation();
  const { addToCart, isAdding, conflictDialog } = useAddToCart();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<number | null>(null);
  const debouncedSearch = useDebouncedValue(search);
  const categories = useCategories();

  const storeParams = {
    search: debouncedSearch,
    category,
    lat: location.coords?.lat,
    lng: location.coords?.lng,
  };

  const storesQuery = useInfiniteQuery({
    queryKey: keys.stores(storeParams),
    initialPageParam: 1,
    queryFn: async ({ pageParam }) =>
      unwrap(
        await api.GET("/api/v1/stores/", {
          params: {
            query: {
              page: pageParam,
              page_size: 20,
              search: debouncedSearch || undefined,
              category: category ?? undefined,
              lat: location.coords?.lat,
              lng: location.coords?.lng,
              ordering: location.coords ? "distance" : undefined,
            },
          },
        }),
      ),
    getNextPageParam: nextPageParam,
  });

  const popularQuery = useQuery({
    queryKey: keys.popular(category),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/products/popular/", {
          params: { query: { page_size: 10, category: category ?? undefined } },
        }),
      ).results,
  });

  const stores = flattenPages<PublicStore>(storesQuery.data);
  const popular = popularQuery.data ?? [];
  const chips = useMemo(
    () => categoryOptions(categories.data),
    [categories.data],
  );

  const locationLabel = location.coords
    ? "Near you"
    : location.status === "denied"
      ? "Location off"
      : "Finding you…";

  return (
    <Screen
      title="Home"
      right={<NotificationBell />}
      scroll={false}
      padded={false}
      refreshing={storesQuery.isRefetching}
      onRefresh={() => {
        void location.refresh();
        void storesQuery.refetch();
        void popularQuery.refetch();
      }}
    >
      {conflictDialog}
      <FlatList
        data={stores}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 32 }}
        onEndReached={() => {
          if (storesQuery.hasNextPage && !storesQuery.isFetchingNextPage) {
            void storesQuery.fetchNextPage();
          }
        }}
        ListHeaderComponent={
          <View className="pb-3">
            <Pressable
              onPress={() => void location.refresh()}
              className="mb-3 self-start rounded-full bg-surface px-3 py-1.5"
            >
              <Text className="text-xs font-medium text-muted">{locationLabel}</Text>
            </Pressable>

            <TextInput
              value={search}
              onChangeText={setSearch}
              placeholder="Search stores"
              placeholderTextColor="#7DA0CA"
              className="mb-3 rounded-xl border border-border bg-surface px-4 py-3 text-base text-foreground"
            />

            <ChipRow options={chips} value={category} onChange={setCategory} />

            {popular.length > 0 ? (
              <View className="mt-5">
                <Text className="mb-3 text-lg font-semibold text-foreground">
                  Popular products
                </Text>
                <FlatList
                  horizontal
                  data={popular}
                  keyExtractor={(item) => String(item.id)}
                  showsHorizontalScrollIndicator={false}
                  renderItem={({ item }: { item: PopularProduct }) => (
                    <View className="mr-3">
                      <ProductCard
                        product={item}
                        width={168}
                        showStore
                        adding={isAdding}
                        onPress={() => router.push(`/product/${item.id}`)}
                        onAdd={() => void addToCart(item.id)}
                      />
                    </View>
                  )}
                />
              </View>
            ) : null}

            <Text className="mb-3 mt-6 text-lg font-semibold text-foreground">
              Stores
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <StoreCard store={item} onPress={() => router.push(`/store/${item.id}`)} />
        )}
        ListEmptyComponent={
          storesQuery.isLoading ? (
            <LoadingView label="Finding stores…" />
          ) : storesQuery.isError ? (
            <ErrorView error={storesQuery.error} onRetry={() => void storesQuery.refetch()} />
          ) : (
            <EmptyState
              icon="storefront-outline"
              title="No stores nearby"
              message="Try another search or turn on location."
            />
          )
        }
      />
    </Screen>
  );
}
