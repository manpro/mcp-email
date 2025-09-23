#!/usr/bin/env node

const FlexibleEmailAIAnalyzer = require('./flexible-ai-analyzer');

// Test emails
const testEmails = [
  {
    from: 'newsletter@techsite.com',
    subject: 'Weekly Tech Newsletter - AI Updates',
    text: 'This week in tech: New AI models released, quantum computing breakthrough. Unsubscribe at any time.'
  },
  {
    from: 'boss@company.com',
    subject: 'Urgent: Project deadline tomorrow',
    text: 'Please review the attached proposal before our meeting tomorrow at 2 PM. This is critical for our Q4 goals.'
  },
  {
    from: 'sales@store.com',
    subject: 'Special Offer - 50% OFF Today Only!',
    text: 'Act now! Limited time offer. Huge discount on all items. This sale ends tonight!'
  }
];

async function testLLMProviders() {
  console.log('🚀 Testing Flexible LLM Configuration\n');
  console.log('=' . repeat(50));

  const analyzer = new FlexibleEmailAIAnalyzer('./llm-config.json');

  // Show current configuration
  console.log('\n📋 Current Configuration:');
  const config = analyzer.getConfig();
  console.log('Active providers:', config.activeProviders.map(p => p.name).join(', '));
  console.log('Default provider:', config.default);
  console.log('Fallback enabled:', config.fallback.enabled);

  // Test connectivity to all providers
  console.log('\n🔌 Testing Provider Connectivity:');
  console.log('-' . repeat(50));
  const testResults = await analyzer.testAllProviders();

  // Count working providers
  const workingProviders = testResults.filter(r => r.success).length;
  const totalProviders = testResults.length;
  console.log(`\n📊 Results: ${workingProviders}/${totalProviders} providers working`);

  // Test email classification with the working providers
  if (workingProviders > 0) {
    console.log('\n📧 Testing Email Classification:');
    console.log('-' . repeat(50));

    for (let i = 0; i < testEmails.length; i++) {
      const email = testEmails[i];
      console.log(`\n${i + 1}. Testing: "${email.subject}"`);

      try {
        const start = Date.now();
        const result = await analyzer.classifyEmail(email);
        const duration = Date.now() - start;

        console.log(`   ✅ Success (${duration}ms)`);
        console.log(`   Provider: ${result.provider}`);
        console.log(`   Category: ${result.category}`);
        console.log(`   Priority: ${result.priority}`);
        console.log(`   Summary: ${result.summary}`);
      } catch (error) {
        console.log(`   ❌ Failed: ${error.message}`);
      }
    }
  } else {
    console.log('\n⚠️ No working LLM providers available');
    console.log('Using rule-based classification as fallback...\n');

    // Test with rule-based fallback
    for (let i = 0; i < testEmails.length; i++) {
      const email = testEmails[i];
      console.log(`\n${i + 1}. Testing: "${email.subject}"`);

      try {
        const result = await analyzer.classifyEmail(email);
        console.log(`   ✅ Success (rule-based)`);
        console.log(`   Category: ${result.category}`);
        console.log(`   Priority: ${result.priority}`);
        console.log(`   Action Required: ${result.actionRequired}`);
      } catch (error) {
        console.log(`   ❌ Failed: ${error.message}`);
      }
    }
  }

  console.log('\n' + '=' . repeat(50));
  console.log('✨ Test completed!');
}

// Interactive mode to update configuration
async function interactiveMode() {
  const analyzer = new FlexibleEmailAIAnalyzer('./llm-config.json');
  const readline = require('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const question = (query) => new Promise(resolve => rl.question(query, resolve));

  console.log('\n🔧 LLM Configuration Manager');
  console.log('Commands:');
  console.log('  1 - Test all providers');
  console.log('  2 - Toggle Mistral');
  console.log('  3 - Toggle GPT-OSS');
  console.log('  4 - Toggle Ollama');
  console.log('  5 - Update Mistral URL');
  console.log('  6 - Test email classification');
  console.log('  0 - Exit');

  while (true) {
    const choice = await question('\nChoice: ');

    switch (choice) {
      case '1':
        await analyzer.testAllProviders();
        break;

      case '2':
        const mistralEnabled = !analyzer.config.providers.mistral.enabled;
        analyzer.toggleProvider('mistral', mistralEnabled);
        break;

      case '3':
        const gptEnabled = !analyzer.config.providers['gpt-oss'].enabled;
        analyzer.toggleProvider('gpt-oss', gptEnabled);
        break;

      case '4':
        const ollamaEnabled = !analyzer.config.providers.ollama.enabled;
        analyzer.toggleProvider('ollama', ollamaEnabled);
        break;

      case '5':
        const newUrl = await question('Enter new Mistral URL (e.g., http://localhost:1234): ');
        analyzer.updateProvider('mistral', { url: newUrl });
        console.log(`✅ Updated Mistral URL to: ${newUrl}`);
        break;

      case '6':
        const email = testEmails[0];
        console.log(`Testing with: "${email.subject}"`);
        try {
          const result = await analyzer.classifyEmail(email);
          console.log('Result:', JSON.stringify(result, null, 2));
        } catch (error) {
          console.log('Error:', error.message);
        }
        break;

      case '0':
        rl.close();
        process.exit(0);

      default:
        console.log('Invalid choice');
    }
  }
}

// Main execution
async function main() {
  const args = process.argv.slice(2);

  if (args.includes('--interactive') || args.includes('-i')) {
    await interactiveMode();
  } else {
    await testLLMProviders();
  }
}

// Handle errors
process.on('unhandledRejection', (err) => {
  console.error('Error:', err);
  process.exit(1);
});

// Run the test
main().catch(console.error);