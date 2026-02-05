# Privacy Implementation Guide
**Step-by-Step Code Examples for RelivChats**

---

## Quick Start: Critical 4 (Do These First)

### 1. Add Encryption at Rest (Core Implementation)

#### Step 1.1: Install Dependencies
```bash
pip install cryptography python-dotenv
```

#### Step 1.2: Create Encryption Utility
**File:** `src/security/encryption.py` (NEW FILE)

```python
"""
Field-level encryption for sensitive data
Uses Fernet symmetric encryption (AES-128)
"""

from cryptography.fernet import Fernet
from sqlalchemy import TypeDecorator, Text, LargeBinary
from typing import Optional
import base64
import os

class EncryptionManager:
    """Manages encryption keys and operations"""

    def __init__(self):
        # Load key from environment (DO NOT HARDCODE)
        key_b64 = os.getenv("ENCRYPTION_KEY")

        if not key_b64:
            raise ValueError(
                "ENCRYPTION_KEY not found in environment. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            key = key_b64.encode() if isinstance(key_b64, str) else key_b64
            self.cipher = Fernet(key)
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_KEY format: {e}")

    def encrypt(self, plaintext: str) -> str:
        """Encrypt string to base64-encoded ciphertext"""
        if not plaintext:
            return plaintext

        encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext to string"""
        if not ciphertext:
            return ciphertext

        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            # Log error but don't expose details
            print(f"Decryption failed: {type(e).__name__}")
            raise ValueError("Failed to decrypt data")


# Global instance
_encryption_manager: Optional[EncryptionManager] = None

def get_encryption_manager() -> EncryptionManager:
    """Get or create encryption manager singleton"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


class EncryptedString(TypeDecorator):
    """SQLAlchemy custom type for encrypted string columns"""

    impl = Text
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encryption_manager = get_encryption_manager()

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt before storing in database"""
        if value is not None:
            return self.encryption_manager.encrypt(value)
        return value

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt when retrieving from database"""
        if value is not None:
            return self.encryption_manager.decrypt(value)
        return value


class EncryptedText(EncryptedString):
    """Same as EncryptedString, for semantic clarity"""
    pass
```

#### Step 1.3: Update Models to Use Encryption
**File:** `src/chats/models.py` (MODIFY)

```python
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Text, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from ..database import Base
from ..security.encryption import EncryptedString, EncryptedText  # ADD THIS
import uuid

class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    # ENCRYPT THESE FIELDS ↓
    title = Column(EncryptedString(500), nullable=True)  # Changed from String
    participants = Column(EncryptedText, nullable=True)  # Changed from Text
    partner_name = Column(EncryptedString(200), nullable=True)  # Changed from String
    user_display_name = Column(EncryptedString(200), nullable=True)  # Changed from String

    chat_metadata = Column(JSON, nullable=True)  # Keep as-is (already aggregated)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    status = Column(String, default="processing")
    error_log = Column(Text, nullable=True)
    platform = Column(String, default="whatsapp", nullable=False)
    is_group_chat = Column(Boolean, default=False, nullable=False)
    participant_count = Column(Integer, nullable=True)

    # Vector-related fields
    vector_status = Column(String, default="pending")
    indexed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    chunk_count = Column(Integer, default=0)

    # Soft delete fields
    is_deleted = Column(Boolean, default=False, nullable=False, server_default='false')
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Privacy fields (ADD THESE - migration needed)
    retention_days = Column(Integer, default=90)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_accessed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    auto_delete_enabled = Column(Boolean, default=True)

    category_id = Column(UUID(as_uuid=True), ForeignKey("analysis_categories.id", ondelete="SET NULL"), nullable=True)

    # ... rest of fields unchanged ...

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="chat", cascade="all, delete-orphan")
    # ... other relationships ...


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)

    # ENCRYPT THESE FIELDS ↓
    sender = Column(EncryptedString(200), nullable=True)  # Changed from String
    content = Column(EncryptedText, nullable=False)  # Changed from Text - THIS IS CRITICAL

    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)

    chat = relationship("Chat", back_populates="messages")
```

#### Step 1.4: Generate and Store Encryption Key

