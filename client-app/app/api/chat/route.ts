import { NextRequest, NextResponse } from 'next/server';
import { Message as VercelAIMessage, StreamingTextResponse, experimental_StreamData } from 'ai';
import axios from 'axios';

// Configure the backend service URL
const BACKEND_URL = process.env.BACKEND_URL || 'https://your-railway-server.railway.app';

export async function POST(req: NextRequest) {
  try {
    // Get messages from request
    const { messages, sessionId } = await req.json();
    
    // Get the last message which is from the user
    const lastMessage = messages[messages.length - 1];
    
    // Meta information
    const data = new experimental_StreamData();
    
    // Forward the request to our Railway backend
    const response = await axios.post(`${BACKEND_URL}/api/chat/message`, {
      sessionId: sessionId || `session-${Date.now()}`,
      message: lastMessage.content
    });
    
    // Create a ReadableStream that sends the response gradually
    // This is a simplified example; in reality we'd stream the response
    const stream = new ReadableStream({
      async start(controller) {
        const assistantMessage = response.data.messages[response.data.messages.length - 1];
        
        if (assistantMessage && assistantMessage.content) {
          // Instead of sending all at once, we would stream it in a real implementation
          controller.enqueue(assistantMessage.content);
        }
        
        // Add metadata about the session
        data.append({ 
          sessionId: response.data.sessionId || sessionId,
          audioAvailable: Boolean(assistantMessage?.audioUrl)
        });
        
        controller.close();
      }
    });
    
    // Return a StreamingTextResponse, which will stream the response to the client
    return new StreamingTextResponse(stream, {}, data);
  } catch (error) {
    console.error('Error in chat API:', error);
    return NextResponse.json(
      { error: 'Failed to process chat request' },
      { status: 500 }
    );
  }
}

// Also handle GET requests to get session info
export async function GET(req: NextRequest) {
  try {
    const sessionId = req.nextUrl.searchParams.get('sessionId');
    
    if (!sessionId) {
      return NextResponse.json({ messages: [] });
    }
    
    // Fetch messages from backend for this session
    const response = await axios.get(`${BACKEND_URL}/api/chat/messages/${sessionId}`);
    
    return NextResponse.json(response.data);
  } catch (error) {
    console.error('Error fetching chat messages:', error);
    return NextResponse.json(
      { error: 'Failed to fetch chat messages' },
      { status: 500 }
    );
  }
} 