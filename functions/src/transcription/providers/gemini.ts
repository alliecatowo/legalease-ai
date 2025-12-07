/**
 * Gemini Transcription Provider
 *
 * Uses Gemini 2.5 Flash for audio transcription with:
 * - Speaker diarization via prompt engineering
 * - Structured JSON output with timestamps
 * - Support for both GCS URIs and direct URLs
 * - Files API for large files (>20MB)
 */

import type { TranscriptionProvider, ProviderCapabilities } from '../provider.js'
import type { TranscriptionRequest, TranscriptionResult, Segment, Speaker } from '../types.js'
import { applyDefaults } from '../types.js'
import config from '../../config.js'
import { getMetadata, download } from '../../storage/index.js'

// Lazy-loaded SDK client with Promise-based initialization to prevent race conditions
let clientPromise: Promise<any> | null = null

async function getClient() {
  if (!clientPromise) {
    clientPromise = (async () => {
      const { GoogleGenAI } = await import('@google/genai')
      return new GoogleGenAI({
        apiKey: process.env.GOOGLE_GENAI_API_KEY
      })
    })()
  }
  return clientPromise
}

/**
 * JSON schema for structured transcription output
 * Uses Gemini's native structured output for reliable parsing
 */
const TRANSCRIPTION_SCHEMA = {
  type: 'object',
  properties: {
    segments: {
      type: 'array',
      description: 'Timestamped transcript segments with speaker identification',
      items: {
        type: 'object',
        properties: {
          speaker: {
            type: 'string',
            description: 'Speaker identifier (e.g., "Speaker 1", "Speaker 2")'
          },
          startTime: {
            type: 'string',
            description: 'Start timestamp in MM:SS or HH:MM:SS format'
          },
          endTime: {
            type: 'string',
            description: 'End timestamp in MM:SS or HH:MM:SS format'
          },
          text: {
            type: 'string',
            description: 'Transcribed text for this segment'
          }
        },
        required: ['speaker', 'startTime', 'endTime', 'text']
      }
    },
    speakers: {
      type: 'array',
      description: 'List of identified speakers',
      items: {
        type: 'object',
        properties: {
          id: {
            type: 'string',
            description: 'Speaker identifier (e.g., "Speaker 1")'
          },
          name: {
            type: 'string',
            description: 'Inferred name if mentioned in audio'
          }
        },
        required: ['id']
      }
    },
    language: {
      type: 'string',
      description: 'Detected primary language (BCP-47 code, e.g., "en-US")'
    },
    duration: {
      type: 'number',
      description: 'Total audio duration in seconds'
    }
  },
  required: ['segments', 'speakers']
}

/**
 * Parse timestamp string (MM:SS or HH:MM:SS) to seconds
 */
function parseTimestamp(timestamp: string): number {
  if (!timestamp) return 0

  // Handle decimal seconds in timestamps like "1:23.456"
  const parts = timestamp.split(':')

  if (parts.length === 2) {
    // MM:SS or M:SS.mmm
    const mins = parseInt(parts[0], 10) || 0
    const secs = parseFloat(parts[1]) || 0
    return mins * 60 + secs
  } else if (parts.length === 3) {
    // HH:MM:SS or H:MM:SS.mmm
    const hours = parseInt(parts[0], 10) || 0
    const mins = parseInt(parts[1], 10) || 0
    const secs = parseFloat(parts[2]) || 0
    return hours * 3600 + mins * 60 + secs
  }

  // Try parsing as plain seconds
  return parseFloat(timestamp) || 0
}

/**
 * Build the transcription prompt
 */
function buildPrompt(opts: ReturnType<typeof applyDefaults>): string {
  const languageInstruction = opts.language === 'auto'
    ? 'Detect the language automatically and report it in the language field using BCP-47 format (e.g., "en-US").'
    : `The audio is in ${opts.language}.`

  const diarizationInstruction = opts.enableDiarization
    ? `Identify distinct speakers (up to ${opts.maxSpeakers} speakers). Label them as "Speaker 1", "Speaker 2", etc. If a speaker's name is mentioned in the audio, include it in the speakers array.`
    : 'Do not perform speaker diarization. Use "Speaker 1" for all segments.'

  return `
Transcribe this audio file completely and accurately.

Requirements:
1. ${diarizationInstruction}
2. Provide precise timestamps for each segment in MM:SS format (or HH:MM:SS for longer audio).
3. ${languageInstruction}
4. Include ALL spoken content - do not summarize or skip any sections.
5. Preserve filler words, false starts, and natural speech patterns for accuracy.
6. Create a new segment when the speaker changes or after natural pauses/sentence boundaries.
7. For legal depositions or interviews, accuracy is critical - transcribe exactly what is said.

Output the transcription as structured JSON with segments, speakers, language, and duration.
`.trim()
}