```bash
# Generate key (run this ONCE)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Output example: gAAAAABhX... (44 characters)

# Add to .env file:
echo "ENCRYPTION_KEY=<generated_key_here>" >> .env
```

**CRITICAL: Key Management Best Practices**

1. **Development (.env file):**
   ```bash
   ENCRYPTION_KEY=your_dev_key_here
   ```

2. **Production (Use AWS Secrets Manager):**
   ```python
   # src/security/encryption.py - modify __init__
   import boto3
   from botocore.exceptions import ClientError

   def get_encryption_key():
       """Get encryption key from AWS Secrets Manager"""
       if os.getenv("ENVIRONMENT") == "production":
           secret_name = "relivchats/encryption-key"
           region_name = "us-east-1"

           session = boto3.session.Session()
           client = session.client(
               service_name='secretsmanager',
               region_name=region_name
           )

           try:
               response = client.get_secret_value(SecretId=secret_name)
               return response['SecretString']
           except ClientError as e:
               raise Exception(f"Failed to retrieve encryption key: {e}")
       else:
           # Development/staging - use .env
           return os.getenv("ENCRYPTION_KEY")
   ```

3. **Key Rotation (Quarterly):**
   ```python
   # src/security/key_rotation.py
   from sqlalchemy.orm import Session
   from .encryption import EncryptionManager
   from ..chats.models import Message, Chat

   def rotate_encryption_key(db: Session, old_key: str, new_key: str):
       """Re-encrypt all data with new key"""
       old_cipher = EncryptionManager(old_key)
       new_cipher = EncryptionManager(new_key)

       # Rotate messages (batch process)
       BATCH_SIZE = 1000
       offset = 0

       while True:
           messages = db.query(Message).limit(BATCH_SIZE).offset(offset).all()
           if not messages:
               break

           for msg in messages:
               # Decrypt with old key, encrypt with new key
               plaintext = old_cipher.decrypt(msg.content)
               msg.content = new_cipher.encrypt(plaintext)

           db.commit()
           offset += BATCH_SIZE
           print(f"Rotated {offset} messages...")

       print("Key rotation complete!")
   ```

#### Step 1.5: Create Migration for Privacy Fields

```bash
# Create migration
alembic revision -m "add_encryption_and_privacy_fields"
```

**File:** `alembic/versions/XXXXX_add_encryption_and_privacy_fields.py`

```python
"""add encryption and privacy fields

Revision ID: xxxxx
Revises: previous_revision
Create Date: 2026-02-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'xxxxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add privacy fields to chats table
    op.add_column('chats', sa.Column('retention_days', sa.Integer(), nullable=True, server_default='90'))
    op.add_column('chats', sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('chats', sa.Column('last_accessed_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.func.now()))
    op.add_column('chats', sa.Column('auto_delete_enabled', sa.Boolean(), nullable=False, server_default='true'))

    # Note: Changing column types to encrypted requires data migration
    # This is handled separately in a data migration script


def downgrade() -> None:
    op.drop_column('chats', 'auto_delete_enabled')
    op.drop_column('chats', 'last_accessed_at')
    op.drop_column('chats', 'expires_at')
    op.drop_column('chats', 'retention_days')
```

#### Step 1.6: Data Migration Script (Encrypt Existing Data)

**File:** `scripts/encrypt_existing_data.py`

