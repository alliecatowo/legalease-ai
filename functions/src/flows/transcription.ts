import { z } from 'genkit'
import { googleAI } from '@genkit-ai/google-genai'
import { ai } from '../genkit.js'

// Input schema
export const TranscriptionInput = z.object({
  gcsUri: z.string().optional().describe('GCS URI of the audio/video file (gs://bucket/path)'),
  url: z.string().optional().describe('URL to transcribe (direct media URL)'),
  language: z.string().default('auto').describe('BCP-47 language code or "auto" for detection'),
  enableDiarization: z.boolean().default(true).describe('Enable speaker diarization'),
  enableSummary: z.boolean().default(false).describe('Generate summary with transcription'),
  maxSpeakers: z.number().default(6).describe('Maximum number of speakers to identify')
}).refine(data => data.gcsUri || data.url, {
  message: 'Either gcsUri or url must be provided'
})

export type TranscriptionInputType = z.infer<typeof TranscriptionInput>

// Segment schema
const TranscriptSegment = z.object({
  id: z.string().describe('Unique segment identifier'),
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
    // Apply defaults since Genkit may not apply Zod defaults
    const gcsUri = input.gcsUri
    const url = input.url
    const language = input.language
    const enableDiarization = input.enableDiarization ?? true  // Default: true
    const enableSummary = input.enableSummary ?? false         // Default: false
    const maxSpeakers = input.maxSpeakers ?? 6                 // Default: 6

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

    // Chirp 3 is available in 'us' multi-region (NOT 'global')
    // See: https://cloud.google.com/speech-to-text/v2/docs/chirp_3-model
    const location = 'us'

    // Create Speech-to-Text V2 client with regional endpoint
    const client = new SpeechClient({
      apiEndpoint: `${location}-speech.googleapis.com`
    })

    // Get project ID from environment or default
    const projectId = process.env.GCLOUD_PROJECT || process.env.GOOGLE_CLOUD_PROJECT || 'legalease-420'

    // Build the recognizer path - use "_" for default recognizer
    const recognizer = `projects/${projectId}/locations/${location}/recognizers/_`

    // Configure the recognition request for V2 API with Chirp 3
    // Note: Chirp 3 is available in 'us' multi-region
    // The V2 BatchRecognize API doesn't support "auto" as a language code
    // Default to en-US when auto is specified or language is not provided
    // (Zod defaults may not be applied by Genkit, so we handle undefined too)
    const effectiveLanguage = (!language || language === 'auto') ? 'en-US' : language

    const config: any = {
      autoDecodingConfig: {}, // Let the API auto-detect audio encoding
      languageCodes: [effectiveLanguage], // BCP-47 code (e.g., "en-US", "es-ES")
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

    // Call BatchRecognize - this returns a long-running operation
    const [operation] = await client.batchRecognize(request)

    // Wait for the operation to complete
    const [response] = await operation.promise()

    // Process results from V2 API response
    const segments: z.infer<typeof TranscriptSegment>[] = []
    const speakerSet = new Set<string>()
    let fullText = ''
    let lastEndTime = 0
    let segmentIndex = 0
    let detectedLanguage: string | undefined

    // V2 API returns results in a different structure
    // Results are keyed by the input file URI
    const results = response.results || {}

    for (const [fileUri, fileResult] of Object.entries(results)) {
      const transcript = (fileResult as any).transcript
      if (!transcript?.results) continue

      for (const result of transcript.results) {
        if (!result.alternatives || result.alternatives.length === 0) continue

        // Extract detected language from the result (set by auto-detection)
        if (result.languageCode && !detectedLanguage) {
          detectedLanguage = result.languageCode
        }

        const alternative = result.alternatives[0]
        const words = alternative.words || []

        // If we have words with speaker labels, create segments by speaker changes
        if (words.length > 0 && words[0]?.speakerLabel) {
          let currentSpeaker = words[0].speakerLabel
          let segmentWords: typeof words = []
          let segmentStartTime = parseDuration(words[0].startOffset)

          for (let i = 0; i < words.length; i++) {
            const word = words[i]
            const wordSpeaker = word.speakerLabel || currentSpeaker

            if (wordSpeaker !== currentSpeaker && segmentWords.length > 0) {
              // Speaker changed - save current segment
              const segmentText = segmentWords.map((w: any) => w.word).join(' ')
              const segmentEndTime = parseDuration(segmentWords[segmentWords.length - 1].endOffset)

              if (segmentText.trim()) {
                segments.push({
                  id: `seg-${segmentIndex++}`,
                  start: Math.max(0, segmentStartTime),
                  end: segmentEndTime,
                  text: segmentText.trim(),
                  speaker: currentSpeaker,
                  confidence: alternative.confidence || undefined
                })
                speakerSet.add(currentSpeaker)
                fullText += segmentText + ' '

                if (segmentEndTime > lastEndTime) {
                  lastEndTime = segmentEndTime
                }
              }

              // Start new segment
              currentSpeaker = wordSpeaker
              segmentWords = [word]
              segmentStartTime = parseDuration(word.startOffset)
            } else {
              segmentWords.push(word)
            }
          }

          // Don't forget the last segment
          if (segmentWords.length > 0) {
            const segmentText = segmentWords.map((w: any) => w.word).join(' ')
            const segmentEndTime = parseDuration(segmentWords[segmentWords.length - 1].endOffset)

            if (segmentText.trim()) {
              segments.push({
                id: `seg-${segmentIndex++}`,
                start: Math.max(0, segmentStartTime),
                end: segmentEndTime,
                text: segmentText.trim(),
                speaker: currentSpeaker,
                confidence: alternative.confidence || undefined
              })
              speakerSet.add(currentSpeaker)
              fullText += segmentText + ' '

              if (segmentEndTime > lastEndTime) {
                lastEndTime = segmentEndTime
              }
            }
          }
        } else {
          // No word-level data or no speaker labels - fall back to result-level
          const transcriptText = alternative.transcript || ''
          fullText += transcriptText + ' '

          const startTime = parseDuration(result.resultEndOffset) - (transcriptText.length * 0.05)
          const endTime = parseDuration(result.resultEndOffset)

          if (endTime > lastEndTime) {
            lastEndTime = endTime
          }

          if (transcriptText.trim()) {
            segments.push({
              id: `seg-${segmentIndex++}`,
              start: Math.max(0, startTime),
              end: endTime,
              text: transcriptText.trim(),
              speaker: undefined,
              confidence: alternative.confidence || undefined
            })
          }
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

    // Use detected language if auto-detection was used, otherwise use input language
    const outputLanguage = detectedLanguage || (language !== 'auto' ? language : undefined)
    console.log('Detected language:', detectedLanguage, 'Output language:', outputLanguage)

    let result: TranscriptionOutputType = {
      fullText,
      segments,
      speakers,
      duration,
      language: outputLanguage
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
