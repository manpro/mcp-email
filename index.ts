import express, { Request, Response } from 'express';
import axios from 'axios';
import { Pool } from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3111;
const GITEA_URL = 'http://172.16.16.138:8181';
const GITEA_TOKEN = '35cc69fd8ca1b7e6ee72fda67e7ee59d4ba47aa5';
const WEAVIATE_URL = process.env.WEAVIATE_URL || 'http://172.16.16.138:8686';

const dbMap: DbConfig = {
  finance: new Pool({ connectionString: process.env.PG_FINANCE_URL }),
  crm: new Pool({ connectionString: process.env.PG_CRM_URL }),
  internal: new Pool({ connectionString: process.env.PG_INTERNAL_URL })
};

app.use(express.json());

interface GiteaCreateIssueRequest {
  input: string;
}

interface ParsedIssueInput {
  repo: string;
  title: string;
  body: string;
}

interface PgQueryRequest {
  db: string;
  query: string;
}

interface WeaviateQueryRequest {
  input: string;
}

interface DbConfig {
  [key: string]: Pool;
}

function parseIssueInput(input: string): ParsedIssueInput {
  const parts = input.split(',').map(part => part.trim());
  
  const repo = parts.find(part => part.startsWith('repo='))?.replace('repo=', '') || '';
  const title = parts.find(part => part.startsWith('title='))?.replace('title=', '') || '';
  const body = parts.find(part => part.startsWith('body='))?.replace('body=', '') || '';
  
  return { repo, title, body };
}

async function createGiteaIssue(repo: string, title: string, body: string): Promise<any> {
  const url = `${GITEA_URL}/api/v1/repos/${repo}/issues`;
  
  const response = await axios.post(url, {
    title,
    body
  }, {
    headers: {
      'Authorization': `token ${GITEA_TOKEN}`,
      'Content-Type': 'application/json'
    }
  });
  
  return response.data;
}

async function executeQuery(db: string, query: string): Promise<any> {
  const pool = dbMap[db];
  
  if (!pool) {
    throw new Error(`Database '${db}' not found in configuration`);
  }
  
  const client = await pool.connect();
  
  try {
    const result = await client.query(query);
    return {
      rows: result.rows,
      rowCount: result.rowCount,
      fields: result.fields?.map(field => ({
        name: field.name,
        dataTypeID: field.dataTypeID
      }))
    };
  } finally {
    client.release();
  }
}

async function queryWeaviate(searchQuery: string): Promise<any> {
  const url = `${WEAVIATE_URL}/v1/graphql`;
  
  const query = `
    {
      Get {
        WorkPackage(
          nearText: {
            concepts: ["${searchQuery}"]
          }
          limit: 10
        ) {
          workPackageId
          subject
          description
          priority
          _additional {
            score
            id
          }
        }
      }
    }
  `;
  
  const response = await axios.post(url, {
    query: query
  }, {
    headers: {
      'Content-Type': 'application/json'
    }
  });
  
  return response.data;
}

