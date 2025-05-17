import { NextResponse } from 'next/server';

// This is a server-side API route that securely fetches RunPod endpoints
export async function GET() {
  try {
    // First try to get endpoints from our backend server
    const BACKEND_URL = process.env.BACKEND_URL || 'https://your-railway-server.railway.app';
    
    try {
      const backendResponse = await fetch(`${BACKEND_URL}/api/endpoints`, { 
        next: { revalidate: 3600 } // Cache for 1 hour  
      });
      
      if (backendResponse.ok) {
        const data = await backendResponse.json();
        if (data.success && data.endpoints) {
          return NextResponse.json(data);
        }
      }
    } catch (backendError) {
      console.warn('Could not fetch from backend, falling back to direct RunPod API:', backendError);
    }
    
    // Fallback: Fetch directly from RunPod if backend is not available
    const RUNPOD_API_KEY = process.env.RUNPOD_API_KEY;
    
    if (!RUNPOD_API_KEY) {
      throw new Error('RunPod API key is not configured');
    }
    
    // Fetch endpoints directly from RunPod
    const response = await fetch('https://api.runpod.io/graphql', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${RUNPOD_API_KEY}`
      },
      body: JSON.stringify({
        query: `
          query {
            myself {
              endpoints {
                id
                name
                status
              }
            }
          }
        `
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch endpoints from RunPod');
    }
    
    const data = await response.json();
    const endpoints = data.data?.myself?.endpoints || [];
    
    // Extract the endpoints we need
    let whisperEndpointId = '';
    let llmEndpointId = '';
    let ttsEndpointId = '';
    
    // Find endpoints by name
    for (const endpoint of endpoints) {
      if (endpoint.name === 'whisper_worker') {
        whisperEndpointId = endpoint.id;
      } else if (endpoint.name === 'llm_worker') {
        llmEndpointId = endpoint.id;
      } else if (endpoint.name === 'tts_worker') {
        ttsEndpointId = endpoint.id;
      }
    }
    
    const API_BASE = 'https://api.runpod.ai/v2';
    
    return NextResponse.json({
      success: true,
      endpoints: {
        whisperEndpoint: `${API_BASE}/${whisperEndpointId}`,
        llmEndpoint: `${API_BASE}/${llmEndpointId}`,
        ttsEndpoint: `${API_BASE}/${ttsEndpointId}`
      }
    });
  } catch (error) {
    console.error('Error fetching endpoints:', error);
    return NextResponse.json(
      { 
        success: false,
        error: 'Failed to fetch endpoints' 
      },
      { status: 500 }
    );
  }
} 