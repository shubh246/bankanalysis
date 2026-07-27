import axios from 'axios'

let rawBase = import.meta.env.VITE_API_URL
export let apiBase = 'http://127.0.0.1:8000/api'

if (rawBase) {
  if (!rawBase.startsWith('http://') && !rawBase.startsWith('https://')) {
    rawBase = `https://${rawBase}`
  }
  apiBase = `${rawBase.replace(/\/$/, '')}/api`
}

const TOKEN_KEY = 'auth_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

let onUnauthorized = () => {}
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

const api = axios.create({
  baseURL: apiBase,
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      clearToken()
      onUnauthorized()
    }
    return Promise.reject(err)
  }
)

export const login = (username, password) =>
  axios.post(`${apiBase}/auth/login`, { username, password })

export const register = (username, password) =>
  axios.post(`${apiBase}/auth/register`, { username, password })

export const uploadStatement = (file, password = '') => {
  const form = new FormData()
  form.append('file', file)
  if (password) {
    form.append('password', password)
  }
  return api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const listStatements = () => api.get('/statements')

export const getStatement = (id) => api.get(`/statements/${id}`)

export const deleteStatement = (id) => api.delete(`/statements/${id}`)

export const searchTransactions = (params) => api.get('/transactions', { params })

export const getFundFlow = (params) => api.get('/fundflow', { params })

export default api
