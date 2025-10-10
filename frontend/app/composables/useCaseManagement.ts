import { ref } from 'vue'

export interface CaseParty {
  id: string
  name: string
  role: 'plaintiff' | 'defendant' | 'attorney' | 'witness' | 'expert' | 'other'
  email?: string
  phone?: string
  organization?: string
  avatar?: string
}

export interface CaseDeadline {
  id: string
  title: string
  date: string
  type: 'filing' | 'hearing' | 'discovery' | 'trial' | 'other'
  completed: boolean
  description?: string
}

export interface CaseDocument {
  id: string
  title: string
  documentType: string
  uploadDate: string
  fileSize: number
  status: string
}

export interface CaseNote {
  id: string
  content: string
  createdAt: string
  createdBy: string
  attachments?: string[]
}

export interface CaseTask {
  id: string
  title: string
  completed: boolean
  dueDate?: string
  assignee?: string
  priority: 'low' | 'medium' | 'high'
}

export interface Case {
  id: string
  caseNumber: string
  title: string
  description?: string
  status: 'active' | 'pending' | 'closed' | 'archived'
  practiceArea: string
  jurisdiction: string
  openDate: string
  closeDate?: string
  parties: CaseParty[]
  documents: CaseDocument[]
  deadlines: CaseDeadline[]
  notes: CaseNote[]
  tasks: CaseTask[]
  tags: string[]
  assignedAttorney?: string
}

export function useCaseManagement() {
  const currentCase = ref<Case | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Load case by ID
  async function loadCase(caseId: string) {
    isLoading.value = true
    error.value = null

    try {
      // TODO: Replace with real API call
      // const response = await api.cases.get(caseId)
      // currentCase.value = response.data

      // Mock data for now
      await new Promise(resolve => setTimeout(resolve, 500))
      currentCase.value = getMockCase(caseId)
    } catch (err) {
      error.value = 'Failed to load case'
      console.error(err)
    } finally {
      isLoading.value = false
    }
  }

  // Add party to case
  async function addParty(party: Omit<CaseParty, 'id'>) {
    if (!currentCase.value) return

    const newParty: CaseParty = {
      ...party,
      id: `party-${Date.now()}`
    }

    currentCase.value.parties.push(newParty)
    // TODO: Save to backend
  }

  // Remove party from case
  async function removeParty(partyId: string) {
    if (!currentCase.value) return

    currentCase.value.parties = currentCase.value.parties.filter(p => p.id !== partyId)
    // TODO: Save to backend
  }

  // Add deadline
  async function addDeadline(deadline: Omit<CaseDeadline, 'id'>) {
    if (!currentCase.value) return

    const newDeadline: CaseDeadline = {
      ...deadline,
      id: `deadline-${Date.now()}`
    }

    currentCase.value.deadlines.push(newDeadline)
    // TODO: Save to backend
  }

  // Toggle deadline completion
  async function toggleDeadline(deadlineId: string) {
    if (!currentCase.value) return

    const deadline = currentCase.value.deadlines.find(d => d.id === deadlineId)
    if (deadline) {
      deadline.completed = !deadline.completed
      // TODO: Save to backend
    }
  }

  // Add note
  async function addNote(content: string, createdBy: string) {
    if (!currentCase.value) return

    const newNote: CaseNote = {
      id: `note-${Date.now()}`,
      content,
      createdAt: new Date().toISOString(),
      createdBy
    }

    currentCase.value.notes.unshift(newNote)
    // TODO: Save to backend
  }

  // Add task
  async function addTask(task: Omit<CaseTask, 'id'>) {
    if (!currentCase.value) return

    const newTask: CaseTask = {
      ...task,
      id: `task-${Date.now()}`
    }

    currentCase.value.tasks.push(newTask)
    // TODO: Save to backend
  }

  // Toggle task completion
  async function toggleTask(taskId: string) {
    if (!currentCase.value) return

    const task = currentCase.value.tasks.find(t => t.id === taskId)
    if (task) {
      task.completed = !task.completed
      // TODO: Save to backend
    }
  }

  // Link document to case
  async function linkDocument(documentId: string) {
    if (!currentCase.value) return

    // TODO: Implement document linking
    console.log('Linking document:', documentId)
  }

  // Update case status
  async function updateStatus(status: Case['status']) {
    if (!currentCase.value) return

    currentCase.value.status = status
    // TODO: Save to backend
  }

  return {
    currentCase,
    isLoading,
    error,
    loadCase,
    addParty,
    removeParty,
    addDeadline,
    toggleDeadline,
    addNote,
    addTask,
    toggleTask,
    linkDocument,
    updateStatus
  }
}

// Mock data generator
function getMockCase(caseId: string): Case {
  return {
    id: caseId,
    caseNumber: 'CV-2024-1234',
    title: 'Acme Corp v. Global Tech Inc - Contract Dispute',
    description: 'Breach of contract claim regarding Master Services Agreement dated January 15, 2024',
    status: 'active',
    practiceArea: 'Commercial Litigation',
    jurisdiction: 'Delaware Superior Court',
    openDate: '2024-01-20',
    parties: [
      {
        id: 'party-1',
        name: 'Acme Corporation',
        role: 'plaintiff',
        email: 'legal@acmecorp.com',
        organization: 'Acme Corporation',
        avatar: ''
      },
      {
        id: 'party-2',
        name: 'Global Tech Inc',
        role: 'defendant',
        email: 'legal@globaltech.com',
        organization: 'Global Tech Inc',
        avatar: ''
      },
      {
        id: 'party-3',
        name: 'Sarah Johnson',
        role: 'attorney',
        email: 'sjohnson@lawfirm.com',
        organization: 'Johnson & Partners LLP',
        avatar: ''
      }
    ],
    documents: [
      {
        id: 'doc-1',
        title: 'Master Services Agreement',
        documentType: 'contract',
        uploadDate: '2024-01-20',
        fileSize: 2457600,
        status: 'processed'
      },
      {
        id: 'doc-2',
        title: 'Complaint',
        documentType: 'court_filing',
        uploadDate: '2024-01-22',
        fileSize: 1234567,
        status: 'processed'
      }
    ],
    deadlines: [
      {
        id: 'deadline-1',
        title: 'Answer to Complaint Due',
        date: '2024-02-20',
        type: 'filing',
        completed: false,
        description: 'Defendant must file answer within 30 days'
      },
      {
        id: 'deadline-2',
        title: 'Initial Case Management Conference',
        date: '2024-03-15',
        type: 'hearing',
        completed: false
      }
    ],
    notes: [
      {
        id: 'note-1',
        content: 'Initial client meeting completed. Reviewed contract terms and identified three potential breach points.',
        createdAt: '2024-01-20T10:00:00Z',
        createdBy: 'Sarah Johnson'
      }
    ],
    tasks: [
      {
        id: 'task-1',
        title: 'Draft interrogatories',
        completed: false,
        dueDate: '2024-02-01',
        priority: 'high'
      },
      {
        id: 'task-2',
        title: 'Review contract exhibits',
        completed: true,
        priority: 'medium'
      }
    ],
    tags: ['contract', 'commercial', 'active'],
    assignedAttorney: 'Sarah Johnson'
  }
}
