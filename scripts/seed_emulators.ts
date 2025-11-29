import { initializeApp } from 'firebase/app'
import { getAuth, connectAuthEmulator, createUserWithEmailAndPassword } from 'firebase/auth'
import { getFirestore, connectFirestoreEmulator, collection, addDoc, serverTimestamp } from 'firebase/firestore'

const firebaseConfig = {
    projectId: 'legalease-420',
    apiKey: 'fake-api-key',
    authDomain: 'legalease-420.firebaseapp.com'
}

const app = initializeApp(firebaseConfig)
const auth = getAuth(app)
const db = getFirestore(app)

connectAuthEmulator(auth, 'http://localhost:9099')
connectFirestoreEmulator(db, 'localhost', 8080)

async function seed() {
    console.log('Seeding emulators...')

    try {
        // Create test user
        const email = 'test@example.com'
        const password = 'password123'
        let user
        try {
            const userCredential = await createUserWithEmailAndPassword(auth, email, password)
            user = userCredential.user
            console.log(`Created user: ${email}`)
        } catch (e: any) {
            if (e.code === 'auth/email-already-in-use') {
                console.log(`User ${email} already exists`)
                // We would need to sign in to get the UID if we wanted to use it, 
                // but for now we'll just assume the user exists or was just created.
                // For simplicity in this script, let's just create a new random user if needed
                // or just proceed.
            } else {
                throw e
            }
        }

        if (user) {
            // Create a test case
            const casesRef = collection(db, 'cases')
            const caseDoc = await addDoc(casesRef, {
                name: 'Test Case 1',
                caseNumber: 'CASE-001',
                client: 'Acme Corp',
                status: 'active',
                userId: user.uid,
                documentCount: 1,
                createdAt: serverTimestamp(),
                updatedAt: serverTimestamp()
            })
            console.log(`Created case: ${caseDoc.id}`)

            // Create a test document (transcript)
            const docsRef = collection(db, 'documents')
            await addDoc(docsRef, {
                caseId: caseDoc.id,
                filename: 'test_audio.mp3',
                title: 'Test Interview',
                mimeType: 'audio/mpeg',
                fileSize: 1024 * 1024 * 5, // 5MB
                documentType: 'transcript',
                status: 'completed',
                userId: user.uid,
                createdAt: serverTimestamp(),
                updatedAt: serverTimestamp()
            })
            console.log('Created test transcript document')
        }

        console.log('Seeding complete!')
        process.exit(0)
    } catch (e) {
        console.error('Seeding failed:', e)
        process.exit(1)
    }
}

seed()
