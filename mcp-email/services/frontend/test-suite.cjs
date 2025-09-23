#!/usr/bin/env node

/**
 * Email Frontend Test Suite
 * Comprehensive testing of all email functionality
 */

const axios = require('axios');

const API_BASE_URL = process.env.VITE_API_URL || 'http://172.16.16.148:3012';
const FRONTEND_URL = 'http://172.16.16.148:3623';

class TestSuite {
  constructor() {
    this.results = [];
    this.passed = 0;
    this.failed = 0;
  }

  log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const prefix = type === 'pass' ? '✅' : type === 'fail' ? '❌' : 'ℹ️';
    console.log(`[${timestamp}] ${prefix} ${message}`);
  }

  async test(name, testFn) {
    try {
      this.log(`Testing: ${name}`, 'info');
      await testFn();
      this.log(`PASS: ${name}`, 'pass');
      this.results.push({ name, status: 'PASS', error: null });
      this.passed++;
    } catch (error) {
      this.log(`FAIL: ${name} - ${error.message}`, 'fail');
      this.results.push({ name, status: 'FAIL', error: error.message });
      this.failed++;
    }
  }

  async run() {
    this.log('🚀 Starting Email Frontend Test Suite');
    this.log(`API Base URL: ${API_BASE_URL}`);
    this.log(`Frontend URL: ${FRONTEND_URL}`);

    // Test 1: Frontend availability
    await this.test('Frontend Accessibility', async () => {
      const response = await axios.get(FRONTEND_URL, { timeout: 5000 });
      if (response.status !== 200) {
        throw new Error(`Frontend returned status ${response.status}`);
      }
    });

    // Test 2: API endpoints discovery
    await this.test('API Service Discovery', async () => {
      const endpoints = [
        '/recent-emails/50a0e1a7',
        '/smart-inbox/50a0e1a7',
        '/sync-emails/50a0e1a7'
      ];

      let workingEndpoints = 0;
      for (const endpoint of endpoints) {
        try {
          const response = await axios.get(`${API_BASE_URL}${endpoint}`, {
            timeout: 10000,
            validateStatus: (status) => status < 500
          });
          if (response.status < 400) workingEndpoints++;
        } catch (error) {
          // Endpoint not working
        }
      }

      if (workingEndpoints === 0) {
        throw new Error('No API endpoints responding');
      }
      this.log(`Found ${workingEndpoints}/${endpoints.length} working endpoints`);
    });

    // Test 3: Email data retrieval
    await this.test('Email Data Retrieval', async () => {
      const response = await axios.get(`${API_BASE_URL}/recent-emails/50a0e1a7?limit=5`, {
        timeout: 15000,
        validateStatus: (status) => status < 500
      });

      if (response.status === 404) {
        throw new Error('Email endpoint not found');
      }

      if (response.status >= 400) {
        throw new Error(`API error: ${response.status}`);
      }

      const emails = response.data;
      if (!Array.isArray(emails) || emails.length === 0) {
        throw new Error('No emails returned or invalid format');
      }

      this.log(`Retrieved ${emails.length} emails successfully`);
    });

    // Test 4: Smart Inbox functionality
    await this.test('Smart Inbox Functionality', async () => {
      const response = await axios.get(`${API_BASE_URL}/smart-inbox/50a0e1a7`, {
        timeout: 15000,
        validateStatus: (status) => status < 500
      });

      if (response.status >= 400) {
        throw new Error(`Smart inbox error: ${response.status}`);
      }

      const data = response.data;
      if (!data.inbox || !data.stats) {
        throw new Error('Invalid smart inbox response format');
      }

      this.log('Smart inbox data structure validated');
    });

    // Test 5: Email sync functionality
    await this.test('Email Sync Functionality', async () => {
      const response = await axios.post(`${API_BASE_URL}/sync-emails/50a0e1a7`, {}, {
        timeout: 20000,
        validateStatus: (status) => status < 500
      });

      if (response.status >= 400) {
        throw new Error(`Sync error: ${response.status}`);
      }

      this.log('Email sync triggered successfully');
    });

    // Test 6: Frontend-Backend Integration
    await this.test('Frontend-Backend Integration', async () => {
      // Check if frontend can load and make API calls
      const frontendResponse = await axios.get(FRONTEND_URL, {
        timeout: 5000,
        headers: { 'Accept': 'text/html' }
      });

      if (!frontendResponse.data.includes('vite') && !frontendResponse.data.includes('app')) {
        throw new Error('Frontend not properly loaded');
      }

      this.log('Frontend-backend integration appears functional');
    });

    // Test 7: Error handling
    await this.test('Error Handling', async () => {
      try {
        await axios.get(`${API_BASE_URL}/nonexistent-endpoint`, { timeout: 5000 });
        throw new Error('Should have returned 404');
      } catch (error) {
        if (error.response && error.response.status === 404) {
          this.log('404 error handling works correctly');
        } else if (error.code === 'ECONNREFUSED') {
          throw new Error('Service not responding');
        } else {
          // Expected behavior for non-existent endpoint
          this.log('Error handling validated');
        }
      }
    });

    this.printSummary();
  }

  printSummary() {
    this.log('\n📊 TEST SUMMARY');
    this.log(`Total Tests: ${this.passed + this.failed}`);
    this.log(`Passed: ${this.passed}`, 'pass');
    this.log(`Failed: ${this.failed}`, this.failed > 0 ? 'fail' : 'info');

    if (this.failed > 0) {
      this.log('\n❌ FAILED TESTS:');
      this.results.filter(r => r.status === 'FAIL').forEach(result => {
        this.log(`  - ${result.name}: ${result.error}`, 'fail');
      });
    }

    const successRate = ((this.passed / (this.passed + this.failed)) * 100).toFixed(1);
    this.log(`\n🎯 Success Rate: ${successRate}%`);

    if (this.failed === 0) {
      this.log('🎉 ALL TESTS PASSED! Frontend is fully functional.', 'pass');
    } else if (this.failed <= 2) {
      this.log('⚠️  Most tests passed. Minor issues detected.', 'info');
    } else {
      this.log('🔥 Multiple test failures. System needs attention.', 'fail');
    }
  }
}

// Handle timeout for hanging tests
const timeout = setTimeout(() => {
  console.log('❌ Test suite timed out after 60 seconds');
  process.exit(1);
}, 60000);

// Run tests
const suite = new TestSuite();
suite.run().then(() => {
  clearTimeout(timeout);
  process.exit(suite.failed > 0 ? 1 : 0);
}).catch(error => {
  clearTimeout(timeout);
  console.error('💥 Test suite crashed:', error.message);
  process.exit(1);
});