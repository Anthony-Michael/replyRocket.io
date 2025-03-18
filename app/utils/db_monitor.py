"""
Database monitoring utilities for ReplyRocket.io.

This module provides tools to monitor database connection and session usage,
which can help detect potential session leaks and connection issues.
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Set
import weakref
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Set up logger
logger = logging.getLogger(__name__)

# Global session tracking
_active_sessions: Dict[str, Dict] = {}
_session_lock = threading.Lock()

# Session performance stats
_session_stats = {
    "created": 0,
    "closed": 0,
    "active": 0,
    "max_active": 0,
    "errors": 0,
}


def register_session(session: Session) -> str:
    """
    Register a new database session for tracking.
    
    Args:
        session: The SQLAlchemy session to track
        
    Returns:
        The session ID used for tracking
    """
    session_id = str(uuid4())
    session_info = {
        "created_at": time.time(),
        "thread_id": threading.get_ident(),
        "thread_name": threading.current_thread().name,
    }
    
    with _session_lock:
        _active_sessions[session_id] = session_info
        _session_stats["created"] += 1
        _session_stats["active"] += 1
        _session_stats["max_active"] = max(_session_stats["max_active"], _session_stats["active"])
    
    # Create a finalizer to detect when session is garbage collected
    weakref.finalize(session, _check_session_closure, session_id)
    
    return session_id


def unregister_session(session_id: str) -> None:
    """
    Unregister a database session from tracking.
    
    Args:
        session_id: The session ID to unregister
    """
    with _session_lock:
        if session_id in _active_sessions:
            session_info = _active_sessions.pop(session_id)
            duration = time.time() - session_info["created_at"]
            
            _session_stats["closed"] += 1
            _session_stats["active"] -= 1
            
            if duration > 30:  # Log long-running sessions (> 30 seconds)
                logger.warning(
                    f"Long-running session closed: {session_id}, "
                    f"duration: {duration:.2f}s, "
                    f"thread: {session_info['thread_name']}"
                )


def _check_session_closure(session_id: str) -> None:
    """
    Check if a session was properly closed when it's garbage collected.
    
    Args:
        session_id: The session ID to check
    """
    with _session_lock:
        if session_id in _active_sessions:
            logger.warning(
                f"Session {session_id} was garbage collected but not properly closed. "
                f"This may indicate a session leak in thread {_active_sessions[session_id]['thread_name']}"
            )
            _session_stats["errors"] += 1
            unregister_session(session_id)


def get_session_stats() -> Dict:
    """
    Get statistics about session usage.
    
    Returns:
        Dictionary with session statistics
    """
    with _session_lock:
        stats = _session_stats.copy()
        # Add active sessions by age
        active_sessions = list(_active_sessions.values())
        current_time = time.time()
        stats["active_by_age"] = {
            "<10s": sum(1 for s in active_sessions if current_time - s["created_at"] < 10),
            "10-30s": sum(1 for s in active_sessions if 10 <= current_time - s["created_at"] < 30),
            "30-60s": sum(1 for s in active_sessions if 30 <= current_time - s["created_at"] < 60),
            ">60s": sum(1 for s in active_sessions if current_time - s["created_at"] >= 60),
        }
    return stats


def log_active_sessions() -> None:
    """Log information about active sessions."""
    with _session_lock:
        active_count = len(_active_sessions)
        if active_count > 0:
            logger.info(f"Active sessions: {active_count}")
            # Log details of any sessions older than 60 seconds
            current_time = time.time()
            old_sessions = [
                (sid, info) for sid, info in _active_sessions.items() 
                if current_time - info["created_at"] >= 60
            ]
            
            if old_sessions:
                logger.warning(f"Found {len(old_sessions)} sessions open for more than 60 seconds:")
                for sid, info in old_sessions:
                    logger.warning(
                        f"  Session {sid}: "
                        f"age={current_time - info['created_at']:.2f}s, "
                        f"thread={info['thread_name']}"
                    )


class SessionTracker:
    """Context manager to track database session usage."""
    
    def __init__(self, session: Session, context: str = "unknown"):
        """
        Initialize the session tracker.
        
        Args:
            session: The SQLAlchemy session to track
            context: A string describing where this session is used
        """
        self.session = session
        self.context = context
        self.session_id = None
        self.start_time = None
    
    def __enter__(self):
        """Register the session when entering the context."""
        self.start_time = time.time()
        self.session_id = register_session(self.session)
        logger.debug(f"Session {self.session_id} started in context: {self.context}")
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Unregister the session when exiting the context."""
        if self.session_id:
            duration = time.time() - self.start_time
            if exc_type:
                logger.error(
                    f"Session {self.session_id} in context {self.context} "
                    f"encountered an error after {duration:.2f}s: {exc_val}"
                )
                _session_stats["errors"] += 1
            else:
                logger.debug(
                    f"Session {self.session_id} in context {self.context} "
                    f"completed successfully in {duration:.2f}s"
                )
            unregister_session(self.session_id) 