import axios from 'axios';
import type { AxiosError, AxiosResponse } from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8100/api';

export const apiClient = axios.create({
  baseURL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'X-Account-Id': import.meta.env.VITE_ACCOUNT_ID ?? 'demo-account',
  },
});

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError | Error) => {
    if ('response' in error && error.response) {
      console.error('API error', error.response.status, error.response.data);
    } else {
      console.error('API error', error.message);
    }
    return Promise.reject(error);
  }
);
