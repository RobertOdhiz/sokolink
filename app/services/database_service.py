"""
Database service for session management and data persistence.
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import uuid
import structlog

from app.config import get_settings
from app.models.webhook_models import SessionData
from app.models.response_models import ComplianceResponse

logger = structlog.get_logger()
settings = get_settings()

# Database setup
Base = declarative_base()


class UserSession(Base):
    """User session database model."""
    __tablename__ = "user_sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    phone_number = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    conversation_state = Column(String, default="active")
    context = Column(Text)  # JSON string
    message_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class ConversationHistory(Base):
    """Conversation history database model."""
    __tablename__ = "conversation_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True, nullable=False)
    phone_number = Column(String, index=True, nullable=False)
    message_type = Column(String, nullable=False)  # 'incoming' or 'outgoing'
    message_content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_metadata = Column(Text)  # JSON string for additional data


class ComplianceResponseDB(Base):
    """Compliance response database model."""
    __tablename__ = "compliance_responses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True, nullable=False)
    phone_number = Column(String, index=True, nullable=False)
    business_type = Column(String)
    business_scale = Column(String)
    location = Column(String)
    total_cost = Column(Integer)
    total_timeline_days = Column(Integer)
    response_data = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    confidence_score = Column(String)  # Store as string to avoid precision issues


class DatabaseService:
    """Database service for managing sessions and data."""
    
    def __init__(self):
        """Initialize database service."""
        self.engine = create_engine(settings.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        # Redis removed - using SQLite3 only
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        
        logger.info("Database service initialized", database_url=settings.database_url)
    
    def get_db_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def create_session(self, phone_number: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Create new user session.
        
        Args:
            phone_number: User's phone number
            context: Initial session context
            
        Returns:
            str: Session ID
        """
        session_id = str(uuid.uuid4())
        db_session = self.get_db_session()
        
        try:
            # Check for existing active session
            existing_session = db_session.query(UserSession).filter(
                UserSession.phone_number == phone_number,
                UserSession.is_active == True
            ).first()
            
            if existing_session:
                # Deactivate existing session
                existing_session.is_active = False
                existing_session.conversation_state = "replaced"
                db_session.commit()
                logger.info("Deactivated existing session", 
                           session_id=existing_session.session_id, 
                           phone_number=phone_number)
            
            # Create new session
            new_session = UserSession(
                session_id=session_id,
                phone_number=phone_number,
                context=json.dumps(context or {}),
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            
            db_session.add(new_session)
            db_session.commit()
            
            # Session stored in database
            
            logger.info("Created new session", session_id=session_id, phone_number=phone_number)
            return session_id
            
        except Exception as e:
            db_session.rollback()
            logger.error("Error creating session", error=str(e), phone_number=phone_number)
            raise
        finally:
            db_session.close()
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[SessionData]: Session data or None
        """
        db_session = self.get_db_session()
        try:
            session = db_session.query(UserSession).filter(
                UserSession.session_id == session_id,
                UserSession.is_active == True
            ).first()
            
            if session:
                session_data = SessionData(
                    session_id=session.session_id,
                    phone_number=session.phone_number,
                    created_at=session.created_at,
                    last_activity=session.last_activity,
                    conversation_state=session.conversation_state,
                    context=json.loads(session.context or "{}"),
                    message_count=session.message_count
                )
                
                return session_data
            
            return None
            
        except Exception as e:
            logger.error("Error getting session", error=str(e), session_id=session_id)
            return None
        finally:
            db_session.close()
    
    def get_active_session_by_phone(self, phone_number: str) -> Optional[SessionData]:
        """
        Get active session by phone number.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Optional[SessionData]: Session data or None
        """
        db_session = self.get_db_session()
        try:
            session = db_session.query(UserSession).filter(
                UserSession.phone_number == phone_number,
                UserSession.is_active == True
            ).order_by(UserSession.last_activity.desc()).first()
            
            if session:
                session_data = SessionData(
                    session_id=session.session_id,
                    phone_number=session.phone_number,
                    created_at=session.created_at,
                    last_activity=session.last_activity,
                    conversation_state=session.conversation_state,
                    context=json.loads(session.context or "{}"),
                    message_count=session.message_count
                )
                
                return session_data
            
            return None
            
        except Exception as e:
            logger.error("Error getting session by phone", error=str(e), phone_number=phone_number)
            return None
        finally:
            db_session.close()
    
    def update_session(self, session_id: str, context: Optional[Dict[str, Any]] = None, 
                      conversation_state: Optional[str] = None) -> bool:
        """
        Update session data.
        
        Args:
            session_id: Session ID
            context: Updated context
            conversation_state: Updated conversation state
            
        Returns:
            bool: True if updated successfully
        """
        db_session = self.get_db_session()
        try:
            session = db_session.query(UserSession).filter(
                UserSession.session_id == session_id,
                UserSession.is_active == True
            ).first()
            
            if session:
                if context is not None:
                    session.context = json.dumps(context)
                
                if conversation_state is not None:
                    session.conversation_state = conversation_state
                
                session.last_activity = datetime.utcnow()
                session.message_count += 1
                
                db_session.commit()
                
                logger.info("Updated session", session_id=session_id)
                return True
            
            return False
            
        except Exception as e:
            db_session.rollback()
            logger.error("Error updating session", error=str(e), session_id=session_id)
            return False
        finally:
            db_session.close()
    
    def deactivate_session(self, session_id: str) -> bool:
        """
        Deactivate session.
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if deactivated successfully
        """
        db_session = self.get_db_session()
        try:
            session = db_session.query(UserSession).filter(
                UserSession.session_id == session_id,
                UserSession.is_active == True
            ).first()
            
            if session:
                session.is_active = False
                session.conversation_state = "inactive"
                db_session.commit()
                
                # Session deactivated
                
                logger.info("Deactivated session", session_id=session_id)
                return True
            
            return False
            
        except Exception as e:
            db_session.rollback()
            logger.error("Error deactivating session", error=str(e), session_id=session_id)
            return False
        finally:
            db_session.close()
    
    def log_conversation(self, session_id: str, phone_number: str, message_type: str, 
                        message_content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log conversation message.
        
        Args:
            session_id: Session ID
            phone_number: User's phone number
            message_type: 'incoming' or 'outgoing'
            message_content: Message content
            metadata: Additional metadata
            
        Returns:
            bool: True if logged successfully
        """
        db_session = self.get_db_session()
        try:
            conversation = ConversationHistory(
                session_id=session_id,
                phone_number=phone_number,
                message_type=message_type,
                message_content=message_content,
                message_metadata=json.dumps(metadata or {}),
                timestamp=datetime.utcnow()
            )
            
            db_session.add(conversation)
            db_session.commit()
            
            logger.info("Logged conversation", 
                       session_id=session_id, 
                       message_type=message_type,
                       content_length=len(message_content))
            return True
            
        except Exception as e:
            db_session.rollback()
            logger.error("Error logging conversation", error=str(e), session_id=session_id)
            return False
        finally:
            db_session.close()
    
    def save_compliance_response(self, session_id: str, phone_number: str, 
                               response: ComplianceResponse) -> bool:
        """
        Save compliance response.
        
        Args:
            session_id: Session ID
            phone_number: User's phone number
            response: Compliance response data
            
        Returns:
            bool: True if saved successfully
        """
        db_session = self.get_db_session()
        try:
            compliance_response = ComplianceResponseDB(
                session_id=session_id,
                phone_number=phone_number,
                business_type=response.business_type,
                business_scale=response.business_scale,
                location=response.location,
                total_cost=response.total_estimated_cost,
                total_timeline_days=response.total_timeline_days,
                response_data=response.json(),
                confidence_score=str(response.confidence_score) if response.confidence_score else None,
                created_at=datetime.utcnow()
            )
            
            db_session.add(compliance_response)
            db_session.commit()
            
            logger.info("Saved compliance response", 
                       session_id=session_id, 
                       total_cost=response.total_estimated_cost,
                       total_timeline=response.total_timeline_days)
            return True
            
        except Exception as e:
            db_session.rollback()
            logger.error("Error saving compliance response", error=str(e), session_id=session_id)
            return False
        finally:
            db_session.close()
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversation history for session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List[Dict]: Conversation history
        """
        db_session = self.get_db_session()
        try:
            conversations = db_session.query(ConversationHistory).filter(
                ConversationHistory.session_id == session_id
            ).order_by(ConversationHistory.timestamp.desc()).limit(limit).all()
            
            history = []
            for conv in conversations:
                history.append({
                    "id": conv.id,
                    "message_type": conv.message_type,
                    "message_content": conv.message_content,
                    "timestamp": conv.timestamp.isoformat(),
                    "metadata": json.loads(conv.message_metadata or "{}")
                })
            
            return list(reversed(history))  # Return in chronological order
            
        except Exception as e:
            logger.error("Error getting conversation history", error=str(e), session_id=session_id)
            return []
        finally:
            db_session.close()
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Clean up old inactive sessions.
        
        Args:
            days: Number of days to keep sessions
            
        Returns:
            int: Number of sessions cleaned up
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        db_session = self.get_db_session()
        
        try:
            # Get sessions to clean up
            old_sessions = db_session.query(UserSession).filter(
                UserSession.is_active == False,
                UserSession.last_activity < cutoff_date
            ).all()
            
            count = len(old_sessions)
            
            # Delete old sessions
            for session in old_sessions:
                db_session.delete(session)
            
            db_session.commit()
            
            logger.info("Cleaned up old sessions", count=count, cutoff_date=cutoff_date.isoformat())
            return count
            
        except Exception as e:
            db_session.rollback()
            logger.error("Error cleaning up old sessions", error=str(e))
            return 0
        finally:
            db_session.close()
    


# Global database service instance
db_service = DatabaseService()
