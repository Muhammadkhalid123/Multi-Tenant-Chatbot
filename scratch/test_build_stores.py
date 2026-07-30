import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock pymongo globally before importing build_vector_stores
import pymongo
mock_db = MagicMock()
mock_client = MagicMock()
mock_client.get_default_database.return_value = mock_db
pymongo.MongoClient = MagicMock(return_value=mock_client)

# Mock fastembed embeddings
import langchain_community.embeddings.fastembed
mock_embeddings = MagicMock()
mock_embeddings.embed_documents.return_value = [[0.1] * 384]
langchain_community.embeddings.fastembed.FastEmbedEmbeddings = MagicMock(return_value=mock_embeddings)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_vector_stores

class TestBuildVectorStores(unittest.TestCase):
    @patch('os.path.exists')
    @patch('glob.glob')
    @patch('build_vector_stores.TextLoader')
    def test_build_vector_store(self, mock_loader, mock_glob, mock_exists):
        # Mock paths
        mock_exists.return_value = True
        mock_glob.return_value = ["data/brands/test_bot/doc1.md"]
        
        # Mock document loading
        mock_doc = MagicMock()
        mock_doc.page_content = "This is a document about testing."
        mock_doc.metadata = {}
        
        mock_loader_instance = MagicMock()
        mock_loader_instance.load.return_value = [mock_doc]
        mock_loader.return_value = mock_loader_instance
        
        # Mock chunks collection
        build_vector_stores.chunks_col = MagicMock()
        
        # Run build
        result = build_vector_stores.build_vector_store("test_bot")
        
        self.assertTrue(result)
        
        # Verify text loader and splitter split the text
        mock_loader_instance.load.assert_called_once()
        
        # Verify embed_documents called
        mock_embeddings.embed_documents.assert_called_once()
        
        # Verify mongo database calls
        build_vector_stores.chunks_col.delete_many.assert_called()
        build_vector_stores.chunks_col.insert_many.assert_called_once()
        
        inserted_docs = build_vector_stores.chunks_col.insert_many.call_args[0][0]
        self.assertEqual(len(inserted_docs), 1)
        self.assertEqual(inserted_docs[0]["bot_id"], "test_bot")
        self.assertEqual(inserted_docs[0]["text"], "This is a document about testing.")
        self.assertEqual(inserted_docs[0]["embedding"], [0.1] * 384)
        self.assertEqual(inserted_docs[0]["source"], "doc1.md")

if __name__ == '__main__':
    unittest.main()
