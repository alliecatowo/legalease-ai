import { ref, computed } from 'vue'
import type { TranscriptSegment, Speaker } from '~/types/transcription'

// Extended segment type for UI features
export interface TranscriptSegmentUI extends TranscriptSegment {
  isKeyMoment?: boolean
  tags?: string[]
}

// Extended speaker type for UI features
export interface SpeakerUI extends Speaker {
  name: string
  role?: string
  color: string
}

export interface Transcription {
  id: string
  title: string
  audioUrl: string
  duration: number
  status: 'processing' | 'completed' | 'failed'
  caseId?: string
  caseName?: string
  createdAt: string
  segments: TranscriptSegmentUI[]
  speakers: SpeakerUI[]
  fullText?: string
  summary?: string
  metadata?: {
    fileSize?: number
    format?: string
    sampleRate?: number
    bitRate?: number
  }
}

// Speaker colors for UI
const SPEAKER_COLORS = [
  '#3B82F6',
  '#8B5CF6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#EC4899',
  '#6366F1',
  '#14B8A6'
]

export function useTranscription() {
  const currentTranscription = ref<Transcription | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const currentTime = ref(0)
  const isPlaying = ref(false)
  const selectedSegment = ref<TranscriptSegmentUI | null>(null)
  const searchQuery = ref('')
  const selectedSpeaker = ref<string | null>(null)
  const showOnlyKeyMoments = ref(false)

  // Filter segments
  const filteredSegments = computed(() => {
    if (!currentTranscription.value) return []

    let segments = currentTranscription.value.segments

    // Filter by speaker
    if (selectedSpeaker.value) {
      segments = segments.filter(s => s.speaker === selectedSpeaker.value)
    }

    // Filter by key moments
    if (showOnlyKeyMoments.value) {
      segments = segments.filter(s => s.isKeyMoment)
    }

    // Filter by search query
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      segments = segments.filter(s =>
        s.text.toLowerCase().includes(query)
      )
    }

    return segments
  })

  // Get current segment based on playback time
  const currentSegment = computed(() => {
    if (!currentTranscription.value) return null

    return currentTranscription.value.segments.find(segment =>
      currentTime.value >= segment.start && currentTime.value <= segment.end
    ) || null
  })

  // Get key moments
  const keyMoments = computed(() => {
    if (!currentTranscription.value) return []
    return currentTranscription.value.segments.filter(s => s.isKeyMoment)
  })

  // Load transcription from document data
  function loadFromDocument(doc: any): void {
    if (!doc) {
      currentTranscription.value = null
      return
    }

    // Convert speakers from backend format to UI format
    const speakers: SpeakerUI[] = (doc.speakers || []).map((s: Speaker, index: number) => ({
      ...s,
      name: s.inferredName || s.id,
      color: SPEAKER_COLORS[index % SPEAKER_COLORS.length]
    }))

    // Convert segments from backend format to UI format
    // Use backend ID if available, otherwise generate fallback for backward compatibility
    const segments: TranscriptSegmentUI[] = (doc.segments || []).map((s: TranscriptSegment, index: number) => ({
      ...s,
      id: s.id || `seg-${index}`,
      isKeyMoment: (s as any).isKeyMoment || false,
      tags: (s as any).tags || []
    }))

    currentTranscription.value = {
      id: doc.id,
      title: doc.title || doc.filename || 'Untitled',
      audioUrl: doc.downloadUrl || '',
      duration: doc.duration || 0,
      status: doc.status || 'completed',
      caseId: doc.caseId,
      caseName: doc.caseName,
      createdAt: doc.createdAt?.toDate?.().toISOString() || new Date().toISOString(),
      segments,
      speakers,
      fullText: doc.fullText || doc.extractedText,
      summary: doc.summary,
      metadata: {
        fileSize: doc.fileSize,
        format: doc.mimeType?.split('/').pop()?.toUpperCase()
      }
    }
  }

  // Seek to time
  function seekToTime(time: number) {
    currentTime.value = time
  }

  // Seek to segment
  function seekToSegment(segment: TranscriptSegmentUI) {
    selectedSegment.value = segment
    currentTime.value = segment.start
  }

  // Toggle key moment
  function toggleKeyMoment(segmentId: string) {
    if (!currentTranscription.value) return

    const segment = currentTranscription.value.segments.find(s => s.id === segmentId)
    if (segment) {
      segment.isKeyMoment = !segment.isKeyMoment
    }
  }

  // Add speaker
  function addSpeaker(name: string, role?: string) {
    if (!currentTranscription.value) return

    const speaker: SpeakerUI = {
      id: `speaker-${Date.now()}`,
      name,
      role,
      color: SPEAKER_COLORS[currentTranscription.value.speakers.length % SPEAKER_COLORS.length]
    }

    currentTranscription.value.speakers.push(speaker)
  }

  // Update speaker
  function updateSpeaker(speakerId: string, updates: Partial<SpeakerUI>) {
    if (!currentTranscription.value) return

    const speaker = currentTranscription.value.speakers.find(s => s.id === speakerId)
    if (speaker) {
      Object.assign(speaker, updates)
    }
  }

  // Assign speaker to segment
  function assignSpeaker(segmentId: string, speakerId: string) {
    if (!currentTranscription.value) return

    const segment = currentTranscription.value.segments.find(s => s.id === segmentId)
    if (segment) {
      segment.speaker = speakerId
    }
  }

  // Edit segment text
  function editSegmentText(segmentId: string, text: string) {
    if (!currentTranscription.value) return

    const segment = currentTranscription.value.segments.find(s => s.id === segmentId)
    if (segment) {
      segment.text = text
    }
  }

  // Export transcript
  function exportTranscript(format: 'txt' | 'pdf' | 'docx' | 'srt' | 'vtt'): string {
    if (!currentTranscription.value) return ''

    switch (format) {
      case 'txt':
        return exportAsText()
      case 'srt':
        return exportAsSRT()
      case 'vtt':
        return exportAsVTT()
      default:
        return exportAsText()
    }
  }

  // Export as plain text
  function exportAsText(): string {
    if (!currentTranscription.value) return ''

    let text = `${currentTranscription.value.title}\n\n`

    currentTranscription.value.segments.forEach(segment => {
      const speaker = currentTranscription.value!.speakers.find(s => s.id === segment.speaker)
      const speakerName = speaker?.name || 'Unknown'
      const timestamp = formatTime(segment.start)
      text += `[${timestamp}] ${speakerName}: ${segment.text}\n\n`
    })

    return text
  }

  // Export as SRT (SubRip)
  function exportAsSRT(): string {
    if (!currentTranscription.value) return ''

    let srt = ''

    currentTranscription.value.segments.forEach((segment, index) => {
      const startTime = formatSRTTime(segment.start)
      const endTime = formatSRTTime(segment.end)
      const speaker = currentTranscription.value!.speakers.find(s => s.id === segment.speaker)
      const text = speaker ? `${speaker.name}: ${segment.text}` : segment.text

      srt += `${index + 1}\n`
      srt += `${startTime} --> ${endTime}\n`
      srt += `${text}\n\n`
    })

    return srt
  }

  // Export as WebVTT
  function exportAsVTT(): string {
    if (!currentTranscription.value) return ''

    let vtt = 'WEBVTT\n\n'

    currentTranscription.value.segments.forEach(segment => {
      const startTime = formatVTTTime(segment.start)
      const endTime = formatVTTTime(segment.end)
      const speaker = currentTranscription.value!.speakers.find(s => s.id === segment.speaker)
      const text = speaker ? `<v ${speaker.name}>${segment.text}` : segment.text

      vtt += `${startTime} --> ${endTime}\n`
      vtt += `${text}\n\n`
    })

    return vtt
  }

  // Format time (MM:SS)
  function formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }

  // Format SRT time (HH:MM:SS,mmm)
  function formatSRTTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    const ms = Math.floor((seconds % 1) * 1000)

    return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')},${String(ms).padStart(3, '0')}`
  }

  // Format VTT time (HH:MM:SS.mmm)
  function formatVTTTime(seconds: number): string {
    const time = formatSRTTime(seconds)
    return time.replace(',', '.')
  }

  // Reset state
  function reset() {
    currentTranscription.value = null
    currentTime.value = 0
    isPlaying.value = false
    selectedSegment.value = null
    searchQuery.value = ''
    selectedSpeaker.value = null
    showOnlyKeyMoments.value = false
    error.value = null
  }

  return {
    currentTranscription,
    isLoading,
    error,
    currentTime,
    isPlaying,
    selectedSegment,
    searchQuery,
    selectedSpeaker,
    showOnlyKeyMoments,
    filteredSegments,
    currentSegment,
    keyMoments,
    loadFromDocument,
    seekToTime,
    seekToSegment,
    toggleKeyMoment,
    addSpeaker,
    updateSpeaker,
    assignSpeaker,
    editSegmentText,
    exportTranscript,
    formatTime,
    reset
  }
}
