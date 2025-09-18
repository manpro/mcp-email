#!/usr/bin/env node

import { spawn } from 'child_process';
import { stdin, stdout } from 'process';

// Test MCP server communication
async function testMCPServer() {
  console.log('Testing MCP Email Server...\n');
  
  const server = spawn('node', ['dist/index.js'], {
    stdio: ['pipe', 'pipe', 'inherit']
  });

  // Send initialization request
  const initRequest = {
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'test-client',
        version: '1.0.0'
      }
    }
  };

  console.log('Sending initialize request...');
  server.stdin.write(JSON.stringify(initRequest) + '\n');

  // Send list tools request
  const listToolsRequest = {
    jsonrpc: '2.0',
    id: 2,
    method: 'tools/list',
    params: {}
  };

  setTimeout(() => {
    console.log('Sending list tools request...');
    server.stdin.write(JSON.stringify(listToolsRequest) + '\n');
  }, 1000);

  // Send list providers request
  const listProvidersRequest = {
    jsonrpc: '2.0',
    id: 3,
    method: 'tools/call',
    params: {
      name: 'list_providers',
      arguments: {}
    }
  };

  setTimeout(() => {
    console.log('Sending list providers request...');
    server.stdin.write(JSON.stringify(listProvidersRequest) + '\n');
  }, 2000);

  // Handle server output
  server.stdout.on('data', (data) => {
    const lines = data.toString().split('\n').filter(line => line.trim());
    lines.forEach(line => {
      try {
        const response = JSON.parse(line);
        console.log('Server response:', JSON.stringify(response, null, 2));
      } catch (e) {
        console.log('Raw server output:', line);
      }
    });
  });

  server.on('error', (err) => {
    console.error('Server error:', err);
  });

  // Close after 5 seconds
  setTimeout(() => {
    console.log('\nClosing server...');
    server.kill();
    process.exit(0);
  }, 5000);
}

testMCPServer().catch(console.error);