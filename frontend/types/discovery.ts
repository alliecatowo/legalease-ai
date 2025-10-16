export type DiscoveryItemType =
  | 'PHOTO'
  | 'VIDEO'
  | 'AUDIO'
  | 'SOCIAL_MEDIA_POST'
  | 'EMAIL'
  | 'CALL_LOG'
  | 'SMS'
  | 'DOCUMENT'

export type DiscoveryItemSource =
  | 'CELLEBRITE'
  | 'PROSECUTOR'
  | 'EVIDENCE'
  | 'SURVEILLANCE'
  | 'BODY_CAM'
  | 'SOCIAL_MEDIA'
  | 'EMAIL_EXPORT'
  | 'PHONE_RECORDS'
  | 'OTHER'

export type DiscoveryItemFormFactor =
  | 'SHORT_FORM'
  | 'LONG_FORM'
  | 'SINGLE_ITEM'
  | 'BATCH_DUMP'

export type CategoryType =
  | 'AUTO_GENERATED'
  | 'MANUAL'
  | 'CASE_SPECIFIC'

export type ImportStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'PARTIALLY_COMPLETED'

export type CallType =
  | 'INCOMING'
  | 'OUTGOING'
  | 'MISSED'
  | 'VOICEMAIL'
  | 'FACETIME'
  | 'VIDEO_CALL'

export interface VisualContent {
  id: number
  discovery_item_id: number
  frame_number: number | null
  timestamp_in_video: number | null
  vlm_caption: string
  detected_objects: string[] | null
  detected_scenes: string[] | null
  detected_activities: string[] | null
  sensitive_flags: Record<string, boolean> | null
  is_meme: boolean
  created_at: string
}

export interface VideoSummary {
  id: number
  discovery_item_id: number
  comprehensive_summary: string
  key_moments: Array<{
    timestamp: number
    description: string
    importance: number
  }>
  visual_summary: string | null
  audio_summary: string | null
  importance_score: number | null
  flagged_content: Record<string, any> | null
  created_at: string
}

export interface Category {
  id: number
  name: string
  description: string | null
  type: CategoryType
  parent_category_id: number | null
  color: string | null
  icon: string | null
  created_at: string
  updated_at: string
}

export interface SocialMediaPost {
  id: number
  discovery_item_id: number
  platform: string
  author: string | null
  content: string | null
  post_text?: string | null
  post_url: string | null
  post_date: string | null
  post_timestamp?: string | null
  engagement_metrics: Record<string, any> | null
  hashtags: string[] | null
  mentions: string[] | null
  media_urls?: string[] | null
  attachments?: Array<Record<string, any>> | null
  comments?: Array<Record<string, any>> | null
  created_at: string
}

export interface EmailMessage {
  id: number
  discovery_item_id: number
  subject: string | null
  sender: string | null
  recipients: string[] | null
  cc: string[] | null
  bcc: string[] | null
  body: string | null
  html_body: string | null
  sent_date: string | null
  has_attachments: boolean
  attachment_count: number
  created_at: string
}

export interface CallLog {
  id: number
  discovery_item_id: number
  call_type: CallType
  caller: string | null
  recipient: string | null
  duration_seconds: number | null
  call_date: string | null
  notes: string | null
  created_at: string
}

export interface ImportBatch {
  id: number
  case_id: number
  source_type: DiscoveryItemSource
  import_path: string | null
  total_items: number
  processed_items: number
  status: ImportStatus
  error_log: Record<string, any> | null
  started_at: string
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface DiscoveryItem {
  id: number
  case_id: number
  type: DiscoveryItemType
  source: DiscoveryItemSource
  form_factor: DiscoveryItemFormFactor
  original_filename: string
  file_path: string
  item_metadata: Record<string, any> | null
  processed: boolean
  importance_score: number | null
  created_at: string
  updated_at: string

  // Relationships
  visual_content?: VisualContent[]
  video_summary?: VideoSummary
  categories?: Category[]
  social_media_post?: SocialMediaPost
  email_message?: EmailMessage
  call_log?: CallLog
}

export interface DiscoveryItemFilters {
  search?: string
  type?: DiscoveryItemType
  source?: DiscoveryItemSource
  formFactor?: DiscoveryItemFormFactor
  minImportance?: number
  maxImportance?: number
  startDate?: string
  endDate?: string
  categories?: number[]
  processedOnly?: boolean
  memeFilter?: boolean
}

export interface DiscoveryStats {
  total: number
  highImportance: number
  processing: number
  storageUsed: number
}

export interface ImportanceScoreExplanation {
  score: number
  summary: string
  breakdown: Array<{
    factor: string
    items: string[]
    contribution: number
  }>
}

export type DiscoveryItemPreviewType =
  | 'image'
  | 'video'
  | 'audio'
  | 'text'
  | 'table'
  | 'key_value'
  | 'markdown'
  | 'html'
  | 'binary'
  | 'unsupported'

export interface DiscoveryItemPreview {
  preview_type: DiscoveryItemPreviewType
  content_type: string
  size: number
  text?: string | null
  truncated: boolean
  headers?: string[] | null
  rows?: string[][] | null
  key_values?: Array<{ label: string; value: string }> | null
  html?: string | null
  markdown?: string | null
}
