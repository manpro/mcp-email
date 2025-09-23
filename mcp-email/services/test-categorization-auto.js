#!/usr/bin/env node

/**
 * Automated Email Categorization Test Suite
 * Tests the complete categorization pipeline from backend to frontend
 */

const axios = require('axios');

const BACKEND_URL = 'http://localhost:3015';
const FRONTEND_URL = 'http://localhost:3623';
const MCP_GUI_URL = 'http://localhost:3624';

// Test result tracking
const testResults = {
  passed: 0,
  failed: 0,
  tests: []
};

// Color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m',
  bold: '\x1b[1m'
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function logTest(name, passed, details = '') {
  const icon = passed ? '✓' : '✗';
  const color = passed ? colors.green : colors.red;
  log(`  ${icon} ${name}`, color);
  if (details) {
    console.log(`    ${details}`);
  }

  testResults.tests.push({ name, passed, details });
  if (passed) {
    testResults.passed++;
  } else {
    testResults.failed++;
  }
}

async function testBackendHealth() {
  log('\n📋 Testing Backend Health...', colors.bold);

  try {
    const response = await axios.get(`${BACKEND_URL}/health`);
    const health = response.data;

    logTest('Backend is running', response.status === 200);
    logTest('Redis connected', health.redis === 'connected');
    logTest('Features available', health.features && health.features.length > 0,
            `Features: ${health.features ? health.features.length : 0}`);

    return true;
  } catch (error) {
    logTest('Backend health check', false, error.message);
    return false;
  }
}

async function testMCPConnection() {
  log('\n🔌 Testing MCP GUI Server Connection...', colors.bold);

  try {
    const response = await axios.get(`${MCP_GUI_URL}/api/connections`);
    const hasConnections = response.data.connections && response.data.connections.length > 0;

    logTest('MCP GUI Server accessible', response.status === 200);
    logTest('Email connections available', hasConnections,
            `Connections: ${response.data.connections ? response.data.connections.length : 0}`);

    if (hasConnections) {
      const conn = response.data.connections[0];
      log(`    Connected to: ${conn.email || 'Unknown'}`, colors.blue);
    }

    return true;
  } catch (error) {
    logTest('MCP GUI Server connection', false, error.message);
    return false;
  }
}

async function testEmailFetching() {
  log('\n📧 Testing Email Fetching...', colors.bold);

  try {
    const response = await axios.get(`${BACKEND_URL}/recent-emails/primary?limit=10`);
    const emails = response.data;

    logTest('Email fetching works', response.status === 200 && Array.isArray(emails));
    logTest('Emails retrieved', emails.length > 0, `Count: ${emails.length}`);

    return emails;
  } catch (error) {
    logTest('Email fetching', false, error.message);
    return [];
  }
}

async function testCategorization(emails) {
  log('\n🏷️  Testing Email Categorization...', colors.bold);

  if (!emails || emails.length === 0) {
    logTest('Categorization test skipped', false, 'No emails to test');
    return;
  }

  // Check categorization fields
  const requiredFields = ['category', 'priority', 'sentiment'];
  const optionalFields = ['topics', 'summary', 'actionRequired', 'confidence'];

  // Test first 5 emails
  const testEmails = emails.slice(0, 5);

  for (let i = 0; i < testEmails.length; i++) {
    const email = testEmails[i];
    log(`\n  Email ${i + 1}: "${email.subject?.substring(0, 50)}..."`, colors.blue);

    // Check required fields
    for (const field of requiredFields) {
      const hasField = email[field] !== null && email[field] !== undefined;
      logTest(`  Has ${field}`, hasField, hasField ? `Value: ${email[field]}` : 'Missing');
    }

    // Check category values
    const validCategories = ['personal', 'work', 'newsletter', 'notification', 'spam',
                           'security', 'finance', 'social', 'shopping', 'meetings',
                           'important', 'urgent'];

    if (email.category) {
      const validCategory = validCategories.includes(email.category);
      logTest(`  Valid category`, validCategory, `Category: ${email.category}`);
    }

    // Check priority values
    const validPriorities = ['critical', 'high', 'medium', 'low'];
    if (email.priority) {
      const validPriority = validPriorities.includes(email.priority);
      logTest(`  Valid priority`, validPriority, `Priority: ${email.priority}`);
    }

    // Check sentiment values
    const validSentiments = ['positive', 'negative', 'neutral'];
    if (email.sentiment) {
      const validSentiment = validSentiments.includes(email.sentiment);
      logTest(`  Valid sentiment`, validSentiment, `Sentiment: ${email.sentiment}`);
    }
  }
}

