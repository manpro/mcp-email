// Test the API connection to see what's happening

const apiBaseUrl = 'http://172.16.16.148:3012';
const selectedAccountId = 'primary';
const userId = 'default';

console.log('Testing API connection...');
console.log('API URL:', apiBaseUrl);
console.log('Account ID:', selectedAccountId);
console.log('User ID:', userId);

const url = `${apiBaseUrl}/recent-emails/${selectedAccountId}?limit=5`;
console.log('\nFetching from:', url);

fetch(url, {
  headers: {
    'x-user-id': userId
  }
})
.then(response => {
  console.log('\nResponse status:', response.status);
  console.log('Response OK:', response.ok);
  console.log('Response headers:', response.headers);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
})
.then(emails => {
  console.log(`\n✅ Success! Loaded ${emails.length} emails`);
  console.log('First email:', JSON.stringify(emails[0], null, 2));
})
.catch(error => {
  console.error('\n❌ Error:', error.message);
  console.error('Full error:', error);
});