/**
 * MIME type mapping by file extension
 */
const MIME_TYPES: Record<string, string> = {
  // Audio formats
  '.mp3': 'audio/mp3',
  '.wav': 'audio/wav',
  '.flac': 'audio/flac',
  '.ogg': 'audio/ogg',
  '.aac': 'audio/aac',
  '.m4a': 'audio/mp4',
  '.wma': 'audio/x-ms-wma',
  '.opus': 'audio/opus',
  // Video formats
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.mov': 'video/quicktime',
  '.avi': 'video/x-msvideo',
  '.mkv': 'video/x-matroska',
  '.wmv': 'video/x-ms-wmv',
  '.flv': 'video/x-flv',
  '.3gp': 'video/3gpp'
}

/**
 * Infer MIME type from URL or filename
 */
function inferMimeType(url: string): string {
  const lower = url.toLowerCase()

  // YouTube URLs
  if (lower.includes('youtube.com') || lower.includes('youtu.be')) {
    return 'video/mp4'
  }

  // Look up by extension
  const ext = Object.keys(MIME_TYPES).find(e => lower.endsWith(e))
  return ext ? MIME_TYPES[ext] : 'audio/mpeg'
}

export class GeminiProvider implements TranscriptionProvider {
  readonly name = 'gemini'
  readonly displayName = 'Google Gemini 2.5 Flash'

  readonly capabilities: ProviderCapabilities = {
    diarization: true,           // Via prompt engineering
    streaming: false,            // Batch only
    languageDetection: true,     // Gemini detects language
    languageCount: 100,          // Supports many languages
    directUrlInput: true,        // Can use HTTPS URLs directly
    maxDurationSeconds: 34200,   // 9.5 hours (Gemini limit)
    multimodal: true,            // Gemini is multimodal
    requiresProduction: {
      storage: false             // We download file ourselves, emulator works fine
    }
  }

  canHandle(request: TranscriptionRequest): boolean {
    // Gemini supports gs://, https://, and http:// URLs
    const uri = request.mediaUri
    return (
      uri.startsWith('gs://') ||
      uri.startsWith('https://') ||
      uri.startsWith('http://')
    )
  }

