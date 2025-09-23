const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.PORT || 3000;

// CORS configuration - Allow multiple origins
app.use(cors({
  origin: function (origin, callback) {
    // Allow requests with no origin (like Postman or curl)
    if (!origin) return callback(null, true);

    // List of allowed origins
    const allowedOrigins = [
      'http://localhost:3623',
      'http://172.16.16.148:3623',
      'http://server3:3623',
      'http://frontend:3623',
      process.env.FRONTEND_URL
    ].filter(Boolean);

    if (allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      console.log('CORS blocked origin:', origin);
      callback(null, true); // Allow anyway for development
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'api-gateway' });
});

// Email service proxy - handle both patterns
// Now pointing to host service instead of Docker for IMAP connectivity
const EMAIL_SERVICE_HOST = process.env.EMAIL_SERVICE_URL || 'http://172.16.16.148:3012';

app.use('/api/email', createProxyMiddleware({
  target: EMAIL_SERVICE_HOST,
  changeOrigin: true,
  pathRewrite: { '^/api/email': '' }
}));

// Direct email API routes (for frontend compatibility)
app.use('/connect', createProxyMiddleware({
  target: EMAIL_SERVICE_HOST,
  changeOrigin: true
}));

app.use('/api/connect', createProxyMiddleware({
  target: EMAIL_SERVICE_HOST,
  changeOrigin: true,
  pathRewrite: { '^/api': '' }
}));

app.use('/disconnect', createProxyMiddleware({
  target: EMAIL_SERVICE_HOST,
  changeOrigin: true
}));

app.use('/api/mailboxes', createProxyMiddleware({
  target: EMAIL_SERVICE_HOST,
  changeOrigin: true
}));

app.use('/api/recent-emails', createProxyMiddleware({
  target: EMAIL_SERVICE_HOST,
  changeOrigin: true
}));

app.use('/api/emails', createProxyMiddleware({
  target: EMAIL_SERVICE_HOST,
  changeOrigin: true
}));

// AI proxy service (GPT-OSS 20B external service)
app.use('/api/ai', createProxyMiddleware({
  target: process.env.GPT_OSS_URL || 'http://172.16.16.148:8085',
  changeOrigin: true,
  pathRewrite: { '^/api/ai': '' }, // Remove /api/ai prefix, GPT-OSS expects /v1/chat/completions directly
  onProxyReq: (proxyReq, req) => {
    console.log(`Proxying AI request to GPT-OSS 20B: ${req.method} ${req.path}`);
  },
  onProxyRes: (proxyRes, req, res) => {
    console.log(`GPT-OSS 20B response status: ${proxyRes.statusCode}`);
  }
}));

// Error handling
app.use((err, req, res, next) => {
  console.error('Gateway error:', err);
  res.status(500).json({
    error: 'Internal gateway error',
    message: err.message
  });
});

app.listen(PORT, () => {
  console.log(`API Gateway running on port ${PORT}`);
  console.log('Routes:');
  console.log('  /health - Health check');
  console.log('  /api/email/* - Email service');
  console.log('  /api/mailboxes - Email mailboxes');
  console.log('  /api/recent-emails - Recent emails');
  console.log('  /api/emails/* - Email operations');
  console.log('  /api/ai/* - AI service (GPT-OSS)');
});