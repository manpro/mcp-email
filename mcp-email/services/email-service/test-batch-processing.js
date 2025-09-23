const axios = require('axios');

const PORT = process.env.PORT || 3014;
const BASE_URL = `http://localhost:${PORT}`;

// Test emails
const testEmails = [
  {
    uid: 'test-001',
    subject: 'Weekly Newsletter - Tech Updates',
    from: 'newsletter@techsite.com',
    text: 'This week in tech: AI advancements, new frameworks released. Click here to unsubscribe from our weekly updates.'
  },
  {
    uid: 'test-002',
    subject: 'Meeting Tomorrow at 2 PM',
    from: 'boss@company.com',
    text: 'Please review the attached project proposal before our meeting tomorrow. The deadline for feedback is end of day.'
  },
  {
    uid: 'test-003',
    subject: 'Special Offer - 50% OFF Today Only!',
    from: 'sales@store.com',
    text: 'Act now! Limited time offer. Huge discount on all items. This sale ends tonight!'
  },
  {
    uid: 'test-004',
    subject: 'Your Monthly Statement',
    from: 'bank@mybank.com',
    text: 'Your account statement for November is now available. Please log in to view your transactions.'
  },
  {
    uid: 'test-005',
    subject: 'Project Review Required',
    from: 'colleague@work.com',
    text: 'Hi, I need your review on the latest project deliverables. The client meeting is scheduled for next week.'
  }
];

async function testSingleEmail() {
  console.log('\n📧 Testing single email categorization...\n');
  try {
    const response = await axios.post(`${BASE_URL}/api/categorize`, testEmails[0]);
    console.log('Single email result:', JSON.stringify(response.data, null, 2));
    return true;
  } catch (error) {
    console.error('Single email test failed:', error.message);
    if (error.response) {
      console.error('Response:', error.response.data);
    }
    return false;
  }
}

async function testBatchProcessing() {
  console.log('\n📦 Testing batch email processing...\n');
  try {
    const response = await axios.post(`${BASE_URL}/api/categorize/batch`, {
      emails: testEmails
    });

    console.log(`Processed ${response.data.count} emails\n`);

    // Display results
    response.data.categorizations.forEach((cat, index) => {
      console.log(`\nEmail ${index + 1}: ${testEmails[index].subject}`);
      console.log(`  Category: ${cat.category}`);
      console.log(`  Priority: ${cat.priority}`);
      console.log(`  Sentiment: ${cat.sentiment || 'N/A'}`);
      console.log(`  Action Required: ${cat.action_required ? 'Yes' : 'No'}`);
      console.log(`  Summary: ${cat.summary}`);
      console.log(`  Confidence: ${cat.confidence || 'N/A'}`);
    });

    return true;
  } catch (error) {
    console.error('Batch processing test failed:', error.message);
    if (error.response) {
      console.error('Response:', error.response.data);
    }
    return false;
  }
}

async function testHealthCheck() {
  console.log('\n🏥 Testing health check...\n');
  try {
    const response = await axios.get(`${BASE_URL}/health`);
    console.log('Health status:', JSON.stringify(response.data, null, 2));
    return response.data.status === 'healthy' || response.data.status === 'degraded';
  } catch (error) {
    console.error('Health check failed:', error.message);
    return false;
  }
}

async function testMetrics() {
  console.log('\n📊 Testing metrics endpoint...\n');
  try {
    const response = await axios.get(`${BASE_URL}/metrics`);
    console.log('Metrics:', JSON.stringify(response.data, null, 2));
    return true;
  } catch (error) {
    console.error('Metrics test failed:', error.message);
    return false;
  }
}

async function testCacheWarming() {
  console.log('\n🔥 Testing cache warming...\n');
  try {
    const response = await axios.post(`${BASE_URL}/api/cache/warm/test-account-123`);
    console.log('Cache warming result:', JSON.stringify(response.data, null, 2));
    return true;
  } catch (error) {
    console.error('Cache warming test failed:', error.message);
    if (error.response) {
      console.error('Response:', error.response.data);
    }
    return false;
  }
}

async function runAllTests() {
  console.log('🚀 Starting Email Service Tests');
  console.log(`Testing service at: ${BASE_URL}`);
  console.log('=' . repeat(50));

  const tests = [
    { name: 'Health Check', fn: testHealthCheck },
    { name: 'Single Email', fn: testSingleEmail },
    { name: 'Batch Processing', fn: testBatchProcessing },
    { name: 'Metrics', fn: testMetrics },
    { name: 'Cache Warming', fn: testCacheWarming }
  ];

  const results = [];

  for (const test of tests) {
    const passed = await test.fn();
    results.push({ name: test.name, passed });

    // Small delay between tests
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  // Summary
  console.log('\n' + '=' . repeat(50));
  console.log('📋 Test Summary:');
  results.forEach(result => {
    const emoji = result.passed ? '✅' : '❌';
    console.log(`  ${emoji} ${result.name}: ${result.passed ? 'PASSED' : 'FAILED'}`);
  });

  const totalPassed = results.filter(r => r.passed).length;
  console.log(`\nTotal: ${totalPassed}/${results.length} tests passed`);
}

// Run tests
runAllTests().catch(error => {
  console.error('Test runner failed:', error);
  process.exit(1);
});