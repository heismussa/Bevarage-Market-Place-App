import type { AxiosInstance } from 'axios'

export type AuthTokens = {
  access: string
  refresh: string
}

export type UserProfile = {
  id: number
  full_name: string
  phone: string
  email?: string | null
  role: string
}

export type LoginResponse = AuthTokens

export const api: AxiosInstance

export function saveTokens(tokens: AuthTokens): void
export function getAccessToken(): string | null
export function clearTokens(): void

export function login(phone: string, password: string): Promise<LoginResponse>

export function getMe(): Promise<UserProfile>
export function getOwnerStores(): Promise<unknown>
export function getOwnerDashboard(storeId: number | string): Promise<unknown>
export function getOwnerOrders(
  storeId: number | string,
  params?: Record<string, string | number | boolean>,
): Promise<unknown>
export function getOwnerProducts(storeId: number | string): Promise<unknown>
export function getHealth(): Promise<unknown>
export function getStores(): Promise<unknown>
export function getCategories(): Promise<unknown>
