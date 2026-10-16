import { useState, type FormEvent } from 'react'
import { Store, Eye, EyeOff, LoaderCircle } from 'lucide-react'
import { clearTokens, getMe, login } from '@beverage/api'

type UserProfile = {
  id: number
  full_name: string
  phone: string
  email?: string | null
  role: string
}

type LoginProps = {
  onSuccess: (user: UserProfile) => void
}

export default function Login({ onSuccess }: LoginProps) {
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(phone.trim(), password)
      const user = (await getMe()) as UserProfile

      if (user.role !== 'STORE_OWNER') {
        clearTokens()
        setError('This account is not a store-owner account.')
        return
      }

      onSuccess(user)
    } catch (err: unknown) {
      clearTokens()

      const message =
        typeof err === 'object' &&
        err !== null &&
        'response' in err &&
        typeof err.response === 'object' &&
        err.response !== null &&
        'data' in err.response
          ? JSON.stringify(err.response.data)
          : 'Unable to connect to the server. Check that the Django backend is running.'

      setError(
        message.includes('401') || message.includes('authentication')
          ? 'Incorrect phone number or password.'
          : message,
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f7f9f7] px-4 py-10">
      <section className="w-full max-w-md rounded-3xl border border-gray-100 bg-white p-7 shadow-sm sm:p-9">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-700 text-white">
          <Store size={28} />
        </div>

        <div className="mt-6 text-center">
          <h1 className="text-2xl font-bold text-gray-900">BeverageHub</h1>
          <p className="mt-2 text-sm text-gray-500">
            Sign in to manage your beverage store.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <div>
            <label
              htmlFor="phone"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Phone number
            </label>
            <input
              id="phone"
              type="tel"
              autoComplete="username"
              placeholder="+255712345678"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              required
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                className="w-full rounded-xl border border-gray-200 px-4 py-3 pr-12 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
              />
              <button
                type="button"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
              >
                {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
              </button>
            </div>
          </div>

          {error && (
            <p
              role="alert"
              className="rounded-xl bg-red-50 p-3 text-sm text-red-700"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 py-3 font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading && <LoaderCircle size={18} className="animate-spin" />}
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-center text-xs leading-5 text-gray-500">
          Use your registered store-owner account. Customer accounts cannot
          access this dashboard.
        </p>
      </section>
    </main>
  )
}
