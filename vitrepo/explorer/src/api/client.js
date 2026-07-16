import axios from 'axios';

const api = axios.create({
  baseURL: '/api/explorer',
  timeout: 10000,
});

export const explorerApi = {
  getBlocks: (limit = 20, offset = 0) =>
    api.get(`/blocks?limit=${limit}&offset=${offset}`).then(res => res.data),

  getBlock: (id) =>
    api.get(`/blocks/${id}`).then(res => res.data),

  getTransactions: (limit = 20, offset = 0, address = '') =>
    api.get(`/transactions?limit=${limit}&offset=${offset}${address ? `&address=${address}` : ''}`).then(res => res.data),

  getTransaction: (hash) =>
    api.get(`/tx/${hash}`).then(res => res.data),

  getAccount: (address) =>
    api.get(`/accounts/${address}`).then(res => res.data),

  getAccountTransactions: (address, limit = 20, offset = 0) =>
    api.get(`/accounts/${address}/transactions?limit=${limit}&offset=${offset}`).then(res => res.data),

  getNodes: (limit = 50) =>
    api.get(`/nodes?limit=${limit}`).then(res => res.data),

  getNodesMap: () =>
    api.get('/nodes/map').then(res => res.data),

  getStats: () =>
    api.get('/blocks/stats').then(res => res.data),
};
