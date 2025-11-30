import { z } from 'genkit'
import { googleAI } from '@genkit-ai/google-genai'
import { ai } from '../genkit.js'

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

// Helper to convert duration string (e.g., "10.500s") to seconds
function parseDuration(duration: string | null | undefined): number {
  if (!duration) return 0
  // Remove trailing 's' and parse as float
  return parseFloat(duration.replace('s', '')) || 0
}

// Transcription flow using Google Cloud Speech-to-Text V2 with Chirp 3
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

    // Import Speech V2 client dynamically
    const { SpeechClient } = await import('@google-cloud/speech').then(m => m.v2)

    // Create Speech-to-Text V2 client
    const client = new SpeechClient()

    // Get project ID from environment or default
    const projectId = process.env.GCLOUD_PROJECT || process.env.GOOGLE_CLOUD_PROJECT || 'legalease-420'

    // Chirp 3 requires 'global' location for BatchRecognize API
    // See: https://cloud.google.com/speech-to-text/v2/docs/chirp-model
    const location = 'global'

    // Build the recognizer path - use "_" for default recognizer
    const recognizer = `projects/${projectId}/locations/${location}/recognizers/_`

    console.log('Starting Chirp 3 transcription for:', mediaUri)
    console.log('Using recognizer:', recognizer)

    // Configure the recognition request for V2 API with Chirp 3
    // Note: Chirp 3 only supports utterance-level timestamps, not word-level
    const config: any = {
      autoDecodingConfig: {}, // Let the API auto-detect audio encoding
      languageCodes: [language],
      model: 'chirp_3', // Chirp 3 - latest model with best accuracy
      features: {
        enableAutomaticPunctuation: true,
        // Note: Word-level timestamps not supported in Chirp models
        // Diarization config is set separately below
      }
    }

    // Add speaker diarization if enabled
    // Note: Chirp 3 supports diarization in specific languages including en-US
    if (enableDiarization) {
      config.features.diarizationConfig = {
        minSpeakerCount: 1,
        maxSpeakerCount: maxSpeakers
      }
    }

    // Use BatchRecognize for long audio files (1 minute to 8 hours)
    const request = {
      recognizer,
      config,
      files: [{
        uri: mediaUri
      }],
      recognitionOutputConfig: {
        inlineResponseConfig: {} // Return results inline
      }
    }

    console.log('Starting batch recognition...')

    // Call BatchRecognize - this returns a long-running operation
    const [operation] = await client.batchRecognize(request)

    console.log('Batch recognition operation started, waiting for completion...')

    // Wait for the operation to complete
    const [response] = await operation.promise()

    console.log('Batch recognition complete, processing results...')

    // Process results from V2 API response
    const segments: z.infer<typeof TranscriptSegment>[] = []
    const speakerSet = new Set<string>()
    let fullText = ''
    let lastEndTime = 0

    // V2 API returns results in a different structure
    // Results are keyed by the input file URI
    const results = response.results || {}

    for (const [fileUri, fileResult] of Object.entries(results)) {
      const transcript = (fileResult as any).transcript
      if (!transcript?.results) continue

      for (const result of transcript.results) {
        if (!result.alternatives || result.alternatives.length === 0) continue

        const alternative = result.alternatives[0]
        const transcriptText = alternative.transcript || ''

        fullText += transcriptText + ' '

        // Get timing from result level (utterance-level timestamps)
        const startTime = parseDuration(result.resultEndOffset) - (transcriptText.length * 0.05) // Estimate start
        const endTime = parseDuration(result.resultEndOffset)

        if (endTime > lastEndTime) {
          lastEndTime = endTime
        }

        // Get speaker tag if diarization was enabled
        let speaker: string | undefined
        if (alternative.words && alternative.words.length > 0) {
          // In V2 API with diarization, speaker tag is on words
          const speakerTag = alternative.words[0]?.speakerLabel
          if (speakerTag) {
            speaker = speakerTag
            speakerSet.add(speakerTag)
          }
        }

        // Create segment for this utterance
        if (transcriptText.trim()) {
          segments.push({
            start: Math.max(0, startTime),
            end: endTime,
            text: transcriptText.trim(),
            speaker,
            confidence: alternative.confidence || undefined
          })
        }
      }
    }

    fullText = fullText.trim()

    // Build speakers list
    const speakers: z.infer<typeof Speaker>[] = Array.from(speakerSet)
      .sort()
      .map(tag => ({
        id: tag,
        inferredName: undefined
      }))

    // Duration from last segment end time
    const duration = lastEndTime > 0 ? lastEndTime : undefined

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
