/**
 * Tenant isolation helpers.
 *
 * Every callable that touches Qdrant or document data MUST derive the caller
 * from the verified Firebase Auth context, never from client-sent IDs, and
 * must scope vector queries by the owner fields stored on each point.
 */

import { HttpsError } from 'firebase-functions/https'

/** Minimal slice of the Firestore Admin API used here (eases unit testing). */
export interface FirestoreLike {
  doc(path: string): {
    get(): Promise<{ exists: boolean; id: string; data(): Record<string, any> | undefined }>
  }
  collectionGroup(id: string): {
    where(field: string, op: '==', value: unknown): {
      get(): Promise<{ docs: Array<{ ref: { parent: { parent: { id: string } | null } }; data(): Record<string, any> }> }>
    }
  }
}

export interface Actor {
  uid: string
  teamIds: string[]
}

export interface Owner {
  userId: string
  teamId: string | null
}

export interface AuthorizedDocument extends Owner {
  documentId: string
  caseId: string | null
  filename: string | null
  storagePath: string | null
  collection: 'documents' | 'transcriptions'
}

/** Extract the verified uid from a callable's context. Throws if unauthenticated. */
export function requireUid(context: { auth?: { uid?: string } | null } | undefined | null): string {
  const uid = context?.auth?.uid
  if (!uid || typeof uid !== 'string') {
    throw new HttpsError('unauthenticated', 'Sign in required')
  }
  return uid
}

/** IDs of every team the user is a member of (teams/{teamId}/members/{uid}). */
export async function getTeamIds(db: FirestoreLike, uid: string): Promise<string[]> {
  const snap = await db.collectionGroup('members').where('userId', '==', uid).get()
  const ids = new Set<string>()
  for (const d of snap.docs) {
    const teamId = d.ref.parent.parent?.id
    // Defence in depth: the member doc's own userId must match.
    if (teamId && d.data().userId === uid) ids.add(teamId)
  }
  return [...ids]
}

export async function resolveActor(
  db: FirestoreLike,
  context: { auth?: { uid?: string } | null } | undefined | null
): Promise<Actor> {
  const uid = requireUid(context)
  return { uid, teamIds: await getTeamIds(db, uid) }
}

export function canAccess(actor: Actor, owner: { userId?: unknown; teamId?: unknown }): boolean {
  if (owner.userId === actor.uid) return true
  return typeof owner.teamId === 'string' && actor.teamIds.includes(owner.teamId)
}

/**
 * Load a document (or transcription) and verify the actor may access it.
 * Missing and forbidden both surface as `not-found` so IDs cannot be probed.
 */
export async function authorizeDocument(
  db: FirestoreLike,
  actor: Actor,
  documentId: string
): Promise<AuthorizedDocument> {
  if (!documentId || documentId.includes('/')) {
    throw new HttpsError('invalid-argument', 'Invalid document ID')
  }
  for (const collection of ['documents', 'transcriptions'] as const) {
    const snap = await db.doc(`${collection}/${documentId}`).get()
    if (!snap.exists) continue
    const data = snap.data() ?? {}
    if (!canAccess(actor, data)) break
    return {
      documentId,
      collection,
      userId: data.userId,
      teamId: typeof data.teamId === 'string' ? data.teamId : null,
      caseId: typeof data.caseId === 'string' ? data.caseId : null,
      filename: typeof data.filename === 'string' ? data.filename : null,
      storagePath: typeof data.storagePath === 'string' ? data.storagePath : null
    }
  }
  throw new HttpsError('not-found', 'Document not found')
}

/** Qdrant condition limiting results to points the actor owns or shares via team. */
export function ownerScope(actor: Actor): Record<string, unknown> {
  const should: Record<string, unknown>[] = [{ key: 'userId', match: { value: actor.uid } }]
  if (actor.teamIds.length > 0) {
    should.push({ key: 'teamId', match: { any: actor.teamIds } })
  }
  return { should }
}

/** Combine caller-supplied narrowing conditions with the mandatory owner scope. */
export function scopedFilter(actor: Actor, conditions: Record<string, unknown>[] = []) {
  return { must: [...conditions, ownerScope(actor)] }
}

/** Payload fields that every indexed point must carry. */
export function ownerPayload(owner: Owner): { userId: string; teamId: string | null } {
  return { userId: owner.userId, teamId: owner.teamId }
}

/** Storage objects for documents live under documents/{ownerUid}/... */
export function assertStoragePathOwned(storagePath: string | null, owner: Owner): string {
  const prefix = `documents/${owner.userId}/`
  if (!storagePath || !storagePath.startsWith(prefix) || storagePath.includes('..')) {
    throw new HttpsError('permission-denied', 'Document storage path does not belong to its owner')
  }
  return storagePath
}
