import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FakeDb, FakeQdrant } from './helpers.js'

const qdrant = new FakeQdrant()
let db: FakeDb

vi.mock('@qdrant/js-client-rest', () => ({ QdrantClient: class { constructor() { return qdrant } } }))
vi.mock('firebase-admin/firestore', () => ({
  getFirestore: () => db,
  FieldValue: { serverTimestamp: () => 'ts' }
}))
vi.mock('firebase-functions/params', () => ({ defineSecret: () => ({ value: () => 'x' }) }))
vi.mock('../src/genkit.js', () => ({
  ai: {
    // Flows become plain async functions: (input, { context }) => output
    defineFlow: (_cfg: unknown, fn: unknown) => fn,
    embed: async () => [{ embedding: [0.1, 0.2] }]
  }
}))
vi.mock('../src/ai/index.js', () => ({
  getEmbedder: () => 'embedder',
  getModelConfig: () => ({ provider: 'google' })
}))
vi.mock('../src/config.js', () => ({
  default: { storageBucket: 'bkt', qdrant: { isLocal: true, url: 'http://x', apiKey: '', collectionName: 'c' } }
}))
const extractDocument = vi.fn()
vi.mock('../src/providers/document/index.js', () => ({ extractDocument }))

const ctx = (uid?: string) => ({ context: uid ? { auth: { uid } } : {} }) as any
const chunk = (id: string, text: string) => ({
  id, text, type: 'paragraph' as const, headings: [], pageNumbers: [1], elementTypes: [], bboxesJson: '[]'
})

beforeEach(() => {
  qdrant.points = []
  extractDocument.mockReset()
  db = new FakeDb({
    'documents/doc-alice': { userId: 'alice', teamId: null, caseId: 'case-alice', filename: 'a.pdf', storagePath: 'documents/alice/case-alice/a.pdf' },
    'documents/doc-team': { userId: 'alice', teamId: 'team-1', caseId: 'case-team', filename: 't.pdf', storagePath: 'documents/alice/case-team/t.pdf' },
    'teams/team-1/members/alice': { userId: 'alice' },
    'teams/team-1/members/bob': { userId: 'bob' }
  })
})

async function seed() {
  const { indexDocumentChunksFlow } = await import('../src/flows/search.js') as any
  await indexDocumentChunksFlow({ documentId: 'doc-alice', caseId: null, chunks: [chunk('c1', 'secret alice text')] }, ctx('alice'))
  await indexDocumentChunksFlow({ documentId: 'doc-team', caseId: null, chunks: [chunk('c2', 'team text')] }, ctx('alice'))
}

const search = async (uid: string | undefined, extra: Record<string, unknown> = {}) => {
  const { searchDocumentsFlow } = await import('../src/flows/search.js') as any
  return searchDocumentsFlow(
    { query: 'secret', limit: 20, scoreThreshold: 0, includeBboxes: true, ...extra },
    ctx(uid)
  )
}

describe('searchDocuments', () => {
  it('rejects unauthenticated callers', async () => {
    await expect(search(undefined)).rejects.toThrow(/Sign in/)
  })
  it('owner finds own points; owner fields come from Firestore', async () => {
    await seed()
    const r = await search('alice')
    expect(r.results.map((x: any) => x.documentId).sort()).toEqual(['doc-alice', 'doc-team'])
    expect(qdrant.points.every(p => p.payload.userId === 'alice')).toBe(true)
    expect(qdrant.points.find(p => p.payload.documentId === 'doc-team')!.payload.teamId).toBe('team-1')
    expect(qdrant.points.find(p => p.payload.documentId === 'doc-alice')!.payload.caseId).toBe('case-alice')
  })
  it('a second user sees nothing of the first, even when naming their caseId/documentId', async () => {
    await seed()
    expect((await search('mallory')).results).toEqual([])
    expect((await search('mallory', { caseId: 'case-alice' })).results).toEqual([])
    expect((await search('mallory', { documentId: 'doc-alice' })).results).toEqual([])
  })
  it('team member sees team-shared points but not private ones', async () => {
    await seed()
    const r = await search('bob')
    expect(r.results.map((x: any) => x.documentId)).toEqual(['doc-team'])
  })
})

describe('indexDocumentChunks', () => {
  it('refuses to index into a document the caller cannot access', async () => {
    const { indexDocumentChunksFlow } = await import('../src/flows/search.js') as any
    await expect(
      indexDocumentChunksFlow({ documentId: 'doc-alice', caseId: null, chunks: [chunk('x', 'poison')] }, ctx('mallory'))
    ).rejects.toThrow(/not found/i)
    expect(qdrant.points).toHaveLength(0)
  })
  it('ignores client-sent owner by deriving it from the record; rejects mismatched caseId', async () => {
    const { indexDocumentChunksFlow } = await import('../src/flows/search.js') as any
    await expect(
      indexDocumentChunksFlow({ documentId: 'doc-alice', caseId: 'someone-elses-case', chunks: [chunk('x', 't')] }, ctx('alice'))
    ).rejects.toThrow(/caseId/)
  })
})

describe('deleteDocumentChunks', () => {
  it('a second user cannot delete the first user\'s vectors', async () => {
    await seed()
    const { deleteDocumentChunksFlow } = await import('../src/flows/search.js') as any
    await deleteDocumentChunksFlow({ documentId: 'doc-alice' }, ctx('mallory'))
    expect(qdrant.points).toHaveLength(2)
    await deleteDocumentChunksFlow({ documentId: 'doc-team' }, ctx('mallory'))
    expect(qdrant.points).toHaveLength(2)
  })
  it('owner can delete; works after the Firestore doc is gone', async () => {
    await seed()
    delete db.docs['documents/doc-alice']
    const { deleteDocumentChunksFlow } = await import('../src/flows/search.js') as any
    await deleteDocumentChunksFlow({ documentId: 'doc-alice' }, ctx('alice'))
    expect(qdrant.points.map(p => p.payload.documentId)).toEqual(['doc-team'])
  })
  it('rejects unauthenticated callers', async () => {
    const { deleteDocumentChunksFlow } = await import('../src/flows/search.js') as any
    await expect(deleteDocumentChunksFlow({ documentId: 'doc-alice' }, ctx())).rejects.toThrow(/Sign in/)
  })
})

describe('extractDocument', () => {
  const run = async (uid: string | undefined, input: Record<string, unknown>) => {
    const { extractDocumentFlow } = await import('../src/flows/document-extraction.js') as any
    return extractDocumentFlow({ documentId: 'doc-alice', ...input }, ctx(uid))
  }
  it('rejects unauthenticated and non-owner callers without touching the document', async () => {
    await expect(run(undefined, {})).rejects.toThrow(/Sign in/)
    await expect(run('mallory', {})).rejects.toThrow(/not found/i)
    expect(extractDocument).not.toHaveBeenCalled()
  })
  it('rejects a client-sent gcsUri pointing at another object', async () => {
    await expect(run('alice', { gcsUri: 'gs://bkt/documents/bob/secret.pdf' })).rejects.toThrow(/gcsUri/)
    expect(extractDocument).not.toHaveBeenCalled()
  })
  it('rejects storagePath outside the owner prefix (record tampering)', async () => {
    db.docs['documents/doc-alice']!.storagePath = 'documents/bob/case/secret.pdf'
    await expect(run('alice', {})).rejects.toThrow(/storage path/i)
    expect(extractDocument).not.toHaveBeenCalled()
  })
})
