import { onCallGenkit, isSignedIn } from 'firebase-functions/https'
import { onDocumentUpdated, onDocumentWritten } from 'firebase-functions/v2/firestore'
import { defineSecret } from 'firebase-functions/params'
import { getFirestore, FieldValue } from 'firebase-admin/firestore'
import { initializeApp, getApps } from 'firebase-admin/app'
import config from './config.js'

// Initialize Firebase Admin if not already initialized
if (getApps().length === 0) {
  initializeApp()
}

// Import flows
import { transcribeMediaFlow, TranscriptionInput } from './flows/transcription.js'
import { summarizeTranscriptFlow, SummarizationInput } from './flows/summarization.js'
import {
  searchDocumentsFlow,
  indexDocumentChunksFlow,
  deleteDocumentChunksFlow,
  SearchInput,
  IndexDocumentChunksInput,
  DeleteDocumentChunksInput
} from './flows/search.js'
import { generateWaveformFlow, WaveformInput } from './flows/waveform.js'
import { extractDocumentFlow, ExtractDocumentInput } from './flows/document-extraction.js'
import { transcribe } from './transcription/index.js'
import { download } from './storage/index.js'
import { ai } from './genkit.js'
import { getModel } from './ai/index.js'
import { SummarizationOutput } from './flows/summarization.js'
import { initializeProviders } from './providers/document/index.js'

// Initialize document extraction providers
initializeProviders()

// Generate waveform peaks from audio buffer (simplified approach)
function generateWaveformPeaks(buffer: Buffer, targetPeaks: number = 800): number[] {
  const peaks: number[] = []
  const bytesPerPeak = Math.max(1, Math.floor(buffer.length / targetPeaks))

  for (let i = 0; i < targetPeaks; i++) {
    const start = i * bytesPerPeak
    const end = Math.min(start + bytesPerPeak, buffer.length)
    let sum = 0, count = 0

    for (let j = start; j < end; j += 2) {
      if (j + 1 < buffer.length) {
        const sample = buffer.readInt16LE(j)
        sum += Math.abs(sample)
        count++
      }
    }

    const avgAmplitude = count > 0 ? sum / count / 32768 : 0
    peaks.push(Math.min(1, avgAmplitude))
  }

  // Normalize to use full range
  const max = Math.max(...peaks, 0.001)
  return peaks.map(p => p / max)
}

// Define secrets
const googleAIApiKey = defineSecret('GOOGLE_GENAI_API_KEY')
const qdrantUrl = defineSecret('QDRANT_URL')
const qdrantApiKey = defineSecret('QDRANT_API_KEY')

// Export flows as Firebase callable functions
export const transcribeMedia = onCallGenkit(
  {
    secrets: [googleAIApiKey],
    authPolicy: isSignedIn(),
    cors: true,
    memory: '1GiB',
    timeoutSeconds: 540 // 9 minutes for long transcriptions
  },
  transcribeMediaFlow
)

export const summarizeTranscript = onCallGenkit(
  {
    secrets: [googleAIApiKey],
    authPolicy: isSignedIn(),
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 120
  },
  summarizeTranscriptFlow
)

export const searchDocuments = onCallGenkit(
  {
    secrets: [googleAIApiKey, qdrantUrl, qdrantApiKey],
    authPolicy: isSignedIn(),
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 60
  },
  searchDocumentsFlow
)

export const indexDocumentChunks = onCallGenkit(
  {
    secrets: [googleAIApiKey, qdrantUrl, qdrantApiKey],
    authPolicy: isSignedIn(),
    cors: true,
    memory: '1GiB',
    timeoutSeconds: 300 // 5 minutes for large documents
  },
  indexDocumentChunksFlow
)

export const deleteDocumentChunks = onCallGenkit(
  {
    secrets: [qdrantUrl, qdrantApiKey],
    authPolicy: isSignedIn(),
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 60
  },
  deleteDocumentChunksFlow
)

