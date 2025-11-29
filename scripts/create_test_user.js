#!/usr/bin/env node

// Simple script to create test user in Auth emulator
// Run with: node scripts/create_test_user.js

const http = require('http');

const testUser = {
    email: 'test@example.com',
    password: 'password123',
    displayName: 'Test User',
    emailVerified: true
};

const data = JSON.stringify(testUser);

const options = {
    hostname: 'localhost',
    port: 9099,
    path: '/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake-api-key',
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': data.length
    }
};

const req = http.request(options, (res) => {
    let responseData = '';

    res.on('data', (chunk) => {
        responseData += chunk;
    });

    res.on('end', () => {
        if (res.statusCode === 200) {
            const result = JSON.parse(responseData);
            console.log('✓ Test user created successfully!');
            console.log('  Email:', testUser.email);
            console.log('  Password:', testUser.password);
            console.log('  UID:', result.localId);
        } else {
            console.log('Response:', responseData);
        }
    });
});

req.on('error', (error) => {
    console.error('Error creating test user:', error.message);
    console.log('Make sure the Auth emulator is running on port 9099');
});

req.write(data);
req.end();
