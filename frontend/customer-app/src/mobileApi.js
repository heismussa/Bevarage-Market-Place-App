import axios from 'axios';

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  'http://192.168.1.60:8000/api/v1';

export const mobileApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function getHealth() {
  const response = await mobileApi.get('/health/');
  return response.data;
}

export async function getStores() {
  const response = await mobileApi.get('/stores/');
  return response.data;
}

export async function getCategories() {
  const response = await mobileApi.get('/categories/');
  return response.data;
}
