const admin = require('firebase-admin');

// Initialize Admin SDK for emulator
process.env.FIRESTORE_EMULATOR_HOST = 'localhost:8080';
process.env.FIREBASE_AUTH_EMULATOR_HOST = 'localhost:9099';

admin.initializeApp({
    projectId: 'legalease-420'
});

const auth = admin.auth();
const db = admin.firestore();

async function seed() {
    console.log('🌱 Seeding Firebase emulators...\n');

    try {
        // Create test user
        const email = 'test@example.com';
        const password = 'password123';

        let userId;
        try {
            const userRecord = await auth.createUser({
                email,
                password,
                displayName: 'Test User',
                emailVerified: true
            });
            userId = userRecord.uid;
            console.log('✓ Created test user:', email);
            console.log('  UID:', userId);
        } catch (error) {
            if (error.code === 'auth/email-already-exists') {
                const userRecord = await auth.getUserByEmail(email);
                userId = userRecord.uid;
                console.log('✓ Test user already exists:', email);
                console.log('  UID:', userId);
            } else {
                throw error;
            }
        }

        // Create test case
        const caseRef = await db.collection('cases').add({
            name: 'Sample Legal Case',
            caseNumber: 'CASE-2024-001',
            client: 'Acme Corporation',
            status: 'active',
            matterType: 'Contract Review',
            description: 'Sample case for testing',
            userId: userId,
            teamId: null,
            documentCount: 2,
            transcriptionCount: 1,
            createdAt: admin.firestore.FieldValue.serverTimestamp(),
            updatedAt: admin.firestore.FieldValue.serverTimestamp()
        });
        console.log('✓ Created test case:', caseRef.id);

        // Create test documents
        const doc1 = await db.collection('documents').add({
            caseId: caseRef.id,
            filename: 'interview_recording.mp3',
            title: 'Client Interview Recording',
            storagePath: 'test/interview_recording.mp3',
            downloadUrl: 'https://example.com/test.mp3',
            mimeType: 'audio/mpeg',
            fileSize: 5242880, // 5MB
            documentType: 'transcript',
            status: 'completed',
            userId: userId,
            teamId: null,
            extractedText: 'This is a sample transcription of the client interview...',
            summary: 'Client discussed contract terms and requested legal review.',
            createdAt: admin.firestore.FieldValue.serverTimestamp(),
            updatedAt: admin.firestore.FieldValue.serverTimestamp()
        });
        console.log('✓ Created test audio document:', doc1.id);

        const doc2 = await db.collection('documents').add({
            caseId: caseRef.id,
            filename: 'contract_draft.pdf',
            title: 'Contract Draft v1',
            storagePath: 'test/contract_draft.pdf',
            downloadUrl: 'https://example.com/test.pdf',
            mimeType: 'application/pdf',
            fileSize: 1048576, // 1MB
            documentType: 'contract',
            status: 'indexed',
            userId: userId,
            teamId: null,
            pageCount: 12,
            createdAt: admin.firestore.FieldValue.serverTimestamp(),
            updatedAt: admin.firestore.FieldValue.serverTimestamp()
        });
        console.log('✓ Created test PDF document:', doc2.id);

        console.log('\n✅ Seeding complete!');
        console.log('\nYou can now log in with:');
        console.log('  Email:', email);
        console.log('  Password:', password);
        console.log('\nView emulator UI at: http://localhost:4000');

        process.exit(0);
    } catch (error) {
        console.error('❌ Seeding failed:', error);
        process.exit(1);
    }
}

seed();