```python
"""
One-time script to encrypt existing plaintext data
RUN THIS AFTER deploying encryption code but BEFORE changing column types
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.security.encryption import get_encryption_manager
from src.chats.models import Chat, Message
from src.database import SessionLocal

def encrypt_existing_messages():
    """Encrypt all existing message content"""
    db = SessionLocal()
    encryption = get_encryption_manager()

    try:
        print("Starting message encryption...")

        # Get total count
        total = db.query(Message).count()
        print(f"Found {total} messages to encrypt")

        BATCH_SIZE = 1000
        encrypted_count = 0

        # Process in batches to avoid memory issues
        for offset in range(0, total, BATCH_SIZE):
            messages = db.query(Message).limit(BATCH_SIZE).offset(offset).all()

            for msg in messages:
                # Only encrypt if not already encrypted
                # (detect by trying to decrypt - will fail if plaintext)
                try:
                    encryption.decrypt(msg.content)
                    # Already encrypted, skip
                    continue
                except:
                    # Not encrypted, encrypt it
                    plaintext_content = msg.content
                    msg.content = encryption.encrypt(plaintext_content)

                    if msg.sender:
                        try:
                            encryption.decrypt(msg.sender)
                        except:
                            plaintext_sender = msg.sender
                            msg.sender = encryption.encrypt(plaintext_sender)

                    encrypted_count += 1

            db.commit()
            print(f"Encrypted {offset + len(messages)}/{total} messages...")

        print(f"✓ Encryption complete! Encrypted {encrypted_count} messages")

    except Exception as e:
        db.rollback()
        print(f"✗ Error during encryption: {e}")
        raise
    finally:
        db.close()


def encrypt_existing_chats():
    """Encrypt chat metadata (title, participants, etc.)"""
    db = SessionLocal()
    encryption = get_encryption_manager()

    try:
        print("Starting chat metadata encryption...")

        chats = db.query(Chat).all()
        print(f"Found {len(chats)} chats to encrypt")

        encrypted_count = 0

        for chat in chats:
            if chat.title:
                try:
                    encryption.decrypt(chat.title)
                except:
                    chat.title = encryption.encrypt(chat.title)
                    encrypted_count += 1

            if chat.participants:
                try:
                    encryption.decrypt(chat.participants)
                except:
                    chat.participants = encryption.encrypt(chat.participants)

            if chat.partner_name:
                try:
                    encryption.decrypt(chat.partner_name)
                except:
                    chat.partner_name = encryption.encrypt(chat.partner_name)

            if chat.user_display_name:
                try:
                    encryption.decrypt(chat.user_display_name)
                except:
                    chat.user_display_name = encryption.encrypt(chat.user_display_name)

        db.commit()
        print(f"✓ Chat encryption complete! Encrypted {encrypted_count} chats")

    except Exception as e:
        db.rollback()
        print(f"✗ Error during chat encryption: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("ENCRYPTION DATA MIGRATION")
    print("="*60)
    print()
    print("⚠️  WARNING: This will encrypt all existing data.")
    print("⚠️  Make sure you have:")
    print("   1. Created a database backup")
    print("   2. Set ENCRYPTION_KEY in .env")
    print("   3. Tested on a dev database first")
    print()

    confirm = input("Continue? (type 'YES' to proceed): ")

    if confirm != "YES":
        print("Aborted.")
        sys.exit(1)

    print()
    encrypt_existing_messages()
    print()
    encrypt_existing_chats()
    print()
    print("="*60)
    print("✓ ENCRYPTION COMPLETE")
    print("="*60)
```

**Run the migration:**
```bash
# 1. Backup database first!
pg_dump $DATABASE_URL > backup_before_encryption.sql

# 2. Run migration
python scripts/encrypt_existing_data.py

# 3. Verify encryption worked
python -c "
from src.database import SessionLocal
from src.chats.models import Message
db = SessionLocal()
msg = db.query(Message).first()
print('Sample encrypted content:', msg.content[:50])
db.close()
"
```

---

## 2. Privacy Policy & Terms (Legal Documents)

### Option A: Use Privacy Policy Generator

**Recommended Service: iubenda**

1. Go to https://www.iubenda.com/en/privacy-and-cookie-policy-generator
2. Fill in details:
   - Service name: RelivChats
   - Service type: Web application
   - Data collected: Chat files, email, payment info
   - Third parties: Google Gemini, Qdrant, Clerk, Razorpay/Stripe
   - Legal basis: Consent
   - User rights: Access, delete, export

3. Generate policy (costs ~$27/month)

### Option B: Free Template (Use at Your Own Risk)

**File:** `docs/PRIVACY_POLICY.md`

