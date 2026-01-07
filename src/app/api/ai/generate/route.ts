import { NextRequest, NextResponse } from 'next/server';
import { generateTopology } from '@/lib/ai/groq';

export async function POST(req: NextRequest) {
    try {
        const { prompt } = await req.json();

        if (!prompt) {
            return NextResponse.json({ error: "Prompt is required" }, { status: 400 });
        }

        const topology = await generateTopology(prompt);
        return NextResponse.json({ success: true, topology });
    } catch (error: any) {
        console.error("AI Generation Error", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}
