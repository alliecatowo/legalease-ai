import { z } from 'genkit'
import { ai } from '../genkit.js'
import { download } from '../storage/index.js'

// Input schema
export const WaveformInput = z.object({
  gcsUri: z.string().describe('GCS URI of the audio file (gs://bucket/path)'),
  samplesPerPeak: z.number().default(256).describe('Number of audio samples per peak (lower = more detail)'),
  targetPeaks: z.number().default(800).describe('Target number of peaks for the waveform')
})

export type WaveformInputType = z.infer<typeof WaveformInput>

// Output schema
export const WaveformOutput = z.object({
  peaks: z.array(z.number()).describe('Normalized peak values (-1 to 1)'),
  duration: z.number().optional().describe('Audio duration in seconds'),
  sampleRate: z.number().optional().describe('Audio sample rate')
})

export type WaveformOutputType = z.infer<typeof WaveformOutput>


// Generate waveform peaks from audio file
export const generateWaveformFlow = ai.defineFlow(
  {
    name: 'generateWaveform',
    inputSchema: WaveformInput,
    outputSchema: WaveformOutput
  },
  async (input) => {
    const { gcsUri, samplesPerPeak, targetPeaks } = input

    // Download the audio file using storage abstraction
    // Supports gs://, s3://, and other provider URIs
    const fileBuffer = await download(gcsUri)

    // For MP3/audio files, we need to decode them to get raw samples
    // In a serverless environment, we can use a pure-JS decoder
    // For now, generate a simplified waveform from the file's raw bytes
    // This provides a visual representation even without full audio decoding

    // Calculate peaks from raw audio bytes (simplified approach)
    // This works for uncompressed formats and provides approximate visuals for compressed
    const peaks = generatePeaksFromBuffer(fileBuffer, targetPeaks)

    return {
      peaks,
      duration: undefined, // Would need full decode to get accurate duration
      sampleRate: undefined
    }
  }
)

// Generate peaks from raw buffer data
// This is a simplified approach that provides visual representation
// For accurate peaks, a full audio decoder would be needed
function generatePeaksFromBuffer(buffer: Buffer, targetPeaks: number): number[] {
  const peaks: number[] = []
  const bytesPerPeak = Math.max(1, Math.floor(buffer.length / targetPeaks))

  for (let i = 0; i < targetPeaks; i++) {
    const start = i * bytesPerPeak
    const end = Math.min(start + bytesPerPeak, buffer.length)

    let sum = 0
    let count = 0

    // Sample bytes and calculate average amplitude
    for (let j = start; j < end; j += 2) {
      // Interpret bytes as signed 16-bit samples (common format)
      if (j + 1 < buffer.length) {
        const sample = buffer.readInt16LE(j)
        sum += Math.abs(sample)
        count++
      }
    }

    // Normalize to 0-1 range
    const avgAmplitude = count > 0 ? sum / count / 32768 : 0
    peaks.push(Math.min(1, avgAmplitude))
  }

  // Apply some smoothing for better visual appearance
  const smoothed = smoothPeaks(peaks, 3)

  // Normalize to use full range
  const max = Math.max(...smoothed, 0.001)
  return smoothed.map(p => p / max)
}

// Simple moving average smoothing
function smoothPeaks(peaks: number[], windowSize: number): number[] {
  const result: number[] = []
  const halfWindow = Math.floor(windowSize / 2)

  for (let i = 0; i < peaks.length; i++) {
    let sum = 0
    let count = 0

    for (let j = i - halfWindow; j <= i + halfWindow; j++) {
      if (j >= 0 && j < peaks.length) {
        sum += peaks[j]
        count++
      }
    }

    result.push(sum / count)
  }

  return result
}
