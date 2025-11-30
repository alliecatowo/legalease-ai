/**
 * Transcription flow - Genkit wrapper around provider-agnostic transcription
 *
 * This flow:
 * 1. Receives transcription requests via Genkit callable
 * 2. Delegates to the transcription provider abstraction
 * 3. Optionally generates detailed summaries using configured AI model
 */

import { z } from 'genkit'
import { ai } from '../genkit.js'
import { getModel } from '../ai/index.js'
import { transcribe, getProvider, listProviders } from '../transcription/index.js'
import type { TranscriptionResult } from '../transcription/index.js'
import { SummarizationOutput, type SummarizationOutputType } from './summarization.js'

// Input schema (maintains backward compatibility with existing frontend)
export const TranscriptionInput = z.object({
  gcsUri: z.string().optional().describe('GCS URI of the audio/video file (gs://bucket/path)'),
  url: z.string().optional().describe('URL to transcribe (direct media URL)'),
  language: z.string().default('auto').describe('BCP-47 language code or "auto" for detection'),
  enableDiarization: z.boolean().default(true).describe('Enable speaker diarization'),
  enableSummary: z.boolean().default(false).describe('Generate summary with transcription'),
  maxSpeakers: z.number().default(6).describe('Maximum number of speakers to identify'),
  provider: z.string().optional().describe('Transcription provider to use (default: chirp)')
}).refine(data => data.gcsUri || data.url, {
  message: 'Either gcsUri or url must be provided'
})

export type TranscriptionInputType = z.infer<typeof TranscriptionInput>

// Output schema (maps to standard TranscriptionResult but with legacy field names)
const TranscriptSegment = z.object({
  id: z.string().describe('Unique segment identifier'),
  start: z.number().describe('Start time in seconds'),
  end: z.number().describe('End time in seconds'),
  text: z.string().describe('Transcribed text'),
  speaker: z.string().optional().describe('Speaker identifier'),
  confidence: z.number().optional().describe('Confidence score 0-1')
})

const Speaker = z.object({
  id: z.string().describe('Speaker identifier (e.g., Speaker1)'),
  inferredName: z.string().optional().describe('Inferred name from context')
})

export const TranscriptionOutput = z.object({
  fullText: z.string().describe('Complete transcript text'),
  segments: z.array(TranscriptSegment).describe('Timestamped segments'),
  speakers: z.array(Speaker).describe('Identified speakers'),
  duration: z.number().optional().describe('Total duration in seconds'),
  language: z.string().optional().describe('Detected language'),
  // Detailed summarization output (replaces brief summary)
  summarization: SummarizationOutput.optional().describe('Detailed AI summary if requested'),
  provider: z.string().optional().describe('Provider used for transcription')
})

export type TranscriptionOutputType = z.infer<typeof TranscriptionOutput>

/**
 * Convert standard TranscriptionResult to output format
 */
function toOutputFormat(result: TranscriptionResult, summarization?: SummarizationOutputType): TranscriptionOutputType {
  return {
    fullText: result.text,
    segments: result.segments.map(seg => ({
      id: seg.id,
      start: seg.startTime,
      end: seg.endTime,
      text: seg.text,
      speaker: seg.speakerId,
      confidence: seg.confidence
    })),
    speakers: result.speakers.map(spk => ({
      id: spk.id,
      inferredName: spk.name
    })),
    duration: result.duration,
    language: result.language,
    summarization,
    provider: result.provider
  }
}

// Main transcription flow
export const transcribeMediaFlow = ai.defineFlow(
  {
    name: 'transcribeMedia',
    inputSchema: TranscriptionInput,
    outputSchema: TranscriptionOutput
  },
  async (input) => {
    // Build provider-agnostic request
    const mediaUri = input.gcsUri || input.url
    if (!mediaUri) {
      throw new Error('Either gcsUri or url must be provided')
    }

    // Delegate to transcription abstraction
    const result = await transcribe(
      {
        mediaUri,
        language: input.language,
        enableDiarization: input.enableDiarization ?? true,
        maxSpeakers: input.maxSpeakers ?? 6,
        enableSummary: false // We handle summary separately with Gemini
      },
      input.provider
    )

    // Generate detailed summary if requested (uses 'standard' model for quality)
    let summarization: SummarizationOutputType | undefined
    if ((input.enableSummary ?? false) && result.text.length > 100) {
      try {
        console.log('Generating detailed summary...')
        const summaryResponse = await ai.generate({
          model: getModel('standard'),
          prompt: `
You are a legal document analyst. Analyze this transcript and provide a structured summary.

Transcript:
${result.text.substring(0, 30000)}

Provide your analysis as JSON with this structure:
{
  "summary": "1-2 paragraph executive summary of the transcript",
  "keyMoments": [
    {
      "timestamp": "optional timestamp or null",
      "description": "what happened",
      "importance": "high|medium|low",
      "speakers": ["who was involved"]
    }
  ],
  "actionItems": ["any follow-up actions mentioned or implied"],
  "topics": ["main topics discussed"],
  "entities": {
    "people": ["names mentioned"],
    "organizations": ["companies, firms, agencies"],
    "locations": ["places mentioned"],
    "dates": ["dates, times, deadlines mentioned"]
  }
}

Focus on:
- Admissions or contradictions
- Key facts and evidence discussed
- Legal issues or claims mentioned
- Dates and deadlines
- Agreements or disputes
`,
          output: { format: 'json', schema: SummarizationOutput }
        })
        summarization = summaryResponse.output as SummarizationOutputType
        console.log(`Summary generated: ${summarization.keyMoments?.length || 0} key moments, ${summarization.actionItems?.length || 0} action items`)
      } catch (error) {
        console.warn('Summary generation failed:', error)
      }
    }

    // Convert to output format
    const output = toOutputFormat(result, summarization)

    console.log(`Transcription complete: ${result.segments.length} segments, ${result.speakers.length} speakers (provider: ${result.provider})`)

    return output
  }
)

// Export helper to list available providers
export { listProviders, getProvider }
