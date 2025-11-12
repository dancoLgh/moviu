import { NextRequest, NextResponse } from 'next/server';

const FUNCTIONS_URL = process.env.NEXT_PUBLIC_SUPABASE_FUNCTIONS_URL;

export async function POST(request: NextRequest) {
  if (!FUNCTIONS_URL) {
    return NextResponse.json({ error: 'Functions URL no configurada' }, { status: 500 });
  }

  const payload = await request.json();
  const response = await fetch(`${FUNCTIONS_URL}/book-makeup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const text = await response.text();
  try {
    return NextResponse.json(JSON.parse(text), { status: response.status });
  } catch (error) {
    return NextResponse.json({ raw: text }, { status: response.status });
  }
}
