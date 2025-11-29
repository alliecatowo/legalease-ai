import { z } from 'genkit'
import { googleAI } from '@genkit-ai/google-genai'
import { ai } from '../genkit.js'

// Input schema
export const TranscriptionInput = z.object({
  gcsUri: z.string().describe('GCS URI of the audio/video file (gs://bucket/path)'),
  language: z.string().default('en').describe('Language code'),
  enableDiarization: z.boolean().default(true).describe('Enable speaker diarization'),
  enableSummary: z.boolean().default(false).describe('Generate summary with transcription')
})

export type TranscriptionInputType = z.infer<typeof TranscriptionInput>

// Segment schema
const TranscriptSegment = z.object({
  start: z.number().describe('Start time in seconds'),
  end: z.number().describe('End time in seconds'),
  text: z.string().describe('Transcribed text'),
  speaker: z.string().optional().describe('Speaker identifier'),
  confidence: z.number().optional().describe('Confidence score 0-1')
})

// Speaker schema
const Speaker = z.object({
  id: z.string().describe('Speaker identifier (e.g., Speaker1)'),
  inferredName: z.string().optional().describe('Inferred name from context')
})

// Output schema
export const TranscriptionOutput = z.object({
  fullText: z.string().describe('Complete transcript text'),
  segments: z.array(TranscriptSegment).describe('Timestamped segments'),
  speakers: z.array(Speaker).describe('Identified speakers'),
  duration: z.number().optional().describe('Total duration in seconds'),
  language: z.string().optional().describe('Detected language'),
  summary: z.string().optional().describe('Brief summary if requested')
})

export type TranscriptionOutputType = z.infer<typeof TranscriptionOutput>

// Transcription flow
export const transcribeMediaFlow = ai.defineFlow(
  {
    name: 'transcribeMedia',
    inputSchema: TranscriptionInput,
    outputSchema: TranscriptionOutput
  },
  async (input) => {
    const { gcsUri, language, enableDiarization, enableSummary } = input

    // Build the transcription prompt
    const transcriptionPrompt = `
You are a professional transcription service. Transcribe the audio/video file accurately.

Requirements:
- Transcribe all spoken content with timestamps
- ${enableDiarization ? 'Identify different speakers as Speaker1, Speaker2, etc.' : 'Do not identify speakers'}
- Include start and end times for each segment in seconds
- Maintain the original language: ${language}
- Be accurate with names, numbers, and technical terms
- Include filler words and false starts for legal accuracy

Return a JSON object with this exact structure:
{
  "fullText": "complete transcript as a single string",
  "segments": [
    { "start": 0.0, "end": 5.2, "text": "segment text", "speaker": "Speaker1" }
  ],
  "speakers": [
    { "id": "Speaker1", "inferredName": null }
  ],
  "duration": total_duration_in_seconds,
  "language": "${language}"
}
`

    // Call Gemini with multimodal input
    const response = await ai.generate({
      model: googleAI.model('gemini-2.5-flash'),
      prompt: [
        { text: transcriptionPrompt },
        {
          media: {
            url: gcsUri,
            contentType: 'audio/mpeg' // Gemini auto-detects the actual type
          }
        }
      ],
      output: { format: 'json', schema: TranscriptionOutput }
    })

    let result = response.output as TranscriptionOutputType

    // If diarization enabled, try to infer speaker names from context
    if (enableDiarization && result.speakers.length > 0) {
      const nameInferencePrompt = `
Based on this transcript, try to infer the real names of speakers from the conversation context.
Look for:
- Self-introductions ("Hi, I'm John")
- Names mentioned when addressing someone ("Thanks, Sarah")
- Role/title mentions ("The attorney stated...")

Transcript:
${result.fullText}

Current speakers: ${JSON.stringify(result.speakers)}

Return updated speakers array with inferredName filled in where confident:
`

      try {
        const nameResponse = await ai.generate({
          model: googleAI.model('gemini-2.5-flash'),
          prompt: nameInferencePrompt,
          output: {
            format: 'json',
            schema: z.object({
              speakers: z.array(Speaker)
            })
          }
        })

        if (nameResponse.output?.speakers) {
          result.speakers = nameResponse.output.speakers
        }
      } catch (error) {
        // Name inference is optional, continue with original speakers
        console.warn('Speaker name inference failed:', error)
      }
    }

    // Generate summary if requested
    if (enableSummary) {
      try {
        const summaryResponse = await ai.generate({
          model: googleAI.model('gemini-2.5-flash'),
          prompt: `Provide a brief 2-3 sentence summary of this transcript:\n\n${result.fullText}`
        })
        result.summary = summaryResponse.text
      } catch (error) {
        console.warn('Summary generation failed:', error)
      }
    }

    return result
  }
)