export const extractDocument = onCallGenkit(
  {
    secrets: [googleAIApiKey, qdrantUrl, qdrantApiKey],
    authPolicy: isSignedIn(),
    cors: true,
    memory: '2GiB',
    timeoutSeconds: 540 // 9 minutes for large documents
  },
  extractDocumentFlow
)

export const generateWaveform = onCallGenkit(
  {
    authPolicy: isSignedIn(),
    cors: true,
    memory: '1GiB', // May need more memory for large audio files
    timeoutSeconds: 120
  },
  generateWaveformFlow
)

// Re-export schemas for client-side use
export {
  TranscriptionInput,
  SummarizationInput,
  SearchInput,
  IndexDocumentChunksInput,
  DeleteDocumentChunksInput,
  ExtractDocumentInput,
  WaveformInput
}

/**
 * Firestore trigger: Start transcription job
 *
 * When status is set to "processing" (on create or update):
 * 1. Calls the configured transcription provider (Gemini by default)
 * 2. Generates AI summary if transcript is long enough
 * 3. Generates waveform peaks for audio visualization
 * 4. Updates Firestore with results
 */
export const startTranscriptionJob = onDocumentWritten(
  {
    document: 'transcriptions/{transcriptionId}',
    secrets: [googleAIApiKey],
    memory: '2GiB',
    timeoutSeconds: 540, // 9 minutes for long transcriptions
    cpu: 2
  },
  async (event) => {
    const beforeData = event.data?.before?.data()
    const afterData = event.data?.after?.data()
    const transcriptionId = event.params.transcriptionId

    // Skip if document was deleted
    if (!afterData) {
      return
    }

    // Only process when status is "processing" and wasn't before
    // This handles both new documents and status updates
    if (afterData.status !== 'processing') {
      return
    }
    if (beforeData?.status === 'processing') {
      return // Already processing, don't restart
    }

    console.log(`[startTranscriptionJob] Starting transcription for ${transcriptionId}`)
    const startTime = Date.now()
    const logTime = (msg: string) => console.log(`[startTranscriptionJob] [${Date.now() - startTime}ms] ${msg}`)

    const db = getFirestore()
    const docRef = db.collection('transcriptions').doc(transcriptionId)

    try {
      // Update status to transcribing
      await docRef.update({
        status: 'transcribing',
        transcriptionStartedAt: FieldValue.serverTimestamp()
      })

      const mediaUri = afterData.gsUri || afterData.downloadUrl
      if (!mediaUri) {
        throw new Error('No media URI available for transcription')
      }

      logTime(`Transcribing: ${mediaUri}`)

      // Use the transcription provider abstraction (Gemini by default)
      const result = await transcribe({
        mediaUri,
        language: afterData.language || 'auto',
        enableDiarization: true,
        maxSpeakers: 6
      })

      logTime(`Transcription complete: ${result.segments.length} segments, ${result.speakers.length} speakers`)

      // Convert to Firestore format (legacy field names)
      const segments = result.segments.map(seg => ({
        id: seg.id,
        start: seg.startTime,
        end: seg.endTime,
        text: seg.text,
        speaker: seg.speakerId || null,
        confidence: seg.confidence || null
      }))

      const speakers = result.speakers.map(spk => ({
        id: spk.id,
        inferredName: spk.name || null
      }))

      // Generate summary if transcript is substantial
      let summarization = null
      if (result.text.length > 100) {
        try {
          logTime('Generating summary...')

          const timestampedTranscript = result.segments.slice(0, 500).map(seg => {
            const mins = Math.floor(seg.startTime / 60)
            const secs = Math.floor(seg.startTime % 60)
            const timestamp = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
            const speaker = seg.speakerId || 'Unknown'
            return `[${timestamp}] ${speaker}: ${seg.text}`
          }).join('\n')

          const summaryResponse = await ai.generate({
            model: getModel('standard'),
            prompt: `
You are a legal document analyst. Analyze this transcript and provide a structured summary.

Transcript (with timestamps):
${timestampedTranscript.substring(0, 30000)}

Provide your analysis as JSON with this structure:
{
  "summary": "1-2 paragraph executive summary of the transcript",
  "keyMoments": [
    {
      "timestamp": "MM:SS format from transcript",
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

IMPORTANT: For keyMoments, use the actual timestamps from the transcript (e.g., "00:15", "01:30").
`,
            output: { format: 'json', schema: SummarizationOutput }
          })
          summarization = summaryResponse.output
          logTime(`Summary generated: ${summarization?.keyMoments?.length || 0} key moments`)
        } catch (error) {
          logTime(`Summary generation failed: ${error}`)
        }
      }

      // Generate waveform peaks if we have a GCS URI
      let waveformPeaks: number[] | null = null
      if (mediaUri.startsWith('gs://')) {
        try {
          logTime('Generating waveform peaks...')
          const audioBuffer = await download(mediaUri)
          logTime(`Downloaded ${audioBuffer.length} bytes for waveform`)
          waveformPeaks = generateWaveformPeaks(audioBuffer, 800)
          logTime(`Generated ${waveformPeaks.length} waveform peaks`)
        } catch (error) {
          logTime(`Waveform generation failed: ${error}`)
        }
      }

      // Update Firestore with final results
      await docRef.update({
        status: 'completed',
        fullText: result.text,
        segments,
        speakers,
        duration: result.duration ?? null,
        language: result.language ?? null,
        provider: result.provider,
        summarization: summarization || null,
        waveformPeaks,
        processingTimeMs: result.processingTimeMs,
        completedAt: FieldValue.serverTimestamp()
      })

      logTime(`Successfully completed transcription for ${transcriptionId}`)

    } catch (error: any) {
      console.error(`[startTranscriptionJob] Failed for ${transcriptionId}:`, error)
      await docRef.update({
        status: 'failed',
        error: error.message || 'Failed to transcribe',
        failedAt: FieldValue.serverTimestamp()
      })
    }
  }
)