```markdown
# Privacy Policy

**Last Updated: February 4, 2026**

## 1. Introduction

RelivChats ("we", "our", "us") respects your privacy. This policy explains how we collect, use, and protect your personal data when you use our service.

## 2. Data We Collect

### 2.1 Data You Provide
- **Account Information**: Email address (via Clerk authentication)
- **Chat Files**: WhatsApp chat exports you upload
- **Payment Information**: Processed by Razorpay/Stripe (we don't store card details)

### 2.2 Automatically Collected Data
- **Usage Data**: IP address, device type, browser type
- **Log Data**: Error logs, performance metrics (via Sentry)

## 3. How We Use Your Data

We use your data to:
- Generate AI-powered relationship insights
- Process payments for credit purchases
- Improve our service quality
- Comply with legal obligations

**Legal Basis (GDPR):** Consent (Article 6.1.a)

## 4. Data Sharing & Third-Party Processing

We share your data with:

| Service | Purpose | Data Shared | Privacy Policy |
|---------|---------|-------------|----------------|
| Google Gemini API | AI insight generation | Chat content | [Link](https://ai.google.dev/gemini-api/terms) |
| Qdrant Cloud | Vector storage | Chat embeddings | [Link](https://qdrant.tech/legal/privacy-policy/) |
| Clerk | Authentication | Email | [Link](https://clerk.com/legal/privacy) |
| Razorpay/Stripe | Payment processing | Payment details | [Razorpay](https://razorpay.com/privacy/) [Stripe](https://stripe.com/privacy) |
| Sentry | Error monitoring | Error logs | [Link](https://sentry.io/privacy/) |

**Data Processing Agreements:** We have DPAs in place with all sub-processors.

**International Transfers:** Your data may be processed in the United States (Google Gemini). We use Standard Contractual Clauses (SCCs) to ensure adequate protection.

## 5. Data Security

- **Encryption at Rest:** All chat content encrypted using AES-256
- **Encryption in Transit:** HTTPS/TLS 1.3
- **Access Controls:** Role-based access, audit logging
- **Regular Audits:** Quarterly security reviews

## 6. Data Retention

- **Active Chats:** Retained until you delete them
- **Auto-Deletion:** Chats automatically deleted after 90 days of inactivity (configurable)
- **Deleted Data:** Permanently removed within 30 days
- **Backups:** Encrypted backups retained for 90 days

## 7. Your Privacy Rights

Under GDPR and CCPA, you have the right to:

- **Access:** Request a copy of your data ([Export My Data])
- **Rectification:** Correct inaccurate data
- **Erasure:** Delete your data ([Delete My Account])
- **Portability:** Receive data in machine-readable format (JSON)
- **Objection:** Object to certain processing
- **Withdraw Consent:** At any time

**To exercise rights:** Contact privacy@relivchats.com

**Response Time:** Within 30 days

## 8. Children's Privacy

RelivChats is not intended for users under 16. We do not knowingly collect data from children.

## 9. Cookies

We use essential cookies for:
- Authentication (Clerk session)
- Payment processing (Stripe/Razorpay)

**Analytics Cookies:** Only with your consent.

## 10. Data Breach Notification

If a breach occurs, we will:
1. Notify affected users within 72 hours
2. Report to supervisory authority (if required)
3. Provide remediation steps

## 11. Changes to This Policy

We may update this policy. Changes will be posted with a new "Last Updated" date.

**Material Changes:** We'll email you 30 days in advance.

## 12. Contact Us

**Email:** privacy@relivchats.com
**Address:** [Your Business Address]
**Data Protection Officer:** [DPO Name/Email]

**EU Representative:** [If applicable]
**UK Representative:** [If applicable]

## 13. Supervisory Authority

**EU Users:** You can lodge a complaint with your local data protection authority.
- **Ireland:** Data Protection Commission (dpc.ie)
- **Germany:** Bundesbeauftragter für Datenschutz (bfdi.bund.de)
- [List for your jurisdiction]

**California Users:** California Attorney General (oag.ca.gov)

---

**By using RelivChats, you agree to this Privacy Policy.**
```

### Terms of Service Template

**File:** `docs/TERMS_OF_SERVICE.md`

