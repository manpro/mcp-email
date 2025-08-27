import { NextRequest, NextResponse } from 'next/server';

// Use backend container name when running in Docker
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

function buildHeaders(request: NextRequest) {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };

  // Forward authorization header
  const authorization = request.headers.get('authorization');
  if (authorization) {
    headers['Authorization'] = authorization;
  }

  // Forward X-User-ID header
  const userId = request.headers.get('x-user-id');
  if (userId) {
    headers['X-User-ID'] = userId;
  }

  // Forward session token cookie
  const sessionToken = request.cookies.get('session_token')?.value;
  if (sessionToken) {
    headers['Cookie'] = `session_token=${sessionToken}`;
  }

  return headers;
}

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path?.join('/') || '';
  const searchParams = request.nextUrl.searchParams.toString();
  
  // Handle search options endpoint locally
  if (path === 'search/options') {
    return NextResponse.json({
      "filters": {
        "categories": ["Technology", "AI Research", "Cryptocurrency", "Blockchain", "DeFi", "NFT"],
        "languages": ["en", "sv"],
        "date_ranges": [
          {"label": "Last 24 hours", "value": "1d"},
          {"label": "Last week", "value": "7d"}, 
          {"label": "Last month", "value": "30d"},
          {"label": "Last 3 months", "value": "90d"},
          {"label": "All time", "value": "all"}
        ]
      },
      "search_modes": [
        {"label": "Hybrid (Recommended)", "value": "hybrid"},
        {"label": "Semantic", "value": "semantic"},
        {"label": "Keyword", "value": "keyword"}
      ],
      "stats": {"total_chunks": 5680}
    });
  }
  
  // Some endpoints are directly on root (like /items), others under /api
  const rootEndpoints = ['items', 'config', 'health', 'refresh', 'img', 'articles', 'extraction', 'diagnostics', 'images'];
  const isRootEndpoint = rootEndpoints.some(endpoint => path.startsWith(endpoint));
  
  const url = isRootEndpoint 
    ? `${BACKEND_URL}/${path}${searchParams ? `?${searchParams}` : ''}`
    : `${BACKEND_URL}/api/${path}${searchParams ? `?${searchParams}` : ''}`;

  try {
    const response = await fetch(url, {
      headers: buildHeaders(request),
      cache: 'no-store',
    });

    const data = await response.json();
    
    // Create response with Set-Cookie header if present
    const nextResponse = NextResponse.json(data, {
      status: response.status,
      headers: {
        'Cache-Control': 'no-store, max-age=0',
      },
    });

    // Forward Set-Cookie header for auth
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      nextResponse.headers.set('Set-Cookie', setCookie);
    }
    
    return nextResponse;
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from backend' },
      { status: 500 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path?.join('/') || '';
  
  // Some endpoints are directly on root (like /items), others under /api
  const rootEndpoints = ['items', 'config', 'health', 'refresh', 'img', 'articles', 'extraction', 'diagnostics', 'images'];
  const isRootEndpoint = rootEndpoints.some(endpoint => path.startsWith(endpoint));
  
  const url = isRootEndpoint 
    ? `${BACKEND_URL}/${path}`
    : `${BACKEND_URL}/api/${path}`;

  try {
    let body = {};
    try {
      body = await request.json();
    } catch (e) {
      // Handle empty body - refresh endpoint doesn't need a body
      body = {};
    }
    
    const headers = buildHeaders(request);
    headers['Content-Type'] = 'application/json';
    
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    const data = await response.json();
    
    // Create response with Set-Cookie header if present
    const nextResponse = NextResponse.json(data, {
      status: response.status,
    });

    // Forward Set-Cookie header for auth
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      nextResponse.headers.set('Set-Cookie', setCookie);
    }
    
    return nextResponse;
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to post to backend' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path?.join('/') || '';
  
  // Some endpoints are directly on root (like /items), others under /api
  const rootEndpoints = ['items', 'config', 'health', 'refresh', 'img', 'articles', 'extraction', 'diagnostics', 'images'];
  const isRootEndpoint = rootEndpoints.some(endpoint => path.startsWith(endpoint));
  
  const url = isRootEndpoint 
    ? `${BACKEND_URL}/${path}`
    : `${BACKEND_URL}/api/${path}`;

  try {
    const body = await request.json();
    
    const headers = buildHeaders(request);
    headers['Content-Type'] = 'application/json';
    
    const response = await fetch(url, {
      method: 'PUT',
      headers,
      body: JSON.stringify(body),
    });

    const data = await response.json();
    
    // Create response with Set-Cookie header if present
    const nextResponse = NextResponse.json(data, {
      status: response.status,
    });

    // Forward Set-Cookie header for auth
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      nextResponse.headers.set('Set-Cookie', setCookie);
    }
    
    return nextResponse;
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to update backend' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path?.join('/') || '';
  
  // Some endpoints are directly on root (like /items), others under /api
  const rootEndpoints = ['items', 'config', 'health', 'refresh', 'img', 'articles', 'extraction', 'diagnostics', 'images'];
  const isRootEndpoint = rootEndpoints.some(endpoint => path.startsWith(endpoint));
  
  const url = isRootEndpoint 
    ? `${BACKEND_URL}/${path}`
    : `${BACKEND_URL}/api/${path}`;

  try {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: buildHeaders(request),
    });

    const data = await response.json();
    
    // Create response with Set-Cookie header if present
    const nextResponse = NextResponse.json(data, {
      status: response.status,
    });

    // Forward Set-Cookie header for auth
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      nextResponse.headers.set('Set-Cookie', setCookie);
    }
    
    return nextResponse;
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to delete from backend' },
      { status: 500 }
    );
  }
}