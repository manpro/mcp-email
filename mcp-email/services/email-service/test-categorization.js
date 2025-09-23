#!/usr/bin/env node

const axios = require('axios');

async function testCategorization() {
  const testEmails = [
    {
      from: 'newsletter@techcrunch.com',
      subject: 'Weekly Tech News Digest',
      text: 'This week in tech: AI advances, new startup funding rounds, and product launches. Click here to unsubscribe from our weekly newsletter.'
    },
    {
      from: 'boss@company.com',
      subject: 'Urgent: Project Deadline Tomorrow',
      text: 'Hi team, I need the quarterly report on my desk by tomorrow morning. This is critical for our board meeting. Please confirm receipt of this message.'
    },
    {
      from: 'sales@amazon.com',
      subject: '50% OFF Sale - Limited Time Only!',
      text: 'Shop our biggest sale of the year! Get 50% off on selected items. Act now, this offer expires in 24 hours!'
    }
  ];

  console.log('🧪 Testing Email Categorization Service...\n');

  for (const email of testEmails) {
    console.log(`📧 Testing: "${email.subject}"`);
    console.log(`   From: ${email.from}`);

    try {
      const response = await axios.post('http://localhost:3016/api/categorize', email);
      const result = response.data;

      console.log(`   ✅ Category: ${result.category}`);
      console.log(`   📊 Priority: ${result.priority}`);
      console.log(`   🎯 Confidence: ${result.confidence || 'N/A'}`);
      console.log(`   📝 Summary: ${result.summary}`);
      console.log(`   🤖 Provider: ${result.provider || 'Unknown'}`);
      console.log('   ---');
    } catch (error) {
      console.log(`   ❌ Error: ${error.message}`);
      console.log('   ---');
    }
  }

  // Test health endpoint
  console.log('\n📊 Service Health Check:');
  try {
    const health = await axios.get('http://localhost:3016/health');
    console.log(`   Status: ${health.data.status}`);
    console.log(`   Redis: ${health.data.services.redis ? '✅' : '❌'}`);
    console.log(`   AI Service: ${health.data.services.ai ? '✅' : '❌'}`);
    console.log(`   Cache Hit Rate: ${health.data.metrics.cacheHitRate}`);
    console.log(`   DB Hit Rate: ${health.data.metrics.dbHitRate}`);
    console.log(`   Avg Response Time: ${health.data.metrics.avgResponseTimeMs}ms`);
  } catch (error) {
    console.log(`   ❌ Health check failed: ${error.message}`);
  }
}

testCategorization().catch(console.error);