import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from ..config import settings

@dataclass
class ChunkMessage:
    message_id: str
    sender: str
    content: str
    timestamp: datetime

@dataclass
class ConversationChunk:
    chunk_index: int
    messages: List[ChunkMessage]
    chunk_text: str
    metadata: Dict[str, Any]
    estimated_tokens: int

class ConversationChunker:
    def __init__(
        self,
        max_chunk_size: int = settings.MAX_CHUNK_SIZE,
        min_chunk_size: int = settings.MIN_CHUNK_SIZE,
        time_window_minutes: int = settings.TIME_WINDOW_MINUTES
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.time_window = timedelta(minutes=time_window_minutes)

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4

    def should_break_chunk(
        self, 
        current_chunk: List[ChunkMessage], 
        new_message: ChunkMessage
    ) -> bool:
        """Determine if we should start a new chunk"""
        if not current_chunk:
            return False

        # Get current chunk text
        current_text = self._format_messages_to_text(current_chunk)
        new_text = f"{current_text}\n{new_message.sender}: {new_message.content}"
        
        # Check token limit
        if self.estimate_tokens(new_text) > self.max_chunk_size:
            return True

        # Check time gap
        last_message = current_chunk[-1]
        time_diff = new_message.timestamp - last_message.timestamp
        if time_diff > self.time_window:
            return True

        # Check speaker transition after significant gap (more than 1 hour)
        if (time_diff > timedelta(hours=1) and 
            new_message.sender != last_message.sender):
            return True

        return False

    def _format_messages_to_text(self, messages: List[ChunkMessage]) -> str:
        """Convert messages to formatted text"""
        lines = []
        current_speaker = None
        speaker_messages = []

        for msg in messages:
            if msg.sender != current_speaker:
                # Flush previous speaker's messages
                if speaker_messages:
                    content = " ".join(speaker_messages)
                    lines.append(f"{current_speaker}: {content}")
                    speaker_messages = []
                current_speaker = msg.sender
            
            speaker_messages.append(msg.content)

        # Flush last speaker's messages
        if speaker_messages:
            content = " ".join(speaker_messages)
            lines.append(f"{current_speaker}: {content}")

        return "\n".join(lines)

    def _create_chunk_metadata(self, messages: List[ChunkMessage]) -> Dict[str, Any]:
        """Create metadata for a chunk"""
        if not messages:
            return {}

        start_time = messages[0].timestamp
        end_time = messages[-1].timestamp
        speakers = list(set(msg.sender for msg in messages if msg.sender))
        message_ids = [msg.message_id for msg in messages]

        return {
            "start_timestamp": start_time.isoformat(),
            "end_timestamp": end_time.isoformat(),
            "speakers": speakers,
            "message_count": len(messages),
            "message_ids": message_ids,
            "time_span_minutes": int((end_time - start_time).total_seconds() / 60),
        }

    def chunk_messages(self, messages: List[ChunkMessage]) -> List[ConversationChunk]:
        """Main chunking function"""
        if not messages:
            return []
        print("messages: ", messages)
        # Sort messages by timestamp
        messages.sort(key=lambda x: x.timestamp)

        chunks = []
        current_chunk = []
        chunk_index = 0

        for message in messages:
            # Check if we should start a new chunk
            if self.should_break_chunk(current_chunk, message):
                # Finalize current chunk if it meets minimum size
                if current_chunk:
                    chunk_text = self._format_messages_to_text(current_chunk)
                    if self.estimate_tokens(chunk_text) >= self.min_chunk_size:
                        chunks.append(ConversationChunk(
                            chunk_index=chunk_index,
                            messages=current_chunk.copy(),
                            chunk_text=chunk_text,
                            metadata=self._create_chunk_metadata(current_chunk),
                            estimated_tokens=self.estimate_tokens(chunk_text)
                        ))
                        chunk_index += 1
                    else:
                        # If chunk is too small, merge with next chunk
                        # We'll handle this by not incrementing chunk_index
                        pass

                # Start new chunk
                current_chunk = [message]
            else:
                current_chunk.append(message)

        # Handle final chunk
        if current_chunk:
            chunk_text = self._format_messages_to_text(current_chunk)
            # Always include the last chunk, even if it's small
            chunks.append(ConversationChunk(
                chunk_index=chunk_index,
                messages=current_chunk,
                chunk_text=chunk_text,
                metadata=self._create_chunk_metadata(current_chunk),
                estimated_tokens=self.estimate_tokens(chunk_text)
            ))
        print("chunks: ",chunks)
        return chunks

def chunk_chat_messages(db_messages) -> List[ConversationChunk]:
    """Convert database messages to chunks"""
    # Convert DB messages to ChunkMessage objects
    chunk_messages = []
    for msg in db_messages:
        chunk_messages.append(ChunkMessage(
            message_id=msg.id,
            sender=msg.sender or "Unknown",
            content=msg.content,
            timestamp=msg.timestamp
        ))
    # Create chunker and process
    chunker = ConversationChunker()
    return chunker.chunk_messages(chunk_messages)