import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterAll, beforeAll, beforeEach, describe, it } from 'vitest'
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
  type RulesTestEnvironment
} from '@firebase/rules-unit-testing'
import { doc, getDoc, setDoc, updateDoc, deleteDoc } from 'firebase/firestore'

let env: RulesTestEnvironment

beforeAll(async () => {
  env = await initializeTestEnvironment({
    projectId: 'demo-legalease-rules',
    firestore: { rules: readFileSync(resolve(__dirname, '../../firestore.rules'), 'utf8') }
  })
})
afterAll(async () => env.cleanup())

// Seed: alice owns case-a, doc-a, tr-a; team-1 is owned by alice with bob as a member.
beforeEach(async () => {
  await env.clearFirestore()
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore()
    await setDoc(doc(db, 'users/alice'), { name: 'Alice' })
    await setDoc(doc(db, 'cases/case-a'), { userId: 'alice', teamId: null, title: 'A' })
    await setDoc(doc(db, 'documents/doc-a'), { userId: 'alice', teamId: null, caseId: 'case-a' })
    await setDoc(doc(db, 'transcriptions/tr-a'), { userId: 'alice', teamId: null })
    await setDoc(doc(db, 'teams/team-1'), { ownerId: 'alice', name: 'T' })
    await setDoc(doc(db, 'teams/team-1/members/alice'), { userId: 'alice', role: 'owner' })
    await setDoc(doc(db, 'teams/team-1/members/bob'), { userId: 'bob', role: 'member' })
    await setDoc(doc(db, 'cases/case-team'), { userId: 'alice', teamId: 'team-1' })
  })
})

const as = (uid: string) => env.authenticatedContext(uid).firestore()

describe('second user (mallory) cannot touch alice data', () => {
  it('cannot read case, document, transcription or user profile', async () => {
    const db = as('mallory')
    await assertFails(getDoc(doc(db, 'cases/case-a')))
    await assertFails(getDoc(doc(db, 'documents/doc-a')))
    await assertFails(getDoc(doc(db, 'transcriptions/tr-a')))
    await assertFails(getDoc(doc(db, 'users/alice')))
  })
  it('cannot update or delete', async () => {
    const db = as('mallory')
    await assertFails(updateDoc(doc(db, 'documents/doc-a'), { title: 'x' }))
    await assertFails(deleteDoc(doc(db, 'documents/doc-a')))
    await assertFails(deleteDoc(doc(db, 'cases/case-a')))
  })
  it('cannot read a team case, or create into a team they are not in', async () => {
    const db = as('mallory')
    await assertFails(getDoc(doc(db, 'cases/case-team')))
    await assertFails(setDoc(doc(db, 'cases/x'), { userId: 'mallory', teamId: 'team-1' }))
  })
  it('unauthenticated users get nothing', async () => {
    const db = env.unauthenticatedContext().firestore()
    await assertFails(getDoc(doc(db, 'cases/case-a')))
  })
})

describe('owner fields are pinned on create', () => {
  it('rejects spoofed userId on cases, documents and transcriptions', async () => {
    const db = as('mallory')
    await assertFails(setDoc(doc(db, 'cases/s1'), { userId: 'alice', teamId: null }))
    await assertFails(setDoc(doc(db, 'documents/s2'), { userId: 'alice', teamId: null }))
    await assertFails(setDoc(doc(db, 'transcriptions/s3'), { userId: 'alice', teamId: null }))
  })
  it('rejects missing userId', async () => {
    await assertFails(setDoc(doc(as('mallory'), 'cases/s4'), { title: 'no owner' }))
  })
  it('allows own docs, and team docs for members', async () => {
    await assertSucceeds(setDoc(doc(as('mallory'), 'cases/ok1'), { userId: 'mallory', teamId: null }))
    await assertSucceeds(setDoc(doc(as('bob'), 'cases/ok2'), { userId: 'bob', teamId: 'team-1' }))
  })
  it('rejects a document attached to a case the caller cannot access', async () => {
    await assertFails(setDoc(doc(as('mallory'), 'documents/s5'), { userId: 'mallory', teamId: null, caseId: 'case-a' }))
    await assertSucceeds(setDoc(doc(as('alice'), 'documents/ok3'), { userId: 'alice', teamId: null, caseId: 'case-a' }))
  })
  it('team creation must name the caller as owner', async () => {
    await assertFails(setDoc(doc(as('mallory'), 'teams/t2'), { ownerId: 'alice' }))
    await assertSucceeds(setDoc(doc(as('mallory'), 'teams/t3'), { ownerId: 'mallory' }))
  })
})

describe('owner fields are immutable on update', () => {
  it('owner cannot reassign userId or teamId', async () => {
    const db = as('alice')
    await assertFails(updateDoc(doc(db, 'documents/doc-a'), { userId: 'mallory' }))
    await assertFails(updateDoc(doc(db, 'documents/doc-a'), { teamId: 'team-1' }))
    await assertFails(updateDoc(doc(db, 'cases/case-a'), { userId: 'mallory' }))
    await assertFails(updateDoc(doc(db, 'transcriptions/tr-a'), { teamId: 'team-1' }))
    await assertFails(updateDoc(doc(db, 'documents/doc-a'), { caseId: 'other' }))
  })
  it('team member cannot take over a shared case', async () => {
    await assertFails(updateDoc(doc(as('bob'), 'cases/case-team'), { userId: 'bob' }))
  })
  it('normal updates still work', async () => {
    await assertSucceeds(updateDoc(doc(as('alice'), 'documents/doc-a'), { title: 'renamed' }))
    await assertSucceeds(updateDoc(doc(as('bob'), 'cases/case-team'), { title: 'by bob' }))
  })
  it('team ownerId is immutable', async () => {
    await assertFails(updateDoc(doc(as('alice'), 'teams/team-1'), { ownerId: 'mallory' }))
    await assertSucceeds(updateDoc(doc(as('alice'), 'teams/team-1'), { name: 'new' }))
  })
})

describe('users profile', () => {
  it('owner can read and write, others cannot', async () => {
    await assertSucceeds(getDoc(doc(as('alice'), 'users/alice')))
    await assertSucceeds(setDoc(doc(as('alice'), 'users/alice'), { name: 'A2' }))
    await assertFails(setDoc(doc(as('mallory'), 'users/alice'), { name: 'pwn' }))
  })
})
