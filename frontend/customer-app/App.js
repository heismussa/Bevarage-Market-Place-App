import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { colors, spacing, radius } from '@beverage/ui-tokens';
import {
  getHealth,
  getStores,
  getCategories,
} from './src/mobileApi';

function getList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

export default function App() {
  const [health, setHealth] = useState('Checking connection...');
  const [categories, setCategories] = useState([]);
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  async function loadMarketplace(isRefresh = false) {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError('');

    try {
      const healthData = await getHealth();
      setHealth(healthData.status || 'Connected');

      const results = await Promise.allSettled([
        getCategories(),
        getStores(),
      ]);

      if (results[0].status === 'fulfilled') {
        setCategories(getList(results[0].value));
      }

      if (results[1].status === 'fulfilled') {
        setStores(getList(results[1].value));
      }

      const failed = results
        .map((result, index) =>
          result.status === 'rejected'
            ? ['categories', 'stores'][index]
            : null
        )
        .filter(Boolean);

      if (failed.length) {
        setError(`Unable to load ${failed.join(' and ')}.`);
      }
    } catch (err) {
      setHealth('Connection failed');
      setError(
        err?.message ||
          'Could not connect to the marketplace API.'
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadMarketplace();
  }, []);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar
        barStyle="light-content"
        backgroundColor={colors.primary}
      />

      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => loadMarketplace(true)}
            tintColor={colors.primary}
          />
        }
      >
        <View style={styles.hero}>
          <Text style={styles.eyebrow}>BEVERAGE DELIVERY</Text>
          <Text style={styles.title}>
            Find your favourite drinks
          </Text>
          <Text style={styles.subtitle}>
            Discover beverage stores and explore what's available.
          </Text>

          <View style={styles.statusPill}>
            <View
              style={[
                styles.statusDot,
                health === 'ok' || health === 'Connected'
                  ? styles.connectedDot
                  : null,
              ]}
            />
            <Text style={styles.statusText}>
              API: {health}
            </Text>
          </View>
        </View>

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
            <Text style={styles.errorHint}>
              Pull down to try again.
            </Text>
          </View>
        ) : null}

        {loading ? (
          <View style={styles.loading}>
            <ActivityIndicator
              size="large"
              color={colors.primary}
            />
            <Text style={styles.loadingText}>
              Loading marketplace...
            </Text>
          </View>
        ) : (
          <>
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Categories</Text>

              {categories.length ? (
                <FlatList
                  horizontal
                  data={categories}
                  keyExtractor={(item, index) =>
                    String(item.id ?? index)
                  }
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.horizontalList}
                  renderItem={({ item }) => (
                    <View style={styles.categoryCard}>
                      <Text style={styles.categoryName}>
                        {item.name || item.title || 'Beverages'}
                      </Text>
                    </View>
                  )}
                />
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyTitle}>
                    No categories yet
                  </Text>
                  <Text style={styles.emptyText}>
                    Categories will appear here when available.
                  </Text>
                </View>
              )}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionTitle}>
                Available stores
              </Text>

              {stores.length ? (
                stores.map((store, index) => (
                  <View
                    style={styles.storeCard}
                    key={String(store.id ?? index)}
                  >
                    <View style={styles.storeIcon}>
                      <Text style={styles.storeIconText}>B</Text>
                    </View>
                    <View style={styles.storeDetails}>
                      <Text style={styles.storeName}>
                        {store.name ||
                          store.store_name ||
                          'Beverage store'}
                      </Text>
                      <Text style={styles.storeDescription}>
                        {store.description ||
                          store.address ||
                          'Store details unavailable'}
                      </Text>
                    </View>
                  </View>
                ))
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyTitle}>
                    No stores available yet
                  </Text>
                  <Text style={styles.emptyText}>
                    Stores will appear here when they are registered
                    and available in the marketplace.
                  </Text>
                </View>
              )}
            </View>
          </>
        )}

        <Text style={styles.footer}>
          Beverage Marketplace
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  container: {
    paddingBottom: spacing.large,
  },
  hero: {
    backgroundColor: colors.primary,
    padding: spacing.large,
    paddingTop: spacing.extraLarge,
    paddingBottom: spacing.extraLarge,
    borderBottomLeftRadius: radius.medium,
    borderBottomRightRadius: radius.medium,
  },
  eyebrow: {
    color: '#D5F5E6',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 2,
    marginBottom: spacing.small,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 32,
    fontWeight: '800',
    lineHeight: 39,
    marginBottom: spacing.small,
  },
  subtitle: {
    color: '#E7F5EE',
    fontSize: 15,
    lineHeight: 23,
  },
  statusPill: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginTop: spacing.large,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#D97706',
    marginRight: 8,
  },
  connectedDot: {
    backgroundColor: colors.success,
  },
  statusText: {
    color: colors.text,
    fontSize: 12,
    fontWeight: '600',
  },
  section: {
    marginTop: spacing.large,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 21,
    fontWeight: '800',
    marginHorizontal: spacing.large,
    marginBottom: spacing.medium,
  },
  horizontalList: {
    paddingHorizontal: spacing.large,
    paddingBottom: 4,
  },
  categoryCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.medium,
    padding: spacing.medium,
    minWidth: 130,
    marginRight: spacing.small,
    borderWidth: 1,
    borderColor: '#E5EAF0',
  },
  categoryName: {
    color: colors.text,
    fontWeight: '700',
    fontSize: 14,
  },
  storeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    marginHorizontal: spacing.large,
    marginBottom: spacing.medium,
    padding: spacing.medium,
    borderRadius: radius.medium,
    borderWidth: 1,
    borderColor: '#E5EAF0',
  },
  storeIcon: {
    width: 48,
    height: 48,
    borderRadius: radius.small,
    backgroundColor: '#E5F6ED',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.medium,
  },
  storeIconText: {
    color: colors.primary,
    fontWeight: '800',
    fontSize: 23,
  },
  storeDetails: {
    flex: 1,
  },
  storeName: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 4,
  },
  storeDescription: {
    color: '#657186',
    fontSize: 13,
    lineHeight: 19,
  },
  emptyCard: {
    marginHorizontal: spacing.large,
    padding: spacing.large,
    backgroundColor: colors.surface,
    borderRadius: radius.medium,
    borderWidth: 1,
    borderColor: '#E5EAF0',
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '700',
    marginBottom: spacing.small,
  },
  emptyText: {
    color: '#657186',
    fontSize: 13,
    lineHeight: 20,
  },
  loading: {
    alignItems: 'center',
    padding: spacing.extraLarge,
  },
  loadingText: {
    color: '#657186',
    marginTop: spacing.medium,
  },
  errorBox: {
    margin: spacing.large,
    marginBottom: 0,
    padding: spacing.medium,
    borderRadius: radius.small,
    backgroundColor: '#FEECEB',
  },
  errorText: {
    color: colors.danger,
    fontWeight: '700',
  },
  errorHint: {
    color: colors.danger,
    marginTop: 4,
    fontSize: 13,
  },
  footer: {
    color: '#657186',
    fontSize: 12,
    textAlign: 'center',
    marginTop: spacing.extraLarge,
  },
});
