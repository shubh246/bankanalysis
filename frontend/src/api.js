import axios from 'axios'

let rawBase = import.meta.env.VITE_API_URL
let apiBase = 'http://127.0.0.1:8000/api'

if (rawBase) {
  if (!rawBase.startsWith('http://') && !rawBase.startsWith('https://')) {
    rawBase = `https://${rawBase}`
  }
  apiBase = `${rawBase.replace(/\/$/, '')}/api`
}

const api = axios.create({
  baseURL: apiBase,
})

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

export const deleteStatement = (id) => api.delete(`/statements/${id}`)

export const searchTransactions = (params) => api.get('/transactions', { params })

export const getFundFlow = (params) => api.get('/fundflow', { params })

export default api
