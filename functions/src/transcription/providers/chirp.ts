/**
 * Google Cloud Speech-to-Text V2 with Chirp 3 provider
 *
 * Chirp 3 provides:
 * - High accuracy transcription (100+ languages)
 * - Speaker diarization (timestamps come from diarization, not enableWordTimeOffsets)
 * - Automatic punctuation
 *
 * Requires: GCS URI (gs://bucket/path) - doesn't support direct URLs
 */

import type { TranscriptionProvider, ProviderCapabilities } from '../provider.js'
import type { TranscriptionRequest, TranscriptionResult, Segment, Speaker } from '../types.js'
import { applyDefaults } from '../types.js'
import appConfig from '../../config.js'

// Helper to convert duration to seconds
// Handles both string format ("10.500s") and object format ({seconds: "10", nanos: 500000000})
function parseDuration(duration: any): number {
  if (!duration) return 0

  // String format: "10.500s"
  if (typeof duration === 'string') {
    return parseFloat(duration.replace('s', '')) || 0
  }

  // Object format: {seconds: "10", nanos: 500000000}
  if (typeof duration === 'object') {
    const secs = parseInt(duration.seconds || '0', 10)
    const nanos = parseInt(duration.nanos || '0', 10)
    return secs + (nanos / 1_000_000_000)
  }

  return 0
}

export class ChirpProvider implements TranscriptionProvider {
  readonly name = 'chirp'
  readonly displayName = 'Google Chirp 3'

  readonly capabilities: ProviderCapabilities = {
    diarization: true,           // Chirp 3 supports speaker diarization
    streaming: false,            // BatchRecognize only, no streaming
    languageDetection: true,     // Can detect language automatically
    languageCount: 100,          // 100+ languages supported
    directUrlInput: false,       // Requires GCS URI (gs://)
    maxDurationSeconds: 28800,   // 8 hours max for batch
    multimodal: false            // Audio only, no video context
  }

  canHandle(request: TranscriptionRequest): boolean {
    // Chirp only supports GCS URIs for long audio
    return request.mediaUri.startsWith('gs://')
  }

