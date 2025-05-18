import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

// Configure the backend service URL
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL;

// Handle audio transcription
export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const audioFile = formData.get('audio') as File;
    const sessionId = formData.get('sessionId') as string;
    
    if (!audioFile) {
      return NextResponse.json(
        { error: 'Audio file is required' },
        { status: 400 }
      );
    }
    
    // Convert audio file to Base64
    const arrayBuffer = await audioFile.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    const base64Audio = buffer.toString('base64');
    
    // Forward to backend server
    const response = await axios.post(`${BACKEND_URL}/api/chat/audio`, {
      sessionId: sessionId || `session-${Date.now()}`,
      audio_base64: base64Audio
    });
    
    return NextResponse.json(response.data);
  } catch (error) {
    console.error('Error in audio API:', error);
    return NextResponse.json(
      { error: 'Failed to process audio' },
      { status: 500 }
    );
  }
}

// Get audio synthesis for a message
export async function GET(req: NextRequest) {
  try {
    const messageId = req.nextUrl.searchParams.get('messageId');
    const sessionId = req.nextUrl.searchParams.get('sessionId');
    
    if (!messageId || !sessionId) {
      return NextResponse.json(
        { error: 'Message ID and Session ID are required' },
        { status: 400 }
      );
    }
    
    // Fetch audio from backend
    const response = await axios.get(`${BACKEND_URL}/api/chat/audio`, {
      params: { messageId, sessionId }
    });
    
    // Check if we have audio data
    if (!response.data.audio_base64) {
      return NextResponse.json(
        { error: 'No audio available for this message' },
        { status: 404 }
      );
    }
    
    // Return the audio data
    return NextResponse.json({
      audio_base64: response.data.audio_base64
    });
  } catch (error) {
    console.error('Error fetching audio:', error);
    return NextResponse.json(
      { error: 'Failed to fetch audio' },
      { status: 500 }
    );
  }
} 