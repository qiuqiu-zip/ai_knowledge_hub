from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter


class ChunkService:
    def __init__(self) -> None:
        self.splitter = SentenceSplitter(chunk_size=800, chunk_overlap=120)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)

    def split_text(self, text: str) -> list[dict]:
        chunks: list[str] = []
        try:
            docs = [Document(text=text)]
            nodes = self.splitter.get_nodes_from_documents(docs)
            chunks = [n.text.strip() for n in nodes if n.text and n.text.strip()]
        except Exception:  # noqa: BLE001
            chunks = [c.strip() for c in text.split("\n\n") if c.strip()]

        result = []
        for i, chunk in enumerate(chunks):
            result.append(
                {
                    "chunk_index": i,
                    "content": chunk,
                    "token_count": self.estimate_tokens(chunk),
                    "metadata": {},
                }
            )
        return result
