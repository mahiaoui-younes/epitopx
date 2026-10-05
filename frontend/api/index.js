/**
 * Vercel Serverless Function entrypoint.
 * Routes all /api/* requests to the existing request handler in server.js.
 */
const requestHandler = require('../server');

module.exports = (req, res) => {
  return requestHandler(req, res);
};
