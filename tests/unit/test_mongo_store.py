"""Unit tests for MongoDBConversationStore."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from uuid import UUID, uuid4

from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError

from src.infrastructure.database.mongo_store import MongoDBConversationStore
from src.memory.models import ConversationState, Message, MessageRole, AgentNote, AgentType


@pytest.fixture
def mock_mongo_client():
    """Create a mock MongoDB client."""
    with patch('src.infrastructure.database.mongo_store.MongoClient') as mock_client:
        # Setup mock database and collections
        mock_db = MagicMock()
        mock_sessions = MagicMock()
        mock_messages = MagicMock()
        mock_transcripts = MagicMock()
        
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.side_effect = lambda name: {
            'sessions': mock_sessions,
            'messages': mock_messages,
            'transcripts': mock_transcripts,
        }[name]
        
        yield {
            'client': mock_client,
            'db': mock_db,
            'sessions': mock_sessions,
            'messages': mock_messages,
            'transcripts': mock_transcripts,
        }


@pytest.mark.asyncio
async def test_create_session(mock_mongo_client):
    """Test creating a new conversation session."""
    # Setup mock
    mock_sessions = mock_mongo_client['sessions']
    mock_result = MagicMock()
    mock_result.inserted_id = str(uuid4())
    mock_sessions.insert_one.return_value = mock_result
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Create session
    state = await store.create_session()
    
    # Assertions
    assert state.session_id is not None
    assert state.active is True
    assert state.turn_count == 0
    assert len(state.messages) == 0
    assert len(state.agent_notes) == 0
    mock_sessions.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_found(mock_mongo_client):
    """Test retrieving an existing session."""
    # Setup mocks
    session_id = uuid4()
    mock_sessions = mock_mongo_client['sessions']
    mock_messages = mock_mongo_client['messages']
    
    # Mock session document
    session_doc = {
        '_id': str(session_id),
        'turn_count': 2,
        'active': True,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'metadata': {'key': 'value'},
    }
    mock_sessions.find_one.return_value = session_doc
    
    # Mock messages
    message_id = uuid4()
    message_doc = {
        '_id': str(message_id),
        'session_id': str(session_id),
        'role': 'user',
        'content': 'Hello',
        'timestamp': datetime.utcnow(),
        'metadata': {},
        'is_agent_note': False,
    }
    mock_messages.find.return_value.sort.return_value = [message_doc]
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Get session
    state = await store.get_session(session_id)
    
    # Assertions
    assert state is not None
    assert state.session_id == session_id
    assert state.turn_count == 2
    assert state.active is True
    assert len(state.messages) == 1
    assert state.messages[0].content == 'Hello'
    mock_sessions.find_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_not_found(mock_mongo_client):
    """Test retrieving a non-existent session."""
    # Setup mock
    mock_sessions = mock_mongo_client['sessions']
    mock_sessions.find_one.return_value = None
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Get session
    session_id = uuid4()
    state = await store.get_session(session_id)
    
    # Assertions
    assert state is None


@pytest.mark.asyncio
async def test_get_session_with_agent_notes(mock_mongo_client):
    """Test retrieving session with agent notes."""
    # Setup mocks
    session_id = uuid4()
    mock_sessions = mock_mongo_client['sessions']
    mock_messages = mock_mongo_client['messages']
    
    # Mock session document
    session_doc = {
        '_id': str(session_id),
        'turn_count': 1,
        'active': True,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'metadata': {},
    }
    mock_sessions.find_one.return_value = session_doc
    
    # Mock agent note
    note_id = uuid4()
    note_doc = {
        '_id': str(note_id),
        'session_id': str(session_id),
        'agent_type': 'reasoning',
        'note_type': 'intent',
        'content': 'greeting',
        'timestamp': datetime.utcnow(),
        'metadata': {},
        'is_agent_note': True,
    }
    mock_messages.find.return_value.sort.return_value = [note_doc]
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Get session
    state = await store.get_session(session_id)
    
    # Assertions
    assert state is not None
    assert len(state.agent_notes) == 1
    assert state.agent_notes[0].content == 'greeting'
    assert state.agent_notes[0].note_type == 'intent'


@pytest.mark.asyncio
async def test_update_session(mock_mongo_client):
    """Test updating an existing session."""
    # Setup mocks
    session_id = uuid4()
    mock_sessions = mock_mongo_client['sessions']
    mock_messages = mock_mongo_client['messages']
    
    # Mock successful update
    mock_result = MagicMock()
    mock_result.matched_count = 1
    mock_sessions.update_one.return_value = mock_result
    
    # Mock find for existing messages
    mock_messages.find.return_value = []
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Create state with messages
    state = ConversationState(
        session_id=session_id,
        messages=[],
        agent_notes=[],
        turn_count=1,
        active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        metadata={'updated': True},
    )
    state.add_message(MessageRole.USER, "Test message")
    
    # Update session
    await store.update_session(state)
    
    # Assertions
    mock_sessions.update_one.assert_called_once()
    mock_messages.insert_many.assert_called_once()


@pytest.mark.asyncio
async def test_update_session_not_found(mock_mongo_client):
    """Test updating a non-existent session raises error."""
    # Setup mock
    mock_sessions = mock_mongo_client['sessions']
    mock_result = MagicMock()
    mock_result.matched_count = 0
    mock_sessions.update_one.return_value = mock_result
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Create state
    state = ConversationState(
        session_id=uuid4(),
        messages=[],
        agent_notes=[],
        turn_count=1,
        active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        metadata={},
    )
    
    # Update session should raise error
    with pytest.raises(ValueError, match="Session .* not found"):
        await store.update_session(state)


@pytest.mark.asyncio
async def test_delete_session(mock_mongo_client):
    """Test deleting a session."""
    # Setup mocks
    session_id = uuid4()
    mock_sessions = mock_mongo_client['sessions']
    mock_messages = mock_mongo_client['messages']
    
    # Mock successful deletion
    mock_result = MagicMock()
    mock_result.deleted_count = 1
    mock_sessions.delete_one.return_value = mock_result
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Delete session
    deleted = await store.delete_session(session_id)
    
    # Assertions
    assert deleted is True
    mock_messages.delete_many.assert_called_once()
    mock_sessions.delete_one.assert_called_once()


@pytest.mark.asyncio
async def test_delete_session_not_found(mock_mongo_client):
    """Test deleting a non-existent session."""
    # Setup mock
    mock_sessions = mock_mongo_client['sessions']
    mock_result = MagicMock()
    mock_result.deleted_count = 0
    mock_sessions.delete_one.return_value = mock_result
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Delete session
    session_id = uuid4()
    deleted = await store.delete_session(session_id)
    
    # Assertions
    assert deleted is False


@pytest.mark.asyncio
async def test_list_sessions_active_only(mock_mongo_client):
    """Test listing only active sessions."""
    # Setup mocks
    mock_sessions = mock_mongo_client['sessions']
    mock_messages = mock_mongo_client['messages']
    
    # Mock session documents
    session1_id = uuid4()
    session2_id = uuid4()
    session_docs = [
        {
            '_id': str(session1_id),
            'turn_count': 1,
            'active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'metadata': {},
        },
        {
            '_id': str(session2_id),
            'turn_count': 2,
            'active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'metadata': {},
        },
    ]
    mock_sessions.find.return_value.sort.return_value = session_docs
    
    # Mock find_one to return session docs when called
    def find_one_side_effect(query):
        session_id = query['_id']
        for doc in session_docs:
            if doc['_id'] == session_id:
                return doc
        return None
    
    mock_sessions.find_one.side_effect = find_one_side_effect
    
    # Mock messages (empty for simplicity)
    mock_messages.find.return_value.sort.return_value = []
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # List sessions
    states = await store.list_sessions(active_only=True)
    
    # Assertions
    assert len(states) == 2
    mock_sessions.find.assert_called_once()


@pytest.mark.asyncio
async def test_list_sessions_all(mock_mongo_client):
    """Test listing all sessions including inactive."""
    # Setup mocks
    mock_sessions = mock_mongo_client['sessions']
    mock_messages = mock_mongo_client['messages']
    
    # Mock session documents
    session_id = uuid4()
    session_docs = [
        {
            '_id': str(session_id),
            'turn_count': 1,
            'active': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'metadata': {},
        },
    ]
    mock_sessions.find.return_value.sort.return_value = session_docs
    
    # Mock find_one to return session doc
    mock_sessions.find_one.return_value = session_docs[0]
    
    # Mock messages
    mock_messages.find.return_value.sort.return_value = []
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # List sessions
    states = await store.list_sessions(active_only=False)
    
    # Assertions
    assert len(states) == 1
    # Verify query was called with empty dict (no active filter)
    call_args = mock_sessions.find.call_args[0]
    assert call_args[0] == {}


def test_create_indexes(mock_mongo_client):
    """Test TTL index creation."""
    # Setup mocks
    mock_sessions = mock_mongo_client['sessions']
    mock_messages = mock_mongo_client['messages']
    mock_transcripts = mock_mongo_client['transcripts']
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Create indexes
    store.create_indexes()
    
    # Assertions - verify indexes were created
    assert mock_sessions.create_index.call_count >= 2
    assert mock_messages.create_index.call_count >= 3
    assert mock_transcripts.create_index.call_count >= 2


def test_health_check_success(mock_mongo_client):
    """Test successful health check."""
    # Setup mock
    mock_client = mock_mongo_client['client'].return_value
    mock_client.admin.command.return_value = {'ok': 1}
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Health check
    result = store.health_check()
    
    # Assertions
    assert result is True
    mock_client.admin.command.assert_called_once_with('ping')


def test_health_check_failure(mock_mongo_client):
    """Test failed health check."""
    # Setup mock
    mock_client = mock_mongo_client['client'].return_value
    mock_client.admin.command.side_effect = ConnectionFailure("Connection failed")
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Health check
    result = store.health_check()
    
    # Assertions
    assert result is False


def test_get_connection_info_success(mock_mongo_client):
    """Test getting connection info."""
    # Setup mock
    mock_client = mock_mongo_client['client'].return_value
    mock_client.server_info.return_value = {'version': '5.0.0'}
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Get connection info
    info = store.get_connection_info()
    
    # Assertions
    assert info['database'] == 'test_db'
    assert info['version'] == '5.0.0'
    assert info['connected'] is True


def test_get_connection_info_failure(mock_mongo_client):
    """Test getting connection info when connection fails."""
    # Setup mock
    mock_client = mock_mongo_client['client'].return_value
    mock_client.server_info.side_effect = Exception("Connection error")
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Get connection info
    info = store.get_connection_info()
    
    # Assertions
    assert info['database'] == 'test_db'
    assert info['connected'] is False
    assert 'error' in info


@pytest.mark.asyncio
async def test_create_session_connection_error(mock_mongo_client):
    """Test handling connection errors during session creation."""
    # Setup mock
    mock_sessions = mock_mongo_client['sessions']
    mock_sessions.insert_one.side_effect = PyMongoError("Connection error")
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Create session should raise error
    with pytest.raises(PyMongoError):
        await store.create_session()


@pytest.mark.asyncio
async def test_get_session_connection_error(mock_mongo_client):
    """Test handling connection errors during session retrieval."""
    # Setup mock
    mock_sessions = mock_mongo_client['sessions']
    mock_sessions.find_one.side_effect = PyMongoError("Connection error")
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Get session should raise error
    with pytest.raises(PyMongoError):
        await store.get_session(uuid4())


def test_close(mock_mongo_client):
    """Test closing MongoDB connections."""
    # Setup mock
    mock_client = mock_mongo_client['client'].return_value
    
    # Create store
    store = MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    )
    
    # Close
    store.close()
    
    # Assertions
    mock_client.close.assert_called_once()


def test_context_manager(mock_mongo_client):
    """Test using store as context manager."""
    # Setup mock
    mock_client = mock_mongo_client['client'].return_value
    
    # Use as context manager
    with MongoDBConversationStore(
        connection_string="mongodb://localhost:27017",
        database_name="test_db"
    ) as store:
        assert store is not None
    
    # Assertions - close should be called on exit
    mock_client.close.assert_called_once()
