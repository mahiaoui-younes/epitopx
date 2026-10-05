/**
 * Vercel Serverless Function entrypoint.
 * Routes all /api/* requests to the request handler in server.js.
 * Restores original requested URL when Vercel rewrites to this function.
 */
const requestHandler = require('../server');

module.exports = (req, res) => {
  const matched = req.headers['x-matched-path'] || req.headers['x-rewrite-url'];
  if (matched && !matched.endsWith('/api/index.js') && !matched.endsWith('/api/index')) {
    const query = req.url && req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
    req.url = matched + query;
  }
  return requestHandler(req, res);
};