  async transcribe(request: TranscriptionRequest): Promise<TranscriptionResult> {
    const startTime = Date.now()
    const logTime = (msg: string) => console.log(`[Gemini] [${Date.now() - startTime}ms] ${msg}`)
    const opts = applyDefaults(request)

    logTime('Starting transcription...')

    const ai = await getClient()
    const prompt = buildPrompt(opts)

    // Determine how to provide the audio to Gemini
    let audioPart: any

    if (opts.mediaUri.startsWith('gs://')) {
      // For GCS files, check size and use appropriate method
      logTime('Checking GCS file size...')
      const metadata = await getMetadata(opts.mediaUri)
      const fileSizeMB = Math.round(metadata.size / 1024 / 1024)

      if (metadata.size > config.transcription.fileSizeThresholdBytes) {
        // Large file: download and upload via Files API
        logTime(`Large file (${fileSizeMB}MB), using Files API...`)
        audioPart = await this.uploadViaFilesAPI(ai, opts.mediaUri, metadata.contentType, logTime)
      } else {
        // Small file: use inline data
        logTime(`Small file (${fileSizeMB}MB), using inline data...`)
        const buffer = await download(opts.mediaUri)
        audioPart = {
          inlineData: {
            data: buffer.toString('base64'),
            mimeType: metadata.contentType || inferMimeType(opts.mediaUri)
          }
        }
      }
    } else {
      // For HTTP/HTTPS URLs, Gemini can fetch them directly
      // However, the SDK might not support this directly, so we may need to download
      logTime('Downloading from URL...')
      try {
        const response = await fetch(opts.mediaUri)
        if (!response.ok) {
          throw new Error(`Failed to fetch URL: ${response.status} ${response.statusText}`)
        }
        const buffer = Buffer.from(await response.arrayBuffer())
        const contentType = response.headers.get('content-type') || inferMimeType(opts.mediaUri)

        if (buffer.length > config.transcription.fileSizeThresholdBytes) {
          logTime(`Large URL file (${Math.round(buffer.length / 1024 / 1024)}MB), using Files API...`)
          audioPart = await this.uploadBufferViaFilesAPI(ai, buffer, contentType, logTime)
        } else {
          audioPart = {
            inlineData: {
              data: buffer.toString('base64'),
              mimeType: contentType
            }
          }
        }
      } catch (error: any) {
        const message = error?.message || String(error)
        throw new Error(`Failed to fetch audio from URL '${opts.mediaUri}': ${message}`)
      }
    }

    logTime('Calling Gemini generateContent...')

    const response = await ai.models.generateContent({
      model: config.transcription.geminiModel,
      contents: [
        {
          role: 'user',
          parts: [audioPart, { text: prompt }]
        }
      ],
      config: {
        responseMimeType: 'application/json',
        responseSchema: TRANSCRIPTION_SCHEMA
      }
    })

    logTime('Parsing response...')

    // Parse the structured JSON response
    let result: any
    try {
      const responseText = response.text
      result = JSON.parse(responseText)
    } catch (parseError) {
      console.error('[Gemini] Failed to parse response:', response.text)
      throw new Error(`Failed to parse Gemini transcription response: ${parseError}`)
    }

    // Convert to standard TranscriptionResult format
    const segments: Segment[] = (result.segments || []).map((seg: any, index: number) => ({
      id: `seg-${index}`,
      startTime: parseTimestamp(seg.startTime),
      endTime: parseTimestamp(seg.endTime),
      text: seg.text?.trim() || '',
      speakerId: seg.speaker,
      confidence: undefined // Gemini doesn't provide per-segment confidence
    }))

    const speakers: Speaker[] = (result.speakers || []).map((spk: any) => ({
      id: spk.id,
      name: spk.name
    }))

    // Build full text from segments
    const fullText = segments.map(s => s.text).filter(Boolean).join(' ')

    // Calculate duration from last segment if not provided
    const duration = result.duration ||
      (segments.length > 0 ? segments[segments.length - 1].endTime : undefined)

    const processingTimeMs = Date.now() - startTime
    logTime(`Transcription complete: ${segments.length} segments, ${speakers.length} speakers in ${processingTimeMs}ms`)

    return {
      text: fullText,
      segments,
      speakers,
      duration,
      language: result.language,
      provider: this.name,
      processingTimeMs
    }
  }

  /**
   * Upload large files via Gemini Files API (from GCS URI)
   */
  private async uploadViaFilesAPI(
    ai: any,
    gcsUri: string,
    mimeType: string,
    logTime: (msg: string) => void
  ): Promise<any> {
    logTime('Downloading from GCS...')
    const buffer = await download(gcsUri)
    return this.uploadBufferViaFilesAPI(ai, buffer, mimeType, logTime)
  }

  /**
   * Upload a buffer via Gemini Files API
   */
  private async uploadBufferViaFilesAPI(
    ai: any,
    buffer: Buffer,
    mimeType: string,
    logTime: (msg: string) => void
  ): Promise<any> {
    logTime('Uploading to Gemini Files API...')

    // Create a Blob-like object for the SDK
    const blob = new Blob([buffer], { type: mimeType })

    // Upload to Gemini Files API
    const uploadResult = await ai.files.upload({
      file: blob,
      config: { mimeType }
    })

    const fileName = uploadResult.name

    // Wait for file processing
    logTime('Waiting for file processing...')
    let file = await ai.files.get({ name: fileName })

    while (file.state === 'PROCESSING') {
      logTime('File still processing...')
      await new Promise(resolve => setTimeout(resolve, 2000))
      file = await ai.files.get({ name: fileName })
    }

    if (file.state === 'FAILED') {
      throw new Error(`Gemini file processing failed: ${file.error?.message || 'Unknown error'}`)
    }

    logTime('File ready')

    // Return part reference for use in generateContent
    return {
      fileData: {
        fileUri: file.uri,
        mimeType: file.mimeType
      }
    }
  }
}