```markdown
# Terms of Service

**Last Updated: February 4, 2026**

## 1. Acceptance of Terms

By using RelivChats, you agree to these Terms of Service ("Terms").

## 2. Service Description

RelivChats analyzes WhatsApp chat files to generate AI-powered psychological insights.

## 3. Eligibility

- Must be 16+ years old
- Must have authority to accept these Terms
- Must not be prohibited from using the service

## 4. Account Registration

- You're responsible for account security
- One account per person
- Provide accurate information

## 5. Prohibited Uses

You may NOT:
- Upload chats without all participants' consent
- Use for harassment, stalking, or illegal purposes
- Reverse-engineer our service
- Share account credentials
- Violate others' privacy

## 6. Content Ownership

- **Your Data:** You own all uploaded chats
- **Insights:** You own generated insights
- **Our Service:** We own the platform, code, and algorithms

## 7. Licenses

**You grant us:** License to process your chats to provide the service.
**We grant you:** License to use the service for personal, non-commercial use.

## 8. Credits & Payments

- **Credits:** Non-refundable (except legal requirements)
- **Pricing:** Subject to change with 30 days' notice
- **Refunds:** Only if service materially fails

## 9. Disclaimer of Warranties

**THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES.**

Insights are for informational purposes only, not professional advice.

## 10. Limitation of Liability

**WE ARE NOT LIABLE FOR:**
- Relationship decisions based on insights
- Accuracy of AI-generated content
- Third-party service failures
- Data loss (maintain backups)

**Maximum Liability:** Amount you paid in last 12 months.

## 11. Indemnification

You indemnify us against claims arising from your misuse of the service.

## 12. Termination

We may suspend/terminate accounts for:
- Terms violations
- Fraudulent activity
- Legal requirements

## 13. Governing Law

**Jurisdiction:** [Your Country/State]
**Arbitration:** Disputes resolved through binding arbitration.

## 14. Changes to Terms

We may update these Terms. Continued use = acceptance.

## 15. Contact

**Email:** legal@relivchats.com

---

**Last Reviewed:** February 4, 2026
```

---

## 3. Consent Management System

### Step 3.1: Database Schema

**File:** `src/users/models.py` (ADD THIS)

```python
class UserConsent(Base):
    __tablename__ = "user_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    consent_type = Column(String, nullable=False)
    # Consent types:
    # - 'privacy_policy_v1.0'
    # - 'terms_of_service_v1.0'
    # - 'ai_processing'
    # - 'third_party_storage'
    # - 'marketing_emails'

    consent_version = Column(String, nullable=False)  # 'v1.0', 'v1.1', etc.
    granted = Column(Boolean, default=False, nullable=False)

    granted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    withdrawn_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Audit trail
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    consent_text = Column(Text, nullable=True)  # Snapshot of what they agreed to

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="consents")

# Update User model
class User(Base):
    # ... existing fields ...

    consents = relationship("UserConsent", back_populates="user", cascade="all, delete-orphan")
```

### Step 3.2: Consent Service

**File:** `src/users/consent_service.py` (NEW FILE)

