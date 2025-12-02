// MongoDB initialization script for Orchestration Service
// This script creates the database, user, collections, and indexes

// Switch to the orchestration database
db = db.getSiblingDB('orchestration');

print('Initializing MongoDB for Orchestration Service...');

// Create application user with read/write permissions
// Note: Update username and password as needed for your environment
try {
    db.createUser({
        user: 'orchestrator',
        pwd: 'orchestrator_pass',
        roles: [
            {
                role: 'readWrite',
                db: 'orchestration'
            }
        ]
    });
    print('✓ Created orchestrator user');
} catch (e) {
    if (e.code === 51003) {
        print('⚠ User orchestrator already exists');
    } else {
        print('✗ Failed to create user: ' + e.message);
        throw e;
    }
}

// Create collections
print('\nCreating collections...');

// Sessions collection
if (!db.getCollectionNames().includes('sessions')) {
    db.createCollection('sessions');
    print('✓ Created sessions collection');
} else {
    print('⚠ sessions collection already exists');
}

// Messages collection
if (!db.getCollectionNames().includes('messages')) {
    db.createCollection('messages');
    print('✓ Created messages collection');
} else {
    print('⚠ messages collection already exists');
}

// Transcripts collection
if (!db.getCollectionNames().includes('transcripts')) {
    db.createCollection('transcripts');
    print('✓ Created transcripts collection');
} else {
    print('⚠ transcripts collection already exists');
}

// Create indexes
print('\nCreating indexes...');

// Sessions collection indexes
print('Creating indexes for sessions collection...');

// TTL index: expire sessions after 24 hours of inactivity (86400 seconds)
try {
    db.sessions.createIndex(
        { "updated_at": 1 },
        { 
            name: "ttl_updated_at",
            expireAfterSeconds: 86400
        }
    );
    print('✓ Created TTL index on sessions.updated_at (24 hour expiration)');
} catch (e) {
    print('⚠ TTL index on sessions.updated_at: ' + e.message);
}

// Compound index for active sessions query
try {
    db.sessions.createIndex(
        { "active": 1, "updated_at": -1 },
        { name: "active_updated_idx" }
    );
    print('✓ Created compound index on sessions (active, updated_at)');
} catch (e) {
    print('⚠ Compound index on sessions: ' + e.message);
}

// Messages collection indexes
print('\nCreating indexes for messages collection...');

// TTL index: expire messages after 7 days (604800 seconds)
try {
    db.messages.createIndex(
        { "created_at": 1 },
        { 
            name: "ttl_created_at",
            expireAfterSeconds: 604800
        }
    );
    print('✓ Created TTL index on messages.created_at (7 day expiration)');
} catch (e) {
    print('⚠ TTL index on messages.created_at: ' + e.message);
}

// Compound index for session queries
try {
    db.messages.createIndex(
        { "session_id": 1, "timestamp": 1 },
        { name: "session_timestamp_idx" }
    );
    print('✓ Created compound index on messages (session_id, timestamp)');
} catch (e) {
    print('⚠ Compound index on messages: ' + e.message);
}

// Index for agent notes queries
try {
    db.messages.createIndex(
        { "session_id": 1, "is_agent_note": 1 },
        { name: "session_agent_note_idx" }
    );
    print('✓ Created compound index on messages (session_id, is_agent_note)');
} catch (e) {
    print('⚠ Compound index on messages (agent notes): ' + e.message);
}

// Transcripts collection indexes
print('\nCreating indexes for transcripts collection...');

// TTL index: expire transcripts after 30 days (2592000 seconds)
try {
    db.transcripts.createIndex(
        { "created_at": 1 },
        { 
            name: "ttl_created_at",
            expireAfterSeconds: 2592000
        }
    );
    print('✓ Created TTL index on transcripts.created_at (30 day expiration)');
} catch (e) {
    print('⚠ TTL index on transcripts.created_at: ' + e.message);
}

// Index for session lookup
try {
    db.transcripts.createIndex(
        { "session_id": 1 },
        { name: "session_id_idx" }
    );
    print('✓ Created index on transcripts.session_id');
} catch (e) {
    print('⚠ Index on transcripts.session_id: ' + e.message);
}

// Display collection statistics
print('\n=== Collection Statistics ===');
print('Sessions: ' + db.sessions.countDocuments({}));
print('Messages: ' + db.messages.countDocuments({}));
print('Transcripts: ' + db.transcripts.countDocuments({}));

// Display indexes
print('\n=== Indexes ===');
print('\nSessions indexes:');
db.sessions.getIndexes().forEach(function(idx) {
    print('  - ' + idx.name + ': ' + JSON.stringify(idx.key));
});

print('\nMessages indexes:');
db.messages.getIndexes().forEach(function(idx) {
    print('  - ' + idx.name + ': ' + JSON.stringify(idx.key));
});

print('\nTranscripts indexes:');
db.transcripts.getIndexes().forEach(function(idx) {
    print('  - ' + idx.name + ': ' + JSON.stringify(idx.key));
});

print('\n✓ MongoDB initialization complete!');
print('\nConnection string format:');
print('mongodb://orchestrator:orchestrator_pass@localhost:27017/orchestration');
print('\nSet MONGODB_URL environment variable to use MongoDB persistence.');