  async transcribe(request: TranscriptionRequest): Promise<TranscriptionResult> {
    const startTime = Date.now()
    const logTime = (msg: string) => console.log(`[Chirp] [${Date.now() - startTime}ms] ${msg}`)
    const opts = applyDefaults(request)

    // Validate GCS URI requirement
    if (!opts.mediaUri.startsWith('gs://')) {
      throw new Error('Chirp provider only supports GCS URIs (gs://bucket/path). Upload the file to Firebase Storage first.')
    }

    logTime('Importing Speech V2 client...')
    // Import Speech V2 client dynamically
    const { SpeechClient } = await import('@google-cloud/speech').then(m => m.v2)
    logTime('Speech V2 client imported')

    // Chirp 3 is available in 'us' multi-region
    const location = 'us'

    logTime('Creating SpeechClient...')
    // Create Speech-to-Text V2 client with regional endpoint
    const client = new SpeechClient({
      apiEndpoint: `${location}-speech.googleapis.com`
    })
    logTime('SpeechClient created')

    // Get project ID from config
    const projectId = appConfig.projectId

    // Build the recognizer path - use "_" for default recognizer
    const recognizer = `projects/${projectId}/locations/${location}/recognizers/_`

    // V2 BatchRecognize API doesn't support "auto" - default to en-US
    const effectiveLanguage = opts.language === 'auto' ? 'en-US' : opts.language

    // Build recognition config
    const config: any = {
      autoDecodingConfig: {},
      languageCodes: [effectiveLanguage],
      model: 'chirp_3',
      features: {
        enableAutomaticPunctuation: true,
        enableWordTimeOffsets: true // Provides timestamps for words (used with diarization)
      }
    }

    // Add speaker diarization if enabled (this is what provides segment timestamps)
    if (opts.enableDiarization) {
      config.features.diarizationConfig = {
        minSpeakerCount: 1,
        maxSpeakerCount: opts.maxSpeakers
      }
    }

    // Build the batch recognition request
    const batchRequest = {
      recognizer,
      config,
      files: [{ uri: opts.mediaUri }],
      recognitionOutputConfig: {
        inlineResponseConfig: {}
      }
    }

    logTime('Calling batchRecognize...')
    // Call BatchRecognize and wait for completion
    const [operation] = await client.batchRecognize(batchRequest)
    logTime('batchRecognize returned, waiting for operation to complete...')
    const [response] = await operation.promise()
    logTime('Operation completed')

    // Process results
    const segments: Segment[] = []
    const speakerSet = new Set<string>()
    let fullText = ''
    let lastEndTime = 0
    let segmentIndex = 0
    let detectedLanguage: string | undefined

    const results = response.results || {}

    for (const [, fileResult] of Object.entries(results)) {
      const transcript = (fileResult as any).transcript
      if (!transcript?.results) continue

      for (const result of transcript.results) {
        if (!result.alternatives || result.alternatives.length === 0) continue

        // Capture detected language
        if (result.languageCode && !detectedLanguage) {
          detectedLanguage = result.languageCode
        }

        const alternative = result.alternatives[0]
        const words = alternative.words || []

        // If we have words with speaker labels, group by speaker
        if (words.length > 0 && words[0]?.speakerLabel) {
          let currentSpeaker = words[0].speakerLabel
          const speakerSegments: { speaker: string; words: typeof words }[] = []
          let currentSegment = { speaker: currentSpeaker, words: [] as typeof words }

          for (const word of words) {
            const wordSpeaker = word.speakerLabel || currentSpeaker

            if (wordSpeaker !== currentSpeaker && currentSegment.words.length > 0) {
              speakerSegments.push(currentSegment)
              currentSegment = { speaker: wordSpeaker, words: [word] }
              currentSpeaker = wordSpeaker
            } else {
              currentSegment.words.push(word)
            }
          }
          if (currentSegment.words.length > 0) {
            speakerSegments.push(currentSegment)
          }

          // Create segments with timestamps from word offsets
          for (const seg of speakerSegments) {
            const segmentText = seg.words.map((w: any) => w.word).join(' ')
            if (!segmentText.trim()) continue

            const segStart = parseDuration(seg.words[0].startOffset)
            const segEnd = parseDuration(seg.words[seg.words.length - 1].endOffset)

            segments.push({
              id: `seg-${segmentIndex++}`,
              startTime: segStart,
              endTime: segEnd,
              text: segmentText.trim(),
              speakerId: seg.speaker,
              confidence: alternative.confidence || undefined
            })
            speakerSet.add(seg.speaker)
            fullText += segmentText + ' '

            if (segEnd > lastEndTime) {
              lastEndTime = segEnd
            }
          }
        } else {
          // Fallback: no diarization data
          const transcriptText = alternative.transcript || ''
          fullText += transcriptText + ' '

          const startTimeVal = parseDuration(result.resultEndOffset) - (transcriptText.length * 0.05)
          const endTimeVal = parseDuration(result.resultEndOffset)

          if (endTimeVal > lastEndTime) {
            lastEndTime = endTimeVal
          }

          if (transcriptText.trim()) {
            segments.push({
              id: `seg-${segmentIndex++}`,
              startTime: Math.max(0, startTimeVal),
              endTime: endTimeVal,
              text: transcriptText.trim(),
              speakerId: undefined,
              confidence: alternative.confidence || undefined
            })
          }
        }
      }
    }

    // Build speakers list
    const speakers: Speaker[] = Array.from(speakerSet)
      .sort()
      .map(tag => ({ id: tag }))

    const processingTimeMs = Date.now() - startTime
    console.log(`[Chirp] Transcription complete: ${segments.length} segments, ${speakers.length} speakers in ${processingTimeMs}ms`)

    return {
      text: fullText.trim(),
      segments,
      speakers,
      duration: lastEndTime > 0 ? lastEndTime : undefined,
      language: detectedLanguage || (opts.language !== 'auto' ? opts.language : undefined),
      provider: this.name,
      processingTimeMs
    }
  }
}
