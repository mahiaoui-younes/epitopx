/**
 * Vercel Serverless Function entrypoint (Root-level).
 * Forwards all /api/* requests to the requestHandler in frontend/server.js.
 */
const requestHandler = require('../frontend/server');

module.exports = (req, res) => {
  const matched = req.headers['x-matched-path'] || req.headers['x-rewrite-url'];
  if (matched && !matched.endsWith('/api/index.js') && !matched.endsWith('/api/index')) {
    const query = req.url && req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
    req.url = matched + query;
  }
  return requestHandler(req, res);
};