```python
"""
Consent management service
Handles user consent tracking and validation
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
from typing import List, Dict, Optional
from .models import UserConsent, User
from ..logging_config import get_logger

logger = get_logger(__name__)

# Define required consents
REQUIRED_CONSENTS = {
    'privacy_policy': 'v1.0',
    'terms_of_service': 'v1.0',
    'ai_processing': 'v1.0'
}

OPTIONAL_CONSENTS = {
    'marketing_emails': 'v1.0',
    'analytics': 'v1.0'
}


def record_consent(
    db: Session,
    user_id: str,
    consent_type: str,
    granted: bool,
    consent_version: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    consent_text: Optional[str] = None
) -> UserConsent:
    """Record user consent (or withdrawal)"""

    now = datetime.now(timezone.utc)

    # Check if consent already exists
    existing = db.query(UserConsent).filter(
        and_(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type,
            UserConsent.consent_version == consent_version
        )
    ).first()

    if existing:
        # Update existing consent
        existing.granted = granted
        if granted:
            existing.granted_at = now
            existing.withdrawn_at = None
        else:
            existing.withdrawn_at = now

        existing.ip_address = ip_address
        existing.user_agent = user_agent

        db.commit()
        db.refresh(existing)

        logger.info(
            f"Consent {'granted' if granted else 'withdrawn'}: {consent_type}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "consent_type": consent_type,
                    "granted": granted
                }
            }
        )

        return existing
    else:
        # Create new consent record
        consent = UserConsent(
            user_id=user_id,
            consent_type=consent_type,
            consent_version=consent_version,
            granted=granted,
            granted_at=now if granted else None,
            withdrawn_at=None if granted else now,
            ip_address=ip_address,
            user_agent=user_agent,
            consent_text=consent_text
        )

        db.add(consent)
        db.commit()
        db.refresh(consent)

        logger.info(
            f"New consent recorded: {consent_type}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "consent_type": consent_type,
                    "granted": granted
                }
            }
        )

        return consent


def has_valid_consent(db: Session, user_id: str, consent_type: str, consent_version: str) -> bool:
    """Check if user has valid consent for a specific type"""

    consent = db.query(UserConsent).filter(
        and_(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type,
            UserConsent.consent_version == consent_version,
            UserConsent.granted == True,
            UserConsent.withdrawn_at.is_(None)
        )
    ).first()

    return consent is not None


def check_required_consents(db: Session, user_id: str) -> Dict[str, bool]:
    """Check if user has all required consents"""

    results = {}

    for consent_type, version in REQUIRED_CONSENTS.items():
        results[consent_type] = has_valid_consent(db, user_id, consent_type, version)

    return results


def get_user_consents(db: Session, user_id: str) -> List[UserConsent]:
    """Get all consents for a user"""

    return db.query(UserConsent).filter(
        UserConsent.user_id == user_id
    ).order_by(UserConsent.created_at.desc()).all()


def withdraw_consent(db: Session, user_id: str, consent_type: str) -> bool:
    """Withdraw a consent"""

    consent = db.query(UserConsent).filter(
        and_(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type,
            UserConsent.granted == True
        )
    ).first()

    if consent:
        consent.granted = False
        consent.withdrawn_at = datetime.now(timezone.utc)
        db.commit()

        logger.warning(
            f"Consent withdrawn: {consent_type}",
            extra={"user_id": user_id}
        )

        return True

    return False
```

### Step 3.3: Update Chat Upload to Require Consent

**File:** `src/chats/router.py` (MODIFY upload endpoint)

```python
from ..users.consent_service import has_valid_consent, record_consent

@router.post("/upload", response_model=schemas.ChatResponse)
@limiter.limit(UPLOAD_LIMIT)
async def upload_chat(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category_id: Optional[str] = Form(None),
    # NEW: Consent parameters
    consent_ai_processing: bool = Form(...),  # Required
    consent_third_party: bool = Form(...),    # Required
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """Upload WhatsApp chat file with consent validation"""

    # STEP 1: Validate consents
    if not consent_ai_processing:
        raise HTTPException(
            status_code=400,
            detail="Consent for AI processing is required to use this service"
        )

    if not consent_third_party:
        raise HTTPException(
            status_code=400,
            detail="Consent for third-party storage is required to use this service"
        )

    # STEP 2: Record consents (use sync session for this)
    sync_db = SessionLocal()
    try:
        record_consent(
            db=sync_db,
            user_id=user_id,
            consent_type='ai_processing',
            granted=True,
            consent_version='v1.0',
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent')
        )

        record_consent(
            db=sync_db,
            user_id=user_id,
            consent_type='third_party_storage',
            granted=True,
            consent_version='v1.0',
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent')
        )
    finally:
        sync_db.close()

    # STEP 3: Continue with normal upload flow
    # ... rest of upload logic ...
```

---

## 4. HTTPS Enforcement

### Step 4.1: Force HTTPS in Production

