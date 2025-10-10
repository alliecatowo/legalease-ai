export interface Document {
  id: string
  name: string
  type: string
  uploadedAt: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  size: number
}

export interface ComplianceResult {
  documentId: string
  score: number
  issues: ComplianceIssue[]
  timestamp: string
}

export interface ComplianceIssue {
  severity: 'low' | 'medium' | 'high' | 'critical'
  category: string
  description: string
  location?: {
    page: number
    section: string
  }
}

export interface User {
  id: string
  email: string
  name: string
  role: 'user' | 'admin'
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}
