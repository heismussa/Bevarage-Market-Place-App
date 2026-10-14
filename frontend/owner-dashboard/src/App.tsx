import { useCallback, useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router'
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  Store,
  Settings,
  Menu,
  LogOut,
  CircleDollarSign,
  Clock3,
  X,
} from 'lucide-react'
import {
  clearTokens,
  getAccessToken,
  getMe,
  getOwnerStores,
  getOwnerDashboard,
  getOwnerProducts,
} from '@beverage/api'
import Login from './Login'

type UserProfile = {
  id: number
  full_name: string
  phone: string
  email?: string | null
  role: string
}

type StoreInfo = {
  id: number
  store_name: string
  city?: string
  area?: string
  status?: string
}

type OrderInfo = {
  id?: number | string
  order_number?: string
  customer?: { full_name?: string } | string
  total_amount?: string | number
  order_status?: string
  status?: string
}

type DashboardData = {
  total_orders?: number
  pending_orders?: number
  total_sales?: string | number
  low_stock_count?: number
  recent_orders?: OrderInfo[]
}

const navigation = [
  { label: 'Overview', path: '/', icon: LayoutDashboard },
  { label: 'Products', path: '/products', icon: Package },
  { label: 'Orders', path: '/orders', icon: ShoppingCart },
  { label: 'My Store', path: '/store', icon: Store },
  { label: 'Settings', path: '/settings', icon: Settings },
]

function extractList<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) return payload as T[]

  if (
    payload &&
    typeof payload === 'object' &&
    'results' in payload &&
    Array.isArray(payload.results)
  ) {
    return payload.results as T[]
  }

  return []
}

function money(value: string | number | undefined) {
  const amount = Number(value ?? 0)
  return `TZS ${Number.isFinite(amount) ? amount.toLocaleString('en-TZ') : '0'}`
}

function readableStatus(status?: string) {
  if (!status) return 'Unknown'
  return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()
}

function Overview({
  user,
  store,
  dashboard,
  productCount,
}: {
  user: UserProfile
  store: StoreInfo
  dashboard: DashboardData
  productCount: number
}) {
  const stats = [
    {
      label: 'Total sales',
      value: money(dashboard.total_sales),
      note: 'Completed orders',
      icon: CircleDollarSign,
    },
    {
      label: 'Total orders',
      value: String(dashboard.total_orders ?? 0),
      note: 'Orders for your store',
      icon: ShoppingCart,
    },
    {
      label: 'Products',
      value: String(productCount),
      note: 'Products in your store',
      icon: Package,
    },
    {
      label: 'Pending orders',
      value: String(dashboard.pending_orders ?? 0),
      note: 'Orders needing attention',
      icon: Clock3,
    },
  ]

  const orders = dashboard.recent_orders ?? []

  return (
    <div className="space-y-7">
      <div>
        <p className="text-sm text-gray-500">
          {store.store_name}
          {store.city ? ` · ${store.city}` : ''}
        </p>
        <h2 className="mt-1 text-2xl font-bold tracking-tight text-gray-900">
          Welcome back, {user.full_name || 'Store Owner'} 👋
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Here is the latest information returned by your store dashboard.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-500">{stat.label}</p>
                <span className="rounded-xl bg-emerald-50 p-2 text-emerald-700">
                  <Icon size={20} />
                </span>
              </div>
              <p className="mt-4 text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="mt-2 text-xs text-gray-500">{stat.note}</p>
            </div>
          )
        })}
      </div>

      <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-gray-900">Recent orders</h3>
        <p className="mt-1 text-sm text-gray-500">
          Orders returned by your Django API
        </p>

        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[550px] text-left text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs uppercase tracking-wide text-gray-400">
                <th className="pb-3 font-medium">Order</th>
                <th className="pb-3 font-medium">Customer</th>
                <th className="pb-3 font-medium">Amount</th>
                <th className="pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order, index) => {
                const customer =
                  typeof order.customer === 'string'
                    ? order.customer
                    : order.customer?.full_name || 'Customer'

                const status = readableStatus(order.order_status ?? order.status)

                return (
                  <tr key={order.id ?? order.order_number ?? index} className="border-b border-gray-50 last:border-0">
                    <td className="py-4 font-semibold text-gray-800">
                      {order.order_number ?? order.id ?? '—'}
                    </td>
                    <td className="py-4 text-gray-600">{customer}</td>
                    <td className="py-4 font-medium text-gray-800">
                      {money(order.total_amount)}
                    </td>
                    <td className="py-4">
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                        {status}
                      </span>
                    </td>
                  </tr>
                )
              })}
              {orders.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-gray-500">
                    No orders have been returned for this store yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <section>
      <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
      <div className="mt-6 rounded-2xl border border-gray-100 bg-white p-8 text-center shadow-sm">
        <Package className="mx-auto text-emerald-700" size={36} />
        <h3 className="mt-4 font-semibold text-gray-900">{title} management</h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-gray-500">
          We will connect this section to the Django API in a later step.
        </p>
      </div>
    </section>
  )
}