**File:** `src/middleware.py` (ADD THIS)

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect all HTTP traffic to HTTPS in production"""

    async def dispatch(self, request: Request, call_next):
        # Only enforce in production
        if settings.ENVIRONMENT == "production":
            # Check if request is HTTP
            if request.url.scheme == "http":
                # Redirect to HTTPS
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(url), status_code=301)

        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.clerk.com https://clerk.relivchats.com"
        )

        return response
```

**File:** `src/main.py` (ADD MIDDLEWARE)

```python
from .middleware import HTTPSRedirectMiddleware, SecurityHeadersMiddleware

app = FastAPI(...)

# Add security middleware
app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
```

### Step 4.2: Configure Production Server (Nginx)

**File:** `/etc/nginx/sites-available/relivchats`

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.relivchats.com;

    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name api.relivchats.com;

    # SSL Certificate (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.relivchats.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.relivchats.com/privkey.pem;

    # SSL Configuration (Mozilla Modern)
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # File upload limit
    client_max_body_size 25M;
}
```

**Install SSL certificate:**
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.relivchats.com

# Auto-renewal (cron job)
sudo certbot renew --dry-run
```

---

## Testing the Implementation

### Test 1: Encryption Works

```python
# tests/test_encryption.py

from src.security.encryption import get_encryption_manager
from src.chats.models import Message
from src.database import SessionLocal

def test_message_encryption():
    """Test that messages are encrypted in database"""

    db = SessionLocal()
    encryption = get_encryption_manager()

    # Create test message
    test_content = "This is a secret message"
    msg = Message(
        chat_id="test-chat-id",
        sender="Alice",
        content=test_content,  # Will be auto-encrypted
        timestamp=datetime.now()
    )

    db.add(msg)
    db.commit()

    # Check database has encrypted version
    raw_query = db.execute(
        f"SELECT content FROM messages WHERE id = '{msg.id}'"
    ).first()

    assert raw_query[0] != test_content  # Should be encrypted
    assert len(raw_query[0]) > len(test_content)  # Encrypted is longer

    # Check ORM returns decrypted version
    db.refresh(msg)
    assert msg.content == test_content  # Should be decrypted

    print("✓ Encryption test passed!")

    db.close()
```

### Test 2: Consent Validation

```bash
# Manual test with curl
curl -X POST http://localhost:8000/api/chats/upload \
  -H "Authorization: Bearer $CLERK_TOKEN" \
  -F "file=@test_chat.txt" \
  -F "category_id=romantic" \
  -F "consent_ai_processing=false"  # Should FAIL

# Expected: 400 Bad Request "Consent for AI processing is required"
```

### Test 3: HTTPS Redirect

```bash
curl -I http://api.relivchats.com/health
# Expected: 301 Moved Permanently
# Location: https://api.relivchats.com/health
```

---

## Deployment Checklist

```
Pre-Launch Privacy Checklist
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL (Must-Have):
[ ] Privacy Policy published at /privacy
[ ] Terms of Service published at /terms
[ ] Encryption implemented and tested
[ ] HTTPS enforced (HTTP redirects to HTTPS)
[ ] Consent checkboxes at upload
[ ] Database backup created
[ ] ENCRYPTION_KEY stored in secrets manager (AWS/Vault)
[ ] All team members briefed on privacy policy

HIGH PRIORITY:
[ ] Data retention policy configured (90 days)
[ ] Auto-delete cron job scheduled
[ ] DPAs signed with Google, Qdrant
[ ] Data export endpoint tested
[ ] Deletion flow tested
[ ] Security headers added

MEDIUM PRIORITY:
[ ] Access audit logging enabled
[ ] Privacy dashboard created
[ ] Anonymization option available
[ ] Log PII scrubbing configured

POST-LAUNCH (30 days):
[ ] Privacy policy linked in footer
[ ] "Delete my data" button tested
[ ] Consent withdrawal flow tested
[ ] First data retention cleanup ran
[ ] Legal review completed
```

---

**Files Created:**
1. `src/security/encryption.py` - Encryption utilities
2. `src/users/consent_service.py` - Consent management
3. `scripts/encrypt_existing_data.py` - Migration script
4. `docs/PRIVACY_POLICY.md` - Privacy policy
5. `docs/TERMS_OF_SERVICE.md` - Terms of service

**Files Modified:**
1. `src/chats/models.py` - Add encrypted columns
2. `src/chats/router.py` - Add consent validation
3. `src/middleware.py` - Add HTTPS redirect
4. `src/main.py` - Add security middleware

**Total Implementation Time:** 3-5 days for one developer

**Next Steps:**
1. Review this guide with your team
2. Create database backup
3. Generate encryption key
4. Run migrations
5. Test on staging environment
6. Deploy to production

---

*Questions? Run the test suite first, then check logs!*
