import type {
  Timestamp
} from 'firebase/firestore'
import {
  collection,
  doc,
  addDoc,
  getDoc,
  getDocs,
  setDoc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  onSnapshot,
  serverTimestamp
} from 'firebase/firestore'

export interface Team {
  id?: string
  name: string
  ownerId: string
  description?: string
  createdAt?: Timestamp
  updatedAt?: Timestamp
}

export interface TeamMember {
  id?: string
  odcId: string
  email: string
  displayName?: string
  photoURL?: string
  role: 'owner' | 'admin' | 'member'
  joinedAt?: Timestamp
}

export interface TeamInvitation {
  id?: string
  email: string
  role: 'admin' | 'member'
  status: 'pending' | 'accepted' | 'declined'
  invitedBy: string
  createdAt?: Timestamp
  expiresAt?: Timestamp
}

export function useTeam() {
  const { $firestore } = useNuxtApp()
  const { user } = useAuth()

  const currentTeam = useState<Team | null>('current-team', () => null)
  const teams = useState<Team[]>('user-teams', () => [])
  const members = useState<TeamMember[]>('team-members', () => [])
  const invitations = useState<TeamInvitation[]>('team-invitations', () => [])
  const isLoading = useState<boolean>('team-loading', () => false)

  /**
   * Create a new team
   */
  async function createTeam(name: string, description?: string): Promise<string> {
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    isLoading.value = true

    try {
      const teamsRef = collection($firestore, 'teams')
      const teamDoc = await addDoc(teamsRef, {
        name,
        description,
        ownerId: user.value.uid,
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp()
      })

      // Add owner as first member
      const membersRef = collection($firestore, 'teams', teamDoc.id, 'members')
      await setDoc(doc(membersRef, user.value.uid), {
        userId: user.value.uid,
        email: user.value.email,
        displayName: user.value.displayName,
        photoURL: user.value.photoURL,
        role: 'owner',
        joinedAt: serverTimestamp()
      })

      await loadTeams()
      return teamDoc.id
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Load all teams the user is a member of
   */
  async function loadTeams(): Promise<void> {
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) return

    isLoading.value = true

    try {
      // Query all teams where user is a member
      // Note: This requires a collection group query or checking membership
      const teamsRef = collection($firestore, 'teams')
      const teamsSnapshot = await getDocs(teamsRef)

      const userTeams: Team[] = []

      for (const teamDoc of teamsSnapshot.docs) {
        const memberRef = doc($firestore, 'teams', teamDoc.id, 'members', user.value.uid)
        const memberSnap = await getDoc(memberRef)

        if (memberSnap.exists()) {
          userTeams.push({
            id: teamDoc.id,
            ...teamDoc.data()
          } as Team)
        }
      }

      teams.value = userTeams

      // Set current team if not set
      if (!currentTeam.value && userTeams.length > 0) {
        currentTeam.value = userTeams[0] ?? null
      }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Load members of a team
   */
  async function loadMembers(teamId: string): Promise<void> {
    if (!$firestore) throw new Error('Firestore not initialized')

    isLoading.value = true

    try {
      const membersRef = collection($firestore, 'teams', teamId, 'members')
      const membersSnapshot = await getDocs(membersRef)

      members.value = membersSnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as TeamMember[]
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Invite a user to the team
   */
  async function inviteMember(teamId: string, email: string, role: 'admin' | 'member' = 'member'): Promise<string> {
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    const invitationsRef = collection($firestore, 'teams', teamId, 'invitations')

    // Check if invitation already exists
    const existingQuery = query(invitationsRef, where('email', '==', email), where('status', '==', 'pending'))
    const existingSnapshot = await getDocs(existingQuery)

    if (!existingSnapshot.empty) {
      throw new Error('An invitation has already been sent to this email')
    }

    const invitationDoc = await addDoc(invitationsRef, {
      email,
      role,
      status: 'pending',
      invitedBy: user.value.uid,
      createdAt: serverTimestamp(),
      expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) // 7 days
    })

    await loadInvitations(teamId)
    return invitationDoc.id
  }

  /**
   * Load pending invitations for a team
   */
  async function loadInvitations(teamId: string): Promise<void> {
    if (!$firestore) throw new Error('Firestore not initialized')

    const invitationsRef = collection($firestore, 'teams', teamId, 'invitations')
    const invitationsQuery = query(invitationsRef, where('status', '==', 'pending'))
    const invitationsSnapshot = await getDocs(invitationsQuery)

    invitations.value = invitationsSnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    })) as TeamInvitation[]
  }

  /**
   * Accept an invitation
   */
  async function acceptInvitation(teamId: string, invitationId: string): Promise<void> {
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    const invitationRef = doc($firestore, 'teams', teamId, 'invitations', invitationId)
    const invitationSnap = await getDoc(invitationRef)

    if (!invitationSnap.exists()) {
      throw new Error('Invitation not found')
    }

    const invitation = invitationSnap.data() as TeamInvitation

    // Add user as member
    const membersRef = collection($firestore, 'teams', teamId, 'members')
    await setDoc(doc(membersRef, user.value.uid), {
      userId: user.value.uid,
      email: user.value.email,
      displayName: user.value.displayName,
      photoURL: user.value.photoURL,
      role: invitation.role,
      joinedAt: serverTimestamp()
    })

    // Update invitation status
    await updateDoc(invitationRef, {
      status: 'accepted'
    })

    await loadTeams()
  }

  /**
   * Remove a member from the team
   */
  async function removeMember(teamId: string, memberId: string): Promise<void> {
    if (!$firestore) throw new Error('Firestore not initialized')

    const memberRef = doc($firestore, 'teams', teamId, 'members', memberId)
    await deleteDoc(memberRef)

    await loadMembers(teamId)
  }

  /**
   * Update a member's role
   */
  async function updateMemberRole(teamId: string, memberId: string, role: 'admin' | 'member'): Promise<void> {
    if (!$firestore) throw new Error('Firestore not initialized')

    const memberRef = doc($firestore, 'teams', teamId, 'members', memberId)
    await updateDoc(memberRef, { role })

    await loadMembers(teamId)
  }

  /**
   * Cancel a pending invitation
   */
  async function cancelInvitation(teamId: string, invitationId: string): Promise<void> {
    if (!$firestore) throw new Error('Firestore not initialized')

    const invitationRef = doc($firestore, 'teams', teamId, 'invitations', invitationId)
    await deleteDoc(invitationRef)

    await loadInvitations(teamId)
  }

  /**
   * Update team details
   */
  async function updateTeam(teamId: string, data: Partial<Pick<Team, 'name' | 'description'>>): Promise<void> {
    if (!$firestore) throw new Error('Firestore not initialized')

    const teamRef = doc($firestore, 'teams', teamId)
    await updateDoc(teamRef, {
      ...data,
      updatedAt: serverTimestamp()
    })

    await loadTeams()
  }

  /**
   * Delete a team
   */
  async function deleteTeam(teamId: string): Promise<void> {
    if (!$firestore) throw new Error('Firestore not initialized')

    const teamRef = doc($firestore, 'teams', teamId)
    await deleteDoc(teamRef)

    if (currentTeam.value?.id === teamId) {
      currentTeam.value = teams.value.find(t => t.id !== teamId) ?? null
    }

    await loadTeams()
  }

  /**
   * Set the current active team
   */
  function setCurrentTeam(team: Team | null): void {
    currentTeam.value = team
  }

  return {
    currentTeam,
    teams,
    members,
    invitations,
    isLoading,
    createTeam,
    loadTeams,
    loadMembers,
    inviteMember,
    loadInvitations,
    acceptInvitation,
    removeMember,
    updateMemberRole,
    cancelInvitation,
    updateTeam,
    deleteTeam,
    setCurrentTeam
  }
}
