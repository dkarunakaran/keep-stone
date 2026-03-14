import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from sqlalchemy.orm import sessionmaker
import sys

# Path setup
parent_dir = ".."
sys.path.append(parent_dir)
sys.path.append("/app")
from models.base import engine
import models.artifact

Session = sessionmaker(bind=engine)
Artifact = models.artifact.Artifact

# Set your OpenAI API key from environment variable
if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("OPENAI_API_KEY environment variable is not set")


class ChromaDbClient:
    def __init__(self):
        # Initialize OpenAI embeddings
        self.embeddings = OpenAIEmbeddings()
        # Create the Chroma vector store and persist it to disk
        persist_directory = "/app/db/"
        # Create a Chroma vector store (in-memory for this example, use persist_directory for persistence)
        self.vector_store = Chroma(
            collection_name="keepstone_collection",
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
        )

    def add_artifact(self, artifact: Artifact):
        """
        Add an existing artifact to the vector store by fetching it from the database.

        Args:
            artifact (Artifact): The artifact to fetch and add

        Returns:
            bool: True if artifact was successfully added, False otherwise
        """
        try:
            # Create a Document with artifact content and metadata
            doc = Document(
                page_content=artifact.content,
                metadata={
                    "artifact_id": str(artifact.id),
                    "artifact_name": artifact.name,
                    "artifact_type": artifact.type_name,
                    "project_id": (
                        str(artifact.project_id) if artifact.project_id else None
                    ),
                    "created_at": (
                        artifact.created_at.isoformat() if artifact.created_at else None
                    ),
                },
            )

            # Add document to the vector store
            self.vector_store.add_documents([doc], ids=[str(artifact.id)])

            print(f"Successfully added artifact {artifact.id} to vector store")
            return True

        except ValueError as e:
            print(f"Validation error adding artifact {artifact.id}: {str(e)}")
            return False
        except AttributeError as e:
            print(f"Attribute error adding artifact {artifact.id}: {str(e)}")
            return False

    def update_artifact(self, artifact: Artifact):
        """
        Update an existing artifact in the vector store.

        Args:
            artifact (Artifact): The artifact to update
        Returns:
            bool: True if artifact was successfully updated, False otherwise
        """
        updated_doc = Document(
            page_content=artifact.content,
            metadata={
                "artifact_id": str(artifact.id),
                "artifact_name": artifact.name,
                "artifact_type": artifact.type_name,
                "project_id": (
                    str(artifact.project_id) if artifact.project_id else None
                ),
                "created_at": (
                    artifact.created_at.isoformat() if artifact.created_at else None
                ),
            },
        )
        self.vector_store.update_document(
            document_id=str(artifact.id), document=updated_doc
        )

        print(f"Successfully updated artifact {artifact.id} in vector store")
        return True

    def delete_artifact(self, id: int):
        """
        Delete an artifact from the vector store.

        Args:
            id (int): The ID of the artifact to delete
        Returns:
            bool: True if artifact was successfully deleted, False otherwise
        """
        try:
            self.vector_store.delete(ids=[str(id)])
            print(f"Successfully deleted artifact {id} from vector store")
            return True
        except Exception as e:
            print(f"Error deleting artifact {id}: {str(e)}")
            return False

    def query(self, query: str, k: int = 5):
        """
        Perform a similarity search on the vector store.

        Args:
            query (str): The search query string
            k (int): Number of results to return (default: 5)

        Returns:
            list: List of tuples containing (artifact_id, relevance_score, document)
        """
        try:
            # Perform the similarity search with scores
            relevant_docs = self.vector_store.similarity_search_with_score(query, k=k)

            results = []
            for doc, score in relevant_docs:
                artifact_id = doc.metadata.get("artifact_id")
                results.append(
                    {
                        "artifact_id": int(artifact_id) if artifact_id else None,
                        "score": score,
                        "document": doc,
                        "metadata": doc.metadata,
                    }
                )

            return results
        except ValueError as e:
            print(f"Validation error in similarity search: {str(e)}")
            return []
        except AttributeError as e:
            print(f"Attribute error in similarity search: {str(e)}")
            return []

    def similarity_search(
        self, query: str, k: int = 5, accessible_artifact_ids: list = None
    ):
        """
        Perform a similarity search and filter by accessible artifacts.

        Args:
            query (str): The search query string
            k (int): Number of results to return (default: 5)
            accessible_artifact_ids (list): List of artifact IDs the user has access to

        Returns:
            list: List of artifact IDs matching the query, filtered by accessibility
        """
        try:
            # Perform similarity search
            search_results = self.query(
                query, k=k * 2
            )  # Get more results to account for filtering

            artifact_ids = []
            for result in search_results:
                result_artifact_id = result.get("artifact_id")

                # Filter by accessible artifacts if provided
                if accessible_artifact_ids is not None:
                    if result_artifact_id in accessible_artifact_ids:
                        artifact_ids.append(result_artifact_id)
                else:
                    artifact_ids.append(result_artifact_id)

                # Stop when we have enough results
                if len(artifact_ids) >= k:
                    break

            return artifact_ids
        except ValueError as e:
            print(f"Validation error in filtered similarity search: {str(e)}")
            return []
        except AttributeError as e:
            print(f"Attribute error in filtered similarity search: {str(e)}")
            return []

    def add_all_artifacts(self):
        session = Session()
        try:
            artifacts = session.query(Artifact).filter(Artifact.deleted == False).all()
            for artifact in artifacts:
                self.add_artifact(artifact)
        finally:
            session.close()


if __name__ == "__main__":
    session = Session()
    artifact_id = 65
    # Fetch the artifact from the database
    artifact = (
        session.query(Artifact)
        .filter(Artifact.id == artifact_id, Artifact.deleted == False)
        .first()
    )
    chroma_client = ChromaDbClient()
    # success = chroma_client.add_artifact(artifact)

    # chroma_client.query("Semantic")
    # chroma_client.update_artifact(artifact)
    # chroma_client.delete_artifact(artifact.id)
    chroma_client.add_all_artifacts()