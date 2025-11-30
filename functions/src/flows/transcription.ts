import { z } from 'genkit'
import { googleAI } from '@genkit-ai/google-genai'
import { ai } from '../genkit.js'
import speech from '@google-cloud/speech'

// Input schema
export const TranscriptionInput = z.object({
  gcsUri: z.string().optional().describe('GCS URI of the audio/video file (gs://bucket/path)'),
  url: z.string().optional().describe('URL to transcribe (direct media URL)'),
  language: z.string().default('en-US').describe('Language code'),
  enableDiarization: z.boolean().default(true).describe('Enable speaker diarization'),
  enableSummary: z.boolean().default(false).describe('Generate summary with transcription'),
  maxSpeakers: z.number().default(6).describe('Maximum number of speakers to identify')
}).refine(data => data.gcsUri || data.url, {
  message: 'Either gcsUri or url must be provided'
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

// Helper to detect encoding from URL/file extension
function getEncodingFromUri(uri: string): string {
  const ext = uri.split('.').pop()?.toLowerCase()
  const encodings: Record<string, string> = {
    'mp3': 'MP3',
    'wav': 'LINEAR16',
    'flac': 'FLAC',
    'ogg': 'OGG_OPUS',
    'webm': 'WEBM_OPUS',
    'm4a': 'MP3', // AAC in M4A container - Speech API handles it
    'mp4': 'MP3'  // Audio track extraction
  }
  return encodings[ext || ''] || 'ENCODING_UNSPECIFIED'
}

// Transcription flow using Google Cloud Speech-to-Text
export const transcribeMediaFlow = ai.defineFlow(
  {
    name: 'transcribeMedia',
    inputSchema: TranscriptionInput,
    outputSchema: TranscriptionOutput
  },
  async (input) => {
    const { gcsUri, url, language, enableDiarization, enableSummary, maxSpeakers } = input

    // Determine the media URI - prefer GCS URI for direct access
    const mediaUri = gcsUri || url
    if (!mediaUri) {
      throw new Error('Either gcsUri or url must be provided')
    }

    // Only GCS URIs are supported for long audio files
    if (!mediaUri.startsWith('gs://')) {
      throw new Error('Only GCS URIs (gs://bucket/path) are supported for transcription. Upload the file to Firebase Storage first.')
    }

    // Create Speech-to-Text client
    const client = new speech.SpeechClient()

    // Configure the recognition request
    const config: speech.protos.google.cloud.speech.v1.IRecognitionConfig = {
      encoding: getEncodingFromUri(mediaUri) as any,
      languageCode: language,
      enableAutomaticPunctuation: true,
      enableWordTimeOffsets: true,
      model: 'latest_long', // Best for long-form audio like recordings
      useEnhanced: true,    // Enhanced model for better accuracy
    }

    // Add diarization config if enabled
    if (enableDiarization) {
      config.diarizationConfig = {
        enableSpeakerDiarization: true,
        minSpeakerCount: 1,
        maxSpeakerCount: maxSpeakers
      }
    }

    const audio: speech.protos.google.cloud.speech.v1.IRecognitionAudio = {
      uri: mediaUri
    }

    console.log('Starting long-running transcription for:', mediaUri)

    // Use long-running recognize for audio files (required for >1 minute)
    const [operation] = await client.longRunningRecognize({ config, audio })

    console.log('Transcription operation started, waiting for completion...')

    // Wait for the operation to complete (can take several minutes for long audio)
    const [response] = await operation.promise()

    if (!response.results || response.results.length === 0) {
      throw new Error('No transcription results returned')
    }

    // Process results into our format
    const segments: z.infer<typeof TranscriptSegment>[] = []
    const speakerSet = new Set<number>()
    let fullText = ''

    for (const result of response.results) {
      if (!result.alternatives || result.alternatives.length === 0) continue

      const alternative = result.alternatives[0]
      fullText += (alternative.transcript || '') + ' '

      // Process word-level timing and speaker info
      if (alternative.words) {
        let currentSegment: {
          start: number
          end: number
          text: string
          speaker?: string
          confidence?: number
        } | null = null

        for (const wordInfo of alternative.words) {
          const startTime = Number(wordInfo.startTime?.seconds || 0) +
            Number(wordInfo.startTime?.nanos || 0) / 1e9
          const endTime = Number(wordInfo.endTime?.seconds || 0) +
            Number(wordInfo.endTime?.nanos || 0) / 1e9
          const speakerTag = wordInfo.speakerTag || 0

          if (speakerTag > 0) {
            speakerSet.add(speakerTag)
          }

          const speaker = speakerTag > 0 ? `Speaker${speakerTag}` : undefined

          // Group words into segments by speaker
          if (!currentSegment || currentSegment.speaker !== speaker) {
            // Save previous segment
            if (currentSegment && currentSegment.text.trim()) {
              segments.push({
                start: currentSegment.start,
                end: currentSegment.end,
                text: currentSegment.text.trim(),
                speaker: currentSegment.speaker,
                confidence: currentSegment.confidence
              })
            }
            // Start new segment
            currentSegment = {
              start: startTime,
              end: endTime,
              text: wordInfo.word || '',
              speaker,
              confidence: alternative.confidence || undefined
            }
          } else {
            // Continue current segment
            currentSegment.end = endTime
            currentSegment.text += ' ' + (wordInfo.word || '')
          }
        }

        // Don't forget the last segment
        if (currentSegment && currentSegment.text.trim()) {
          segments.push({
            start: currentSegment.start,
            end: currentSegment.end,
            text: currentSegment.text.trim(),
            speaker: currentSegment.speaker,
            confidence: currentSegment.confidence
          })
        }
      }
    }

    fullText = fullText.trim()

    // Build speakers list
    const speakers: z.infer<typeof Speaker>[] = Array.from(speakerSet)
      .sort((a, b) => a - b)
      .map(tag => ({
        id: `Speaker${tag}`,
        inferredName: undefined
      }))

    // Calculate duration from last segment
    const duration = segments.length > 0
      ? segments[segments.length - 1].end
      : undefined

    let result: TranscriptionOutputType = {
      fullText,
      segments,
      speakers,
      duration,
      language
    }

    // Generate summary if requested (use Gemini 2.5 Flash for this)
    if (enableSummary && fullText.length > 100) {
      try {
        const summaryResponse = await ai.generate({
          model: googleAI.model('gemini-2.5-flash'),
          prompt: `Provide a brief 2-3 sentence summary of this transcript:\n\n${fullText.substring(0, 10000)}`
        })
        result.summary = summaryResponse.text
      } catch (error) {
        console.warn('Summary generation failed:', error)
      }
    }

    console.log(`Transcription complete: ${segments.length} segments, ${speakers.length} speakers`)

    return result
  }
)
