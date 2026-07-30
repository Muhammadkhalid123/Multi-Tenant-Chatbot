import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock pymongo globally before importing app.py
import pymongo
mock_db = MagicMock()
mock_client = MagicMock()
mock_client.get_default_database.return_value = mock_db
pymongo.MongoClient = MagicMock(return_value=mock_client)

# Add parent dir to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app

class TestAtlasLogic(unittest.TestCase):
    @patch('app.embed_query')
    def test_retrieve_context(self, mock_embed_query):
        # Mock embedding return value
        mock_embed_query.return_value = [0.1] * 384
        
        # Setup mock db chunks collection
        app._chunks_col = MagicMock()
        app._chunks_col.aggregate.return_value = [
            {"text": "this is chunk 1", "source": "s1"},
            {"text": "this is chunk 2", "source": "s2"}
        ]
        
        # Call retrieve_context
        context = app.retrieve_context("test_bot", "hello query", top_k=2)
        
        # Verify aggregate call structure
        app._chunks_col.aggregate.assert_called_once()
        pipeline = app._chunks_col.aggregate.call_args[0][0]
        
        self.assertEqual(len(pipeline), 2)
        self.assertIn("$vectorSearch", pipeline[0])
        vector_search = pipeline[0]["$vectorSearch"]
        self.assertEqual(vector_search["index"], "chunk_vector_index")
        self.assertEqual(vector_search["path"], "embedding")
        self.assertEqual(vector_search["queryVector"], [0.1] * 384)
        self.assertEqual(vector_search["limit"], 2)
        self.assertEqual(vector_search["filter"], {"bot_id": {"$eq": "test_bot"}})
        
        # Verify returned context
        self.assertEqual(context, "this is chunk 1\n\nthis is chunk 2")

    def test_store_chunks_to_mongo(self):
        app._chunks_col = MagicMock()
        
        texts = ["text A", "text B"]
        vectors = [[0.2] * 384, [0.3] * 384]
        
        app.store_chunks_to_mongo("bot_abc", texts, vectors, source="unittest")
        
        # Verify delete_many called for the bot_id
        app._chunks_col.delete_many.assert_called_once_with({"bot_id": "bot_abc"})
        
        # Verify insert_many called with the correct docs
        app._chunks_col.insert_many.assert_called_once()
        inserted_docs = app._chunks_col.insert_many.call_args[0][0]
        self.assertEqual(len(inserted_docs), 2)
        self.assertEqual(inserted_docs[0]["bot_id"], "bot_abc")
        self.assertEqual(inserted_docs[0]["text"], "text A")
        self.assertEqual(inserted_docs[0]["embedding"], [0.2] * 384)
        self.assertEqual(inserted_docs[0]["source"], "unittest")

if __name__ == '__main__':
    unittest.main()