/**
 * Firestore trigger: Start document extraction
 *
 * When document status changes to "processing":
 * 1. Extracts document content with bounding boxes via Docling
 * 2. Stores pages and chunks in Firestore subcollections
 * 3. Indexes chunks in Qdrant vector store
 */
export const startDocumentExtraction = onDocumentUpdated(
  {
    document: 'documents/{documentId}',
    secrets: [googleAIApiKey, qdrantUrl, qdrantApiKey],
    memory: '2GiB',
    timeoutSeconds: 540 // 9 minutes for large documents
  },
  async (event) => {
    const beforeData = event.data?.before.data()
    const afterData = event.data?.after.data()
    const documentId = event.params.documentId

    // Only process when status changes to "processing"
    if (!afterData || beforeData?.status === afterData.status) {
      return
    }

    if (afterData.status !== 'processing') {
      return
    }

    // Skip if not a document type that needs extraction
    const extractableMimeTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'text/html',
      'text/markdown'
    ]

    if (!extractableMimeTypes.includes(afterData.mimeType)) {
      console.log(`[startDocumentExtraction] Skipping non-extractable document ${documentId} (${afterData.mimeType})`)
      return
    }

    console.log(`[startDocumentExtraction] Starting extraction for ${documentId}`)

    const gcsUri = `gs://${config.storageBucket}/${afterData.storagePath}`

    try {
      // Call the extraction flow
      const result = await extractDocumentFlow({
        documentId,
        gcsUri,
        filename: afterData.filename,
        caseId: afterData.caseId,
        options: {
          skipOcr: false,
          skipTableStructure: false,
          skipIndexing: false
        }
      })

      if (!result.success) {
        throw new Error(result.error || 'Extraction failed')
      }

      console.log(`[startDocumentExtraction] Completed: ${result.pageCount} pages, ${result.chunkCount} chunks`)

    } catch (error: any) {
      console.error(`[startDocumentExtraction] Failed for ${documentId}:`, error)
      const db = getFirestore()
      await db.doc(`documents/${documentId}`).update({
        status: 'failed',
        extractionStatus: 'failed',
        error: error.message || 'Document extraction failed',
        failedAt: FieldValue.serverTimestamp()
      })
    }
  }
)

