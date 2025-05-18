import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

// Configure the backend service URL
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL;

export async function POST(req: NextRequest) {
  try {
    // Get messages from request
    const { messages, sessionId } = await req.json();
    
    // Get the last message which is from the user
    const lastMessage = messages[messages.length - 1];
    
    // Forward the request to our backend
    const response = await axios.post(`${BACKEND_URL}/api/chat/message`, {
      sessionId: sessionId || `session-${Date.now()}`,
      message: lastMessage.content
    });
    
    // Get the assistant's response
    const assistantMessage = response.data.messages[response.data.messages.length - 1];
    
    if (!assistantMessage || !assistantMessage.content) {
      throw new Error('No response from assistant');
    }
    
    // Create a custom streaming response
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        // Send the text in chunks to simulate streaming
        const text = assistantMessage.content;
        const chunks = text.match(/.{1,20}/g) || [];
        
        let index = 0;
        const interval = setInterval(() => {
          if (index < chunks.length) {
            controller.enqueue(encoder.encode(chunks[index]));
            index++;
          } else {
            clearInterval(interval);
            controller.close();
          }
        }, 100);
      }
    });
    
    // Return the streaming response
    return new Response(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
      }
    });
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