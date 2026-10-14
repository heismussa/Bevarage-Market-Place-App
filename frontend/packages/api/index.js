import axios from 'axios'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

const ACCESS_TOKEN_KEY = 'beverage_access_token'
const REFRESH_TOKEN_KEY = 'beverage_refresh_token'

export function saveTokens({ access, refresh }) {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, access)
  sessionStorage.setItem(REFRESH_TOKEN_KEY, refresh)
}

export function getAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY)
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
}

api.interceptors.request.use((config) => {
  const token = getAccessToken()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

export async function login(phone, password) {
  const response = await api.post('/auth/login/', { phone, password })
  saveTokens(response.data)
  return response.data
}

export async function getMe() {
  const response = await api.get('/auth/me/')
  return response.data
}

export async function getOwnerStores() {
  const response = await api.get('/owner/stores/')
  return response.data
}

export async function getOwnerDashboard(storeId) {
  const response = await api.get(`/owner/stores/${storeId}/dashboard/`)
  return response.data
}

export async function getOwnerOrders(storeId, params = {}) {
  const response = await api.get(`/owner/stores/${storeId}/orders/`, {
    params,
  })
  return response.data
}

export async function getOwnerProducts(storeId) {
  const response = await api.get(`/owner/stores/${storeId}/products/`)
  return response.data
}

export async function getHealth() {
  const response = await api.get('/health/')
  return response.data
}

export async function getStores() {
  const response = await api.get('/stores/')
  return response.data
}

export async function getCategories() {
  const response = await api.get('/categories/')
  return response.data
}
