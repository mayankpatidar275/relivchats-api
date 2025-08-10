import hashlib
import tempfile
import zipfile
import shutil
import os
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from fastapi import UploadFile

from app.db.session import get_db
from app.models.chat import Chat, Message, AIChatConversation, Insight
from app.models.user import User
from app.schemas.chat import ParsedMessageTemp, ChatCreate, MessageResponse, ChatResponse, ParticipantSelectionResponse, InsightResponse
from app.utils.whatsapp_parser import parse_whatsapp_chat
from app.services.qdrant_service import qdrant_service
from app.services.media_service import media_service
from app.core.config import settings # Import settings for constants
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ChatService:
    async def process_uploaded_file(self, file: UploadFile, user_id: str) -> Tuple[ParticipantSelectionResponse, str, Dict[str, bytes]]:
        """
        Processes an uploaded WhatsApp chat file (txt or zip).
        Extracts content, parses messages, and identifies participants.
        Returns data for frontend participant selection.
        Returns `raw_chat_text` and `media_files` to be held temporarily on backend for `create_chat`.
        """
        # Validate file size
        # Use file.size which is available after file has been read once (or check content length)
        # For initial upload, check headers or rely on explicit read
        file_content = await file.read() # Read once to get size and content
        if len(file_content) > settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024:
            raise ValueError(f"File size exceeds {settings.MAX_UPLOAD_FILE_SIZE_MB}MB limit.")

        file_name = file.filename
        raw_chat_text = ""
        media_files = {} # Dict to store media content: {filename_in_chat: bytes_content}

        # Create a temporary directory to extract zip contents
        temp_dir = None
        try:
            if file_name.endswith('.zip'):
                temp_dir = tempfile.mkdtemp()
                zip_path = os.path.join(temp_dir, file_name)
                
                # Write the uploaded content to a temporary zip file
                with open(zip_path, "wb") as f:
                    f.write(file_content)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                chat_txt_found = False
                for root, _, files in os.walk(temp_dir):
                    for f_name in files:
                        full_path = os.path.join(root, f_name)
                        if f_name.endswith('.txt') and 'chat' in f_name.lower() and os.path.getsize(full_path) > 0: # Heuristic
                            # Read the chat file
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                raw_chat_text = f.read()
                            chat_txt_found = True
                        else:
                            # Store media file contents by original filename
                            with open(full_path, 'rb') as f_media:
                                # Use relative path within the zip if needed for matching, for now just filename
                                media_files[f_name] = f_media.read()

                if not chat_txt_found:
                    raise ValueError("No WhatsApp chat (.txt) file found in the uploaded zip archive.")
            elif file_name.endswith('.txt'):
                raw_chat_text = file_content.decode('utf-8', errors='ignore')
            else:
                raise ValueError("Unsupported file type. Please upload a .txt or .zip file.")
        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file.")
        except Exception as e:
            logger.error(f"Error processing uploaded file: {e}", exc_info=True)
            raise ValueError(f"Failed to process file: {e}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir) # Clean up temporary directory

        if not raw_chat_text:
            raise ValueError("Could not extract chat text from the uploaded file.")

        parsed_messages_temp = parse_whatsapp_chat(raw_chat_text)
        if not parsed_messages_temp:
            raise ValueError("Failed to parse chat messages. Please ensure it's a valid WhatsApp chat export.")

        # Extract unique participants
        participants = list(set([msg.author for msg in parsed_messages_temp if msg.author]))
        participants.sort() # Sort for consistent display

        # Return data needed for frontend selection, and the parsed content for later saving
        return ParticipantSelectionResponse(
            file_name=file_name,
            participants=participants,
            message_count=len(parsed_messages_temp)
        ), raw_chat_text, media_files


    async def create_chat(
        self,
        db: AsyncSession,
        user_id: str,
        raw_chat_text: str,
        media_files: Dict[str, bytes],
        file_name: str,
        participants: List[str],
        me_identifier: str
    ) -> Chat:
        """
        Saves a new chat and its messages to the database, handles media, and indexes for AI.
        """
        # First, ensure user exists (or create a placeholder user)
        user_exists = await db.execute(select(User).where(User.id == user_id))
        user = user_exists.scalar_one_or_none()
        if not user:
            # Create a basic user entry if not found (assuming Clerk handles actual user creation via webhooks)
            user = User(id=user_id, email=f"{user_id}@relivchats.com") # Placeholder email
            db.add(user)
            await db.flush() # Ensure user_id is committed for FK

        parsed_messages_temp = parse_whatsapp_chat(raw_chat_text)

        if not parsed_messages_temp:
            raise ValueError("Failed to parse chat messages for saving. Raw text might be empty or invalid.")
        
        # Generate content hash for deduplication
        # Hash a representation of the chat: first 1000 chars of raw text + message count + sorted participant names
        chat_signature = f"{raw_chat_text[:1000]}{len(parsed_messages_temp)}{'_'.join(sorted(participants))}"
        content_hash = hashlib.sha256(chat_signature.encode('utf-8')).hexdigest()

        # Check for duplicate chat for this user
        existing_chat_query = await db.execute(
            select(Chat).where(and_(Chat.user_id == user_id, Chat.content_hash == content_hash))
        )
        if existing_chat_query.scalar_one_or_none():
            raise ValueError("This chat has already been imported by you.")
        
        # Check user chat limit
        chat_count_query = await db.execute(
            select(func.count(Chat.id)).where(Chat.user_id == user_id)
        )
        current_chat_count = chat_count_query.scalar_one()
        if current_chat_count >= settings.MAX_CHATS_PER_USER:
            raise ValueError(f"You have reached the limit of {settings.MAX_CHATS_PER_USER} imported chats. Please delete an existing chat to import a new one.")


        new_chat = Chat(
            user_id=user_id,
            name=file_name.replace(".txt", "").replace(".zip", ""), # Clean name from file name
            participants=participants,
            me_identifier=me_identifier,
            content_hash=content_hash
        )
        db.add(new_chat)
        await db.flush() # Flush to get new_chat.id, needed for message FK and S3 key

        db_messages = []
        for i, msg_temp in enumerate(parsed_messages_temp):
            attachment_url = None
            if msg_temp.attachment:
                # Use the attachment filename from the parser to look up in extracted media_files
                media_content = media_files.get(msg_temp.attachment)
                if media_content:
                    try:
                        # Pass message ID (or a unique identifier) for S3 key uniqueness
                        # For now, using (chat_id, i) as a composite temp ID.
                        attachment_url = await media_service.upload_media_file(
                            media_content, msg_temp.attachment, new_chat.id, i # Using index `i` as a temporary message ID
                        )
                        logger.info(f"Uploaded attachment '{msg_temp.attachment}' for message {i} in chat {new_chat.id}: {attachment_url}")
                    except Exception as e:
                        logger.error(f"Failed to upload media for {msg_temp.attachment} in chat {new_chat.id}: {e}")
                        # Continue without attachment_url if upload fails
                        attachment_url = None

            # Ensure date is timezone-aware
            dt_to_store = msg_temp.date.replace(tzinfo=timezone.utc) if msg_temp.date.tzinfo is None else msg_temp.date

            db_message = Message(
                chat_id=new_chat.id,
                date=dt_to_store,
                author=msg_temp.author,
                message_text=msg_temp.message,
                attachment_filename=msg_temp.attachment,
                attachment_url=attachment_url
            )
            db_messages.append(db_message)

        db.add_all(db_messages)
        await db.commit() # Commit chat and messages together
        await db.refresh(new_chat) # Refresh to get the latest state including auto-generated IDs

        # After successful DB commit, index messages in Qdrant
        # Important: Qdrant needs the *actual* message IDs from the database after commit
        messages_for_qdrant = [
            {
                "id": msg.id, # Use the actual DB message ID
                "chat_id": msg.chat_id,
                "author": msg.author,
                "date": msg.date,
                "message_text": msg.message_text,
                "attachment_filename": msg.attachment_filename,
                "attachment_url": msg.attachment_url
            }
            for msg in db_messages
        ]
        if messages_for_qdrant:
            qdrant_service.index_messages(messages_for_qdrant)

        # Trigger initial insights generation asynchronously (e.g., via a background task)
        # For a full system, you might enqueue a task here:
        # from app.tasks.insight_generation import generate_initial_insights
        # generate_initial_insights.delay(new_chat.id) # Assuming a task queue setup

        return new_chat

    async def get_user_chats(self, db: AsyncSession, user_id: str) -> List[ChatResponse]:
        """Retrieves all chats for a given user."""
        result = await db.execute(
            select(Chat).where(Chat.user_id == user_id).order_by(Chat.imported_at.desc())
        )
        chats = result.scalars().all()
        return [ChatResponse.model_validate(chat) for chat in chats]

    async def get_chat_messages(self, db: AsyncSession, chat_id: int, user_id: str) -> List[MessageResponse]:
        """Retrieves messages for a specific chat, ensuring user ownership."""
        chat_query = await db.execute(
            select(Chat).where(and_(Chat.id == chat_id, Chat.user_id == user_id))
        )
        chat = chat_query.scalar_one_or_none()
        if not chat:
            raise ValueError("Chat not found or you do not have access to it.")

        result = await db.execute(
            select(Message).where(Message.chat_id == chat_id).order_by(Message.date)
        )
        messages = result.scalars().all()
        return [MessageResponse.model_validate(msg) for msg in messages]

    async def get_chat_insights(self, db: AsyncSession, chat_id: int, user_id: str) -> List[InsightResponse]:
        """Retrieves insights for a specific chat, ensuring user ownership."""
        # Ensure the user owns the chat
        chat_check = await db.execute(
            select(Chat).where(and_(Chat.id == chat_id, Chat.user_id == user_id))
        )
        chat = chat_check.scalar_one_or_none()
        if not chat:
            raise ValueError("Chat not found or you do not have access to it.")

        result = await db.execute(
            select(Insight).where(Insight.chat_id == chat_id).order_by(Insight.generated_at.desc())
        )
        insights = result.scalars().all()
        return [InsightResponse.model_validate(insight) for insight in insights]

    async def delete_chat(self, db: AsyncSession, chat_id: int, user_id: str):
        """Deletes a chat and its associated data."""
        chat_to_delete = await db.execute(
            select(Chat).where(and_(Chat.id == chat_id, Chat.user_id == user_id))
        )
        chat = chat_to_delete.scalar_one_or_none()
        if not chat:
            raise ValueError("Chat not found or you do not have permission to delete it.")
        
        # SQLAlchemy handles cascade delete for related messages, AI conversations, and insights
        await db.delete(chat)
        await db.commit()
        logger.info(f"Chat {chat_id} deleted by user {user_id}.")

chat_service = ChatService()