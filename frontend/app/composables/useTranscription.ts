import { ref, computed } from 'vue'

export interface TranscriptSegment {
  id: string
  start: number  // seconds
  end: number    // seconds
  text: string
  speaker?: string
  confidence?: number
  isKeyMoment?: boolean
  tags?: string[]
}

export interface Speaker {
  id: string
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
  documentId?: number  // Added for search filtering
  createdAt: string
  segments: TranscriptSegment[]
  speakers: Speaker[]
  metadata?: {
    fileSize?: number
    format?: string
    sampleRate?: number
    bitRate?: number
  }
}

export function useTranscription() {
  const currentTranscription = ref<Transcription | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const currentTime = ref(0)
  const isPlaying = ref(false)
  const selectedSegment = ref<TranscriptSegment | null>(null)
  const searchQuery = ref('')
  const selectedSpeaker = ref<string | null>(null)
  const showOnlyKeyMoments = ref(false)

  // Speaker colors
  const speakerColors = [
    '#3B82F6',
    '#8B5CF6',
    '#10B981',
    '#F59E0B',
    '#EF4444',
    '#EC4899',
    '#6366F1',
    '#14B8A6'
  ]

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

  // Load transcription
  async function loadTranscription(transcriptionId: string) {
    isLoading.value = true
    error.value = null

    try {
      // TODO: Replace with real API call
      // const response = await api.transcriptions.get(transcriptionId)
      // currentTranscription.value = response.data

      // Mock delay
      await new Promise(resolve => setTimeout(resolve, 500))
      currentTranscription.value = getMockTranscription(transcriptionId)
    } catch (err) {
      error.value = 'Failed to load transcription'
      console.error(err)
    } finally {
      isLoading.value = false
    }
  }

  // Seek to time
  function seekToTime(time: number) {
    currentTime.value = time
  }

  // Seek to segment
  function seekToSegment(segment: TranscriptSegment) {
    selectedSegment.value = segment
    currentTime.value = segment.start
  }

  // Toggle key moment
  function toggleKeyMoment(segmentId: string) {
    if (!currentTranscription.value) return

    const segment = currentTranscription.value.segments.find(s => s.id === segmentId)
    if (segment) {
      segment.isKeyMoment = !segment.isKeyMoment
      // TODO: Save to backend
    }
  }

  // Add speaker
  function addSpeaker(name: string, role?: string) {
    if (!currentTranscription.value) return

    const speaker: Speaker = {
      id: `speaker-${Date.now()}`,
      name,
      role,
      color: speakerColors[currentTranscription.value.speakers.length % speakerColors.length]
    }

    currentTranscription.value.speakers.push(speaker)
    // TODO: Save to backend
  }

  // Update speaker
  function updateSpeaker(speakerId: string, updates: Partial<Speaker>) {
    if (!currentTranscription.value) return

    const speaker = currentTranscription.value.speakers.find(s => s.id === speakerId)
    if (speaker) {
      Object.assign(speaker, updates)
      // TODO: Save to backend
    }
  }

  // Assign speaker to segment
  function assignSpeaker(segmentId: string, speakerId: string) {
    if (!currentTranscription.value) return

    const segment = currentTranscription.value.segments.find(s => s.id === segmentId)
    if (segment) {
      segment.speaker = speakerId
      // TODO: Save to backend
    }
  }

  // Edit segment text
  function editSegmentText(segmentId: string, text: string) {
    if (!currentTranscription.value) return

    const segment = currentTranscription.value.segments.find(s => s.id === segmentId)
    if (segment) {
      segment.text = text
      // TODO: Save to backend
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
        // TODO: Implement PDF and DOCX export
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
    loadTranscription,
    seekToTime,
    seekToSegment,
    toggleKeyMoment,
    addSpeaker,
    updateSpeaker,
    assignSpeaker,
    editSegmentText,
    exportTranscript,
    formatTime
  }
}

// Mock data generator
function getMockTranscription(id: string): Transcription {
  const speakers: Speaker[] = [
    { id: 'speaker-1', name: 'Attorney Smith', role: 'Plaintiff Attorney', color: '#3B82F6' },
    { id: 'speaker-2', name: 'Witness Johnson', role: 'Witness', color: '#8B5CF6' },
    { id: 'speaker-3', name: 'Attorney Davis', role: 'Defense Attorney', color: '#10B981' }
  ]

  const segments: TranscriptSegment[] = [
    {
      id: 'seg-1',
      start: 0,
      end: 8,
      text: 'Good morning. This is the deposition of John Johnson in the matter of Acme Corp versus Global Tech Inc.',
      speaker: 'speaker-1',
      confidence: 0.98
    },
    {
      id: 'seg-2',
      start: 8,
      end: 15,
      text: 'Mr. Johnson, please state your full name for the record.',
      speaker: 'speaker-1',
      confidence: 0.96
    },
    {
      id: 'seg-3',
      start: 15,
      end: 20,
      text: 'John Robert Johnson.',
      speaker: 'speaker-2',
      confidence: 0.99
    },
    {
      id: 'seg-4',
      start: 20,
      end: 28,
      text: 'And what is your current position at Global Tech Inc?',
      speaker: 'speaker-1',
      confidence: 0.95
    },
    {
      id: 'seg-5',
      start: 28,
      end: 38,
      text: 'I am the Chief Technology Officer and have been with the company for eight years.',
      speaker: 'speaker-2',
      confidence: 0.97,
      isKeyMoment: true
    },
    {
      id: 'seg-6',
      start: 38,
      end: 52,
      text: 'Can you describe your role in the contract negotiations with Acme Corporation that took place in January 2024?',
      speaker: 'speaker-1',
      confidence: 0.94,
      isKeyMoment: true
    },
    {
      id: 'seg-7',
      start: 52,
      end: 68,
      text: 'I was the primary technical contact. I reviewed all the technical specifications and participated in three meetings with their team.',
      speaker: 'speaker-2',
      confidence: 0.96
    },
    {
      id: 'seg-8',
      start: 68,
      end: 75,
      text: 'Objection. The question calls for speculation.',
      speaker: 'speaker-3',
      confidence: 0.99
    },
    {
      id: 'seg-9',
      start: 75,
      end: 82,
      text: 'Let me rephrase. Were you present at any meetings with Acme Corporation in January 2024?',
      speaker: 'speaker-1',
      confidence: 0.97
    },
    {
      id: 'seg-10',
      start: 82,
      end: 92,
      text: 'Yes, I attended meetings on January 10th, 15th, and 22nd of 2024.',
      speaker: 'speaker-2',
      confidence: 0.98,
      isKeyMoment: true
    }
  ]

  return {
    id,
    title: 'Deposition - John Johnson',
    audioUrl: '/mock-audio.mp3',  // TODO: Replace with real audio
    duration: 92,
    status: 'completed',
    caseId: 'case-1',
    caseName: 'Acme Corp v. Global Tech Inc',
    createdAt: '2024-03-15T10:00:00Z',
    segments,
    speakers,
    metadata: {
      fileSize: 15728640,
      format: 'MP3',
      sampleRate: 44100,
      bitRate: 128
    }
  }
}