function DashboardLayout({
  user,
  store,
  dashboard,
  productCount,
  onLogout,
}: {
  user: UserProfile
  store: StoreInfo
  dashboard: DashboardData
  productCount: number
  onLogout: () => void
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[#f7f9f7]">
      {sidebarOpen && (
        <button
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
        />
      )}

      <aside className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-gray-100 bg-white transition-transform lg:translate-x-0 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex h-20 items-center justify-between border-b border-gray-100 px-6">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-emerald-700 p-2 text-white">
              <Store size={22} />
            </div>
            <div>
              <h1 className="font-bold text-gray-900">BeverageHub</h1>
              <p className="text-xs text-gray-500">Owner dashboard</p>
            </div>
          </div>
          <button onClick={() => setSidebarOpen(false)} aria-label="Close navigation" className="text-gray-500 lg:hidden">
            <X size={21} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-6">
          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
            Workspace
          </p>
          {navigation.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                    isActive
                      ? 'bg-emerald-50 text-emerald-800'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`
                }
              >
                <Icon size={19} />
                {item.label}
              </NavLink>
            )
          })}
        </nav>

        <div className="m-4 rounded-2xl bg-emerald-800 p-4 text-white">
          <p className="text-sm font-semibold">{store.store_name}</p>
          <p className="mt-2 text-xs leading-5 text-emerald-100">
            Manage your products and customer orders.
          </p>
        </div>
      </aside>

      <div className="min-h-screen lg:pl-64">
        <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-gray-100 bg-white/95 px-4 backdrop-blur sm:px-8">
          <div className="flex items-center gap-3">
            <button
              aria-label="Open navigation"
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 lg:hidden"
            >
              <Menu size={22} />
            </button>
            <div>
              <p className="text-sm font-semibold text-gray-800">{user.full_name}</p>
              <p className="text-xs text-gray-500">{store.store_name}</p>
            </div>
          </div>

          <button
            onClick={onLogout}
            className="flex items-center gap-2 rounded-xl border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
          >
            <LogOut size={17} />
            <span>Log out</span>
          </button>
        </header>

        <main className="p-4 sm:p-8">
          <Routes>
            <Route
              path="/"
              element={
                <Overview
                  user={user}
                  store={store}
                  dashboard={dashboard}
                  productCount={productCount}
                />
              }
            />
            <Route path="/products" element={<PlaceholderPage title="Products" />} />
            <Route path="/orders" element={<PlaceholderPage title="Orders" />} />
            <Route path="/store" element={<PlaceholderPage title="My Store" />} />
            <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
            <Route path="*" element={<PlaceholderPage title="Page not found" />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [store, setStore] = useState<StoreInfo | null>(null)
  const [dashboard, setDashboard] = useState<DashboardData>({})
  const [productCount, setProductCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadOwnerData = useCallback(async (profile: UserProfile) => {
    setLoading(true)
    setError('')

    try {
      if (profile.role !== 'STORE_OWNER') {
        clearTokens()
        setUser(null)
        setError('This account is not a store-owner account.')
        return
      }

      const storesPayload = await getOwnerStores()
      const stores = extractList<StoreInfo>(storesPayload)

      if (stores.length === 0) {
        setUser(profile)
        setStore(null)
        setDashboard({})
        setProductCount(0)
        setError('Your account does not have a store yet. Store registration is the next step.')
        return
      }

      const selectedStore = stores[0]
      setUser(profile)
      setStore(selectedStore)

      const [dashboardPayload, productsPayload] = await Promise.all([
        getOwnerDashboard(selectedStore.id),
        getOwnerProducts(selectedStore.id),
      ])

      setDashboard(dashboardPayload as DashboardData)
      setProductCount(extractList<unknown>(productsPayload).length)
    } catch (err: unknown) {
      const status =
        typeof err === 'object' &&
        err !== null &&
        'response' in err &&
        typeof err.response === 'object' &&
        err.response !== null &&
        'status' in err.response
          ? err.response.status
          : undefined

      if (status === 401) {
        clearTokens()
        setUser(null)
        setStore(null)
        setError('Your session has expired. Please sign in again.')
      } else {
        setError('Could not load your store data. Check the backend and try again.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true

    async function restoreSession() {
      if (!getAccessToken()) {
        if (active) setLoading(false)
        return
      }

      try {
        const profile = await getMe() as UserProfile
        if (active) await loadOwnerData(profile)
      } catch {
        clearTokens()
        if (active) {
          setUser(null)
          setLoading(false)
        }
      }
    }

    void restoreSession()

    return () => {
      active = false
    }
  }, [loadOwnerData])

  function logout() {
    clearTokens()
    setUser(null)
    setStore(null)
    setDashboard({})
    setProductCount(0)
    setError('')
  }

  return (
    <BrowserRouter>
      {loading ? (
        <main className="flex min-h-screen items-center justify-center bg-[#f7f9f7]">
          <p className="text-sm text-gray-600">Loading your owner dashboard...</p>
        </main>
      ) : user && store ? (
        <>
          {error && (
            <div role="alert" className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {error}
            </div>
          )}
          <DashboardLayout
            user={user}
            store={store}
            dashboard={dashboard}
            productCount={productCount}
            onLogout={logout}
          />
        </>
      ) : user && !store ? (
        <main className="flex min-h-screen items-center justify-center bg-[#f7f9f7] px-4">
          <section className="max-w-lg rounded-2xl border border-gray-100 bg-white p-8 text-center shadow-sm">
            <Store className="mx-auto text-emerald-700" size={40} />
            <h1 className="mt-4 text-xl font-bold text-gray-900">Welcome, {user.full_name}</h1>
            <p className="mt-3 text-sm text-gray-600">
              {error || 'No store is registered on this account yet.'}
            </p>
            <button onClick={logout} className="mt-6 rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">
              Log out
            </button>
          </section>
        </main>
      ) : (
        <>
          {error && (
            <p role="alert" className="bg-amber-50 px-4 py-3 text-center text-sm text-amber-800">
              {error}
            </p>
          )}
          <Login onSuccess={(profile) => void loadOwnerData(profile)} />
        </>
      )}
    </BrowserRouter>
  )
}