app.post('/agent/gitea-create-issue', async (req: Request, res: Response) => {
  const startTime = Date.now();
  
  try {
    const { input }: GiteaCreateIssueRequest = req.body;
    
    console.log(`[${new Date().toISOString()}] Received issue creation request: "${input}"`);
    
    if (!input || typeof input !== 'string' || input.trim().length === 0) {
      console.log(`[${new Date().toISOString()}] Invalid input: ${JSON.stringify(input)}`);
      return res.status(400).json({
        error: 'Invalid input. Expected non-empty string with format: repo=owner/name, title=Issue Title, body=Issue Body'
      });
    }

    const parsed = parseIssueInput(input.trim());
    
    if (!parsed.repo || !parsed.title) {
      console.log(`[${new Date().toISOString()}] Missing required fields:`, parsed);
      return res.status(400).json({
        error: 'Missing required fields. Format: repo=owner/name, title=Issue Title, body=Issue Body'
      });
    }

    const result = await createGiteaIssue(parsed.repo, parsed.title, parsed.body);
    const duration = Date.now() - startTime;
    
    console.log(`[${new Date().toISOString()}] Issue created in ${duration}ms, ID: ${result.id}`);
    
    res.json({ output: result });
    
  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`[${new Date().toISOString()}] Error after ${duration}ms:`, error);
    
    if (axios.isAxiosError(error)) {
      console.error('Gitea API error:', error.response?.status, error.response?.data);
      return res.status(500).json({
        error: `Failed to create issue: ${error.response?.data?.message || error.message}`
      });
    }
    
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

app.post('/agent/pg-query', async (req: Request, res: Response) => {
  const startTime = Date.now();
  
  try {
    const { db, query }: PgQueryRequest = req.body;
    
    console.log(`[${new Date().toISOString()}] Received DB query: db="${db}", query length=${query?.length || 0}`);
    
    if (!db || typeof db !== 'string') {
      console.log(`[${new Date().toISOString()}] Invalid or missing db field:`, db);
      return res.status(400).json({
        error: 'Invalid or missing "db" field. Expected string with database name.'
      });
    }
    
    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      console.log(`[${new Date().toISOString()}] Invalid or missing query field:`, query);
      return res.status(400).json({
        error: 'Invalid or missing "query" field. Expected non-empty SQL string.'
      });
    }
    
    if (!dbMap[db]) {
      console.log(`[${new Date().toISOString()}] Database not found:`, db);
      const availableDbs = Object.keys(dbMap);
      return res.status(400).json({
        error: `Database "${db}" not found. Available databases: ${availableDbs.join(', ')}`
      });
    }

    const result = await executeQuery(db, query.trim());
    const duration = Date.now() - startTime;
    
    console.log(`[${new Date().toISOString()}] Query executed in ${duration}ms, returned ${result.rowCount} rows`);
    
    res.json({ 
      output: {
        database: db,
        query: query.trim(),
        result: result,
        metadata: {
          execution_time_ms: duration,
          timestamp: new Date().toISOString()
        }
      }
    });
    
  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`[${new Date().toISOString()}] DB query error after ${duration}ms:`, error);
    
    if (error instanceof Error) {
      return res.status(500).json({
        error: `Database query failed: ${error.message}`
      });
    }
    
    res.status(500).json({
      error: 'Internal server error during database query'
    });
  }
});

app.post('/agent/weaviate-query', async (req: Request, res: Response) => {
  const startTime = Date.now();
  
  try {
    const { input }: WeaviateQueryRequest = req.body;
    
    console.log(`[${new Date().toISOString()}] Received Weaviate query: "${input}"`);
    
    if (!input || typeof input !== 'string' || input.trim().length === 0) {
      console.log(`[${new Date().toISOString()}] Invalid input: ${JSON.stringify(input)}`);
      return res.status(400).json({
        error: 'Invalid input. Expected non-empty string with search query'
      });
    }

    const result = await queryWeaviate(input.trim());
    const duration = Date.now() - startTime;
    
    console.log(`[${new Date().toISOString()}] Weaviate query executed in ${duration}ms`);
    
    res.json({ 
      output: {
        query: input.trim(),
        results: result.data?.Get?.WorkPackage || [],
        metadata: {
          execution_time_ms: duration,
          timestamp: new Date().toISOString(),
          weaviate_url: WEAVIATE_URL
        }
      }
    });
    
  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`[${new Date().toISOString()}] Weaviate query error after ${duration}ms:`, error);
    
    if (axios.isAxiosError(error)) {
      console.error('Weaviate API error:', error.response?.status, error.response?.data);
      return res.status(500).json({
        error: `Failed to query Weaviate: ${error.response?.data?.message || error.message}`
      });
    }
    
    if (error instanceof Error) {
      return res.status(500).json({
        error: `Weaviate query failed: ${error.message}`
      });
    }
    
    res.status(500).json({
      error: 'Internal server error during Weaviate query'
    });
  }
});

app.listen(PORT, () => {
  console.log(`[${new Date().toISOString()}] MCP server listening on port ${PORT}`);
  console.log(`[${new Date().toISOString()}] Gitea endpoint: ${GITEA_URL}`);
  console.log(`[${new Date().toISOString()}] Weaviate endpoint: ${WEAVIATE_URL}`);
  console.log(`[${new Date().toISOString()}] Available databases: ${Object.keys(dbMap).join(', ')}`);
  
  process.on('SIGTERM', async () => {
    console.log('Closing database connections...');
    await Promise.all(Object.values(dbMap).map(pool => pool.end()));
    process.exit(0);
  });
});