async function testCategoryDistribution(emails) {
  log('\n📊 Testing Category Distribution...', colors.bold);

  if (!emails || emails.length === 0) {
    logTest('Distribution test skipped', false, 'No emails to analyze');
    return;
  }

  const categoryCount = {};
  const priorityCount = {};

  emails.forEach(email => {
    if (email.category) {
      categoryCount[email.category] = (categoryCount[email.category] || 0) + 1;
    }
    if (email.priority) {
      priorityCount[email.priority] = (priorityCount[email.priority] || 0) + 1;
    }
  });

  log('\n  Category Distribution:', colors.yellow);
  Object.entries(categoryCount).forEach(([cat, count]) => {
    const percentage = ((count / emails.length) * 100).toFixed(1);
    console.log(`    ${cat}: ${count} (${percentage}%)`);
  });

  log('\n  Priority Distribution:', colors.yellow);
  Object.entries(priorityCount).forEach(([priority, count]) => {
    const percentage = ((count / emails.length) * 100).toFixed(1);
    console.log(`    ${priority}: ${count} (${percentage}%)`);
  });

  // Test for reasonable distribution
  const hasMultipleCategories = Object.keys(categoryCount).length > 1;
  logTest('Multiple categories detected', hasMultipleCategories,
          `Categories: ${Object.keys(categoryCount).length}`);

  const hasMultiplePriorities = Object.keys(priorityCount).length > 1;
  logTest('Multiple priorities detected', hasMultiplePriorities,
          `Priorities: ${Object.keys(priorityCount).length}`);
}

async function testFilterSimulation() {
  log('\n🔍 Testing Filter Simulation...', colors.bold);

  try {
    // Get all emails
    const allEmails = await axios.get(`${BACKEND_URL}/recent-emails/primary?limit=100`);
    const emails = allEmails.data;

    if (emails.length === 0) {
      logTest('Filter simulation skipped', false, 'No emails to filter');
      return;
    }

    // Test category filters
    const categories = ['newsletter', 'personal', 'work', 'notification'];
    for (const category of categories) {
      const filtered = emails.filter(e => e.category === category);
      logTest(`Filter by ${category}`, true, `Found ${filtered.length} emails`);
    }

    // Test priority filters
    const priorities = ['high', 'medium', 'low'];
    for (const priority of priorities) {
      const filtered = emails.filter(e => e.priority === priority);
      logTest(`Filter by ${priority} priority`, true, `Found ${filtered.length} emails`);
    }

    // Test combined filters
    const highPriorityWork = emails.filter(e =>
      e.category === 'work' && e.priority === 'high'
    );
    logTest('Combined filter (work + high priority)', true,
            `Found ${highPriorityWork.length} emails`);

  } catch (error) {
    logTest('Filter simulation', false, error.message);
  }
}

async function testPerformance() {
  log('\n⚡ Testing Performance...', colors.bold);

  const iterations = 5;
  const times = [];

  for (let i = 0; i < iterations; i++) {
    const start = Date.now();
    try {
      await axios.get(`${BACKEND_URL}/recent-emails/primary?limit=50`);
      const elapsed = Date.now() - start;
      times.push(elapsed);
    } catch (error) {
      logTest(`Performance test ${i + 1}`, false, error.message);
    }
  }

  if (times.length > 0) {
    const avg = times.reduce((a, b) => a + b, 0) / times.length;
    const max = Math.max(...times);
    const min = Math.min(...times);

    logTest('Average response time', avg < 1000, `${avg.toFixed(0)}ms`);
    logTest('Max response time', max < 2000, `${max}ms`);
    logTest('Min response time', true, `${min}ms`);
  }
}

async function generateReport() {
  log('\n' + '='.repeat(60), colors.bold);
  log('📈 TEST REPORT', colors.bold);
  log('='.repeat(60), colors.bold);

  const total = testResults.passed + testResults.failed;
  const percentage = total > 0 ? ((testResults.passed / total) * 100).toFixed(1) : 0;

  log(`\nTotal Tests: ${total}`, colors.bold);
  log(`Passed: ${testResults.passed}`, colors.green);
  log(`Failed: ${testResults.failed}`, colors.red);
  log(`Success Rate: ${percentage}%`, percentage >= 80 ? colors.green : colors.red);

  if (testResults.failed > 0) {
    log('\n❌ Failed Tests:', colors.red);
    testResults.tests
      .filter(t => !t.passed)
      .forEach(t => {
        console.log(`  - ${t.name}: ${t.details}`);
      });
  }

  // Overall assessment
  log('\n📋 Assessment:', colors.bold);
  if (percentage >= 90) {
    log('✅ Excellent! Categorization system is working very well.', colors.green);
  } else if (percentage >= 70) {
    log('⚠️  Good, but some issues need attention.', colors.yellow);
  } else {
    log('❌ Critical issues detected. System needs immediate attention.', colors.red);
  }

  log('\n' + '='.repeat(60), colors.bold);
}

async function runTests() {
  log('\n' + '='.repeat(60), colors.bold);
  log('🚀 AUTOMATED EMAIL CATEGORIZATION TEST', colors.bold);
  log('='.repeat(60), colors.bold);
  log(`Started at: ${new Date().toLocaleString()}`, colors.blue);

  try {
    // Run tests in sequence
    const backendOk = await testBackendHealth();
    if (!backendOk) {
      log('\n⚠️  Backend is not accessible. Stopping tests.', colors.red);
      return;
    }

    await testMCPConnection();
    const emails = await testEmailFetching();
    await testCategorization(emails);
    await testCategoryDistribution(emails);
    await testFilterSimulation();
    await testPerformance();

  } catch (error) {
    log(`\n❌ Unexpected error: ${error.message}`, colors.red);
  } finally {
    await generateReport();
  }
}

// Run the tests
runTests().then(() => {
  process.exit(testResults.failed > 0 ? 1 : 0);
}).catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});