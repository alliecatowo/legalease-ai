import { onCallGenkit } from 'firebase-functions/https'
import { onDocumentUpdated } from 'firebase-functions/v2/firestore'
import { defineSecret } from 'firebase-functions/params'
import { getFirestore, FieldValue } from 'firebase-admin/firestore'
import { initializeApp, getApps } from 'firebase-admin/app'

// Initialize Firebase Admin if not already initialized
if (getApps().length === 0) {
  initializeApp()
}

// Import flows
import { transcribeMediaFlow, TranscriptionInput } from './flows/transcription.js'
import { summarizeTranscriptFlow, SummarizationInput } from './flows/summarization.js'
import { searchDocumentsFlow, indexDocumentFlow, SearchInput, IndexDocumentInput } from './flows/search.js'
import { generateWaveformFlow, WaveformInput } from './flows/waveform.js'
import { transcribe } from './transcription/index.js'
import { download } from './storage/index.js'
import { ai } from './genkit.js'
import { getModel } from './ai/index.js'
import { SummarizationOutput } from './flows/summarization.js'

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
    // TODO: Add auth policy once Firebase Auth is set up
    // authPolicy: hasClaim('email_verified'),
    cors: true,
    memory: '1GiB',
    timeoutSeconds: 540 // 9 minutes for long transcriptions
  },
  transcribeMediaFlow
)

export const summarizeTranscript = onCallGenkit(
  {
    secrets: [googleAIApiKey],
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 120
  },
  summarizeTranscriptFlow
)

export const searchDocuments = onCallGenkit(
  {
    secrets: [googleAIApiKey, qdrantUrl, qdrantApiKey],
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 60
  },
  searchDocumentsFlow
)

export const indexDocument = onCallGenkit(
  {
    secrets: [googleAIApiKey, qdrantUrl, qdrantApiKey],
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 120
  },
  indexDocumentFlow
)

export const generateWaveform = onCallGenkit(
  {
    cors: true,
    memory: '1GiB', // May need more memory for large audio files
    timeoutSeconds: 120
  },
  generateWaveformFlow
)

// Re-export schemas for client-side use
export { TranscriptionInput, SummarizationInput, SearchInput, IndexDocumentInput, WaveformInput }

/**
 * Firestore trigger: Start transcription job (non-blocking)
 *
 * When status changes to "processing":
 * 1. Calls Chirp batchRecognize with output to GCS
 * 2. Saves the operation name to Firestore
 * 3. Returns immediately (doesn't wait for transcription to complete)
 *
 * The completion is handled by onTranscriptionComplete trigger
 */
export const startTranscriptionJob = onDocumentUpdated(
  {
    document: 'transcriptions/{transcriptionId}',
    secrets: [googleAIApiKey],
    memory: '512MiB',
    timeoutSeconds: 60 // Just starting the job, should be fast
  },
  async (event) => {
    const beforeData = event.data?.before.data()
    const afterData = event.data?.after.data()
    const transcriptionId = event.params.transcriptionId

    // Only process when status changes to "processing"
    if (!afterData || beforeData?.status === afterData.status) {
      return
    }

    if (afterData.status !== 'processing') {
      return
    }

    console.log(`[startTranscriptionJob] Starting job for ${transcriptionId}`)

    const db = getFirestore()
    const docRef = db.collection('transcriptions').doc(transcriptionId)

    try {
      const mediaUri = afterData.gsUri || afterData.downloadUrl
      if (!mediaUri) {
        throw new Error('No media URI available for transcription')
      }

      if (!mediaUri.startsWith('gs://')) {
        throw new Error('Chirp requires GCS URI (gs://...). Upload the file first.')
      }

      // Import Speech V2 client
      const { SpeechClient } = await import('@google-cloud/speech').then(m => m.v2)
      const location = 'us'
      const client = new SpeechClient({
        apiEndpoint: `${location}-speech.googleapis.com`
      })

      const projectId = process.env.GCLOUD_PROJECT || process.env.GOOGLE_CLOUD_PROJECT || 'legalease-420'
      const recognizer = `projects/${projectId}/locations/${location}/recognizers/_`

      // Output location for results (GCS)
      const outputBucket = `${projectId}.firebasestorage.app`
      const outputPath = `transcription-results/${transcriptionId}.json`
      const outputUri = `gs://${outputBucket}/${outputPath}`

      // Build recognition config
      const config: any = {
        autoDecodingConfig: {},
        languageCodes: ['en-US'],
        model: 'chirp_3',
        features: {
          enableAutomaticPunctuation: true,
          enableWordTimeOffsets: true,
          diarizationConfig: {
            minSpeakerCount: 1,
            maxSpeakerCount: 6
          }
        }
      }

      // Start batch recognition with GCS output (async - doesn't wait)
      const batchRequest = {
        recognizer,
        config,
        files: [{ uri: mediaUri }],
        recognitionOutputConfig: {
          gcsOutputConfig: {
            uri: outputUri
          }
        }
      }

      console.log(`[startTranscriptionJob] Calling batchRecognize, output: ${outputUri}`)
      const [operation] = await client.batchRecognize(batchRequest)

      // Save operation info to Firestore - we're done here!
      // The GCS trigger will handle the completion
      await docRef.update({
        status: 'transcribing',
        operationName: operation.name,
        outputUri: outputUri,
        transcriptionStartedAt: FieldValue.serverTimestamp()
      })

      console.log(`[startTranscriptionJob] Job started: ${operation.name}`)

    } catch (error: any) {
      console.error(`[startTranscriptionJob] Failed for ${transcriptionId}:`, error)
      await docRef.update({
        status: 'failed',
        error: error.message || 'Failed to start transcription',
        failedAt: FieldValue.serverTimestamp()
      })
    }
  }
)

