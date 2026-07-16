from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.models import ChatLog, CrowdDensity
from typing import Dict, List, Any
import datetime
class ChatService:
    async def log_chat(
        self,
        db: AsyncSession,
        session_id: str,
        fan_message: str,
        ai_response: str,
        detected_language: str,
        intent: str,
        is_emergency: bool
    ) -> ChatLog:
        """Saves a chat log entry into the SQLite database"""
        chat_entry = ChatLog(
            session_id=session_id,
            fan_message=fan_message,
            ai_response=ai_response,
            detected_language=detected_language,
            intent=intent,
            is_emergency=is_emergency
        )
        db.add(chat_entry)
        await db.commit()
        await db.refresh(chat_entry)
        return chat_entry
    async def get_dashboard_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Calculates aggregate statistics for the staff dashboard"""
        # 1. Total queries
        total_queries_query = select(func.count(ChatLog.id))
        total_queries_result = await db.execute(total_queries_query)
        total_queries = total_queries_result.scalar() or 0
        # 2. Active sessions (unique session count)
        active_sessions_query = select(func.count(func.distinct(ChatLog.session_id)))
        active_sessions_result = await db.execute(active_sessions_query)
        active_sessions = active_sessions_result.scalar() or 0
        # 3. Emergency count
        emergency_count_query = select(func.count(ChatLog.id)).where(ChatLog.is_emergency == True)
        emergency_result = await db.execute(emergency_count_query)
        emergency_count = emergency_result.scalar() or 0
        # 4. Language distribution
        lang_query = select(ChatLog.detected_language, func.count(ChatLog.id)).group_by(ChatLog.detected_language)
        lang_result = await db.execute(lang_query)
        language_breakdown = {}
        for row in lang_result.all():
            lang = row[0] or "Unknown"
            count = row[1]
            language_breakdown[lang] = count
        return {
            "total_queries": total_queries,
            "active_sessions": active_sessions,
            "emergency_count": emergency_count,
            "language_breakdown": language_breakdown
        }
    async def get_frequent_queries(self, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves most common user intents"""
        query = select(ChatLog.intent, func.count(ChatLog.id))\
            .group_by(ChatLog.intent)\
            .order_by(desc(func.count(ChatLog.id)))\
            .limit(limit)
            
        result = await db.execute(query)
        frequent_queries = []
        for row in result.all():
            intent = row[0] or "other"
            count = row[1]
            frequent_queries.append({"intent": intent, "count": count})
        return frequent_queries
    async def get_emergency_logs(self, db: AsyncSession, limit: int = 20) -> List[ChatLog]:
        """Retrieves list of recent queries flagged as emergencies"""
        query = select(ChatLog)\
            .where(ChatLog.is_emergency == True)\
            .order_by(desc(ChatLog.created_at))\
            .limit(limit)
            
        result = await db.execute(query)
        return list(result.scalars().all())
chat_service = ChatService()