/**
 * Storage trigger: Process completed transcription results
 *
 * Triggered when Chirp writes results to GCS (transcription-results/*.json)
 * 1. Reads the transcription results from GCS
 * 2. Generates AI summary
 * 3. Generates waveform peaks
 * 4. Updates Firestore with final results
 */
import { onObjectFinalized } from 'firebase-functions/v2/storage'

export const onTranscriptionComplete = onObjectFinalized(
  {
    bucket: 'legalease-420.firebasestorage.app',
    region: 'us-west1', // Must match bucket region
    secrets: [googleAIApiKey],
    memory: '2GiB',
    timeoutSeconds: 540,
    cpu: 2
  },
  async (event) => {
    const filePath = event.data.name

    // Only process transcription results
    if (!filePath.startsWith('transcription-results/') || !filePath.endsWith('.json')) {
      return
    }

    // Extract transcription ID from filename
    const transcriptionId = filePath.replace('transcription-results/', '').replace('.json', '')
    console.log(`[onTranscriptionComplete] Processing results for ${transcriptionId}`)

    const startTime = Date.now()
    const logTime = (msg: string) => console.log(`[onTranscriptionComplete] [${Date.now() - startTime}ms] ${msg}`)

    const db = getFirestore()
    const docRef = db.collection('transcriptions').doc(transcriptionId)

    try {
      // Get the transcription doc to get the media URI for waveform
      const transcriptionDoc = await docRef.get()
      if (!transcriptionDoc.exists) {
        throw new Error(`Transcription document ${transcriptionId} not found`)
      }
      const transcriptionData = transcriptionDoc.data()!

      // Download and parse the results from GCS
      logTime('Downloading transcription results from GCS...')
      const gcsUri = `gs://${event.data.bucket}/${filePath}`
      const resultsBuffer = await download(gcsUri)
      const resultsJson = JSON.parse(resultsBuffer.toString('utf-8'))
      logTime('Results downloaded and parsed')

      // Process the Chirp results into our format
      const { segments, speakers, fullText, duration, language } = processChirpResults(resultsJson)
      logTime(`Processed ${segments.length} segments, ${speakers.length} speakers`)

      // Generate summary if transcript is substantial
      let summarization = null
      if (fullText.length > 100) {
        try {
          logTime('Generating summary...')

          const timestampedTranscript = segments.slice(0, 500).map(seg => {
            const mins = Math.floor(seg.start / 60)
            const secs = Math.floor(seg.start % 60)
            const timestamp = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
            const speaker = seg.speaker || 'Unknown'
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

      // Generate waveform peaks
      let waveformPeaks: number[] | null = null
      const mediaUri = transcriptionData.gsUri
      if (mediaUri?.startsWith('gs://')) {
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
        fullText,
        segments,
        speakers,
        duration: duration ?? null,
        language: language ?? null,
        summarization: summarization || null,
        waveformPeaks,
        completedAt: FieldValue.serverTimestamp()
      })

      logTime(`Successfully completed transcription for ${transcriptionId}`)

      // Clean up the results file from GCS (optional)
      // await deleteFile(gcsUri)

    } catch (error: any) {
      logTime(`FAILED for ${transcriptionId}: ${error?.message || error}`)
      await docRef.update({
        status: 'failed',
        error: error.message || 'Failed to process transcription results',
        failedAt: FieldValue.serverTimestamp()
      })
    }
  }
)

/**
 * Helper: Process Chirp batch results JSON into our segment format
 */
function processChirpResults(resultsJson: any): {
  segments: Array<{ id: string; start: number; end: number; text: string; speaker: string | null; confidence: number | null }>
  speakers: Array<{ id: string; inferredName: string | null }>
  fullText: string
  duration: number | null
  language: string | null
} {
  const segments: Array<{ id: string; start: number; end: number; text: string; speaker: string | null; confidence: number | null }> = []
  const speakerSet = new Set<string>()
  let fullText = ''
  let lastEndTime = 0
  let segmentIndex = 0
  let detectedLanguage: string | null = null

  // Helper to parse duration strings like "10.500s" or {seconds, nanos}
  const parseDuration = (duration: any): number => {
    if (!duration) return 0
    if (typeof duration === 'string') return parseFloat(duration.replace('s', '')) || 0
    if (typeof duration === 'object') {
      const secs = parseInt(duration.seconds || '0', 10)
      const nanos = parseInt(duration.nanos || '0', 10)
      return secs + (nanos / 1_000_000_000)
    }
    return 0
  }

  // Results may be nested in different ways depending on output format
  const results = resultsJson.results || resultsJson

  for (const [, fileResult] of Object.entries(results)) {
    const transcript = (fileResult as any).transcript
    if (!transcript?.results) continue

    for (const result of transcript.results) {
      if (!result.alternatives?.length) continue

      if (result.languageCode && !detectedLanguage) {
        detectedLanguage = result.languageCode
      }

      const alternative = result.alternatives[0]
      const words = alternative.words || []

      if (words.length > 0 && words[0]?.speakerLabel) {
        // Group words by speaker
        let currentSpeaker = words[0].speakerLabel
        let currentWords: any[] = []

        for (const word of words) {
          const wordSpeaker = word.speakerLabel || currentSpeaker
          if (wordSpeaker !== currentSpeaker && currentWords.length > 0) {
            // Save current segment
            const segText = currentWords.map((w: any) => w.word).join(' ').trim()
            if (segText) {
              segments.push({
                id: `seg-${segmentIndex++}`,
                start: parseDuration(currentWords[0].startOffset),
                end: parseDuration(currentWords[currentWords.length - 1].endOffset),
                text: segText,
                speaker: currentSpeaker,
                confidence: alternative.confidence ?? null
              })
              speakerSet.add(currentSpeaker)
              fullText += segText + ' '
            }
            currentWords = [word]
            currentSpeaker = wordSpeaker
          } else {
            currentWords.push(word)
          }
        }
        // Don't forget the last segment
        if (currentWords.length > 0) {
          const segText = currentWords.map((w: any) => w.word).join(' ').trim()
          if (segText) {
            const endTime = parseDuration(currentWords[currentWords.length - 1].endOffset)
            segments.push({
              id: `seg-${segmentIndex++}`,
              start: parseDuration(currentWords[0].startOffset),
              end: endTime,
              text: segText,
              speaker: currentSpeaker,
              confidence: alternative.confidence ?? null
            })
            speakerSet.add(currentSpeaker)
            fullText += segText + ' '
            if (endTime > lastEndTime) lastEndTime = endTime
          }
        }
      } else {
        // No diarization - single segment
        const transcriptText = (alternative.transcript || '').trim()
        if (transcriptText) {
          const endTime = parseDuration(result.resultEndOffset)
          segments.push({
            id: `seg-${segmentIndex++}`,
            start: Math.max(0, endTime - (transcriptText.length * 0.05)),
            end: endTime,
            text: transcriptText,
            speaker: null,
            confidence: alternative.confidence ?? null
          })
          fullText += transcriptText + ' '
          if (endTime > lastEndTime) lastEndTime = endTime
        }
      }
    }
  }

  const speakers = Array.from(speakerSet).sort().map(id => ({
    id,
    inferredName: null
  }))

  return {
    segments,
    speakers,
    fullText: fullText.trim(),
    duration: lastEndTime > 0 ? lastEndTime : null,
    language: detectedLanguage
  }
}
