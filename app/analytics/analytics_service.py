# app/analytics/analytics_service.py
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy import func, and_, or_
from app.models import (
    User, Conversation, Message, ConversionEvent, 
    AnalyticsEvent, AppSession, FeatureUsage
)
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Comprehensive analytics service for tracking and reporting"""
    
    @staticmethod
    def get_dashboard_metrics(company_id: int = None, time_range: str = '7d') -> Dict[str, Any]:
        """Get comprehensive dashboard metrics"""
        
        # Calculate date range
        end_date = datetime.utcnow()
        if time_range == '24h':
            start_date = end_date - timedelta(days=1)
        elif time_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif time_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif time_range == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)
        
        try:
            # Base query filters
            time_filter = and_(
                Message.timestamp >= start_date,
                Message.timestamp <= end_date
            )
            
            # Total users
            total_users = User.query.filter(
                User.created_at >= start_date
            ).count()
            
            # Active users (users who sent messages)
            active_users = db.session.query(
                func.count(func.distinct(Conversation.user_id))
            ).join(Message).filter(time_filter).scalar()
            
            # Total messages
            total_messages = Message.query.filter(time_filter).count()
            
            # Message breakdown
            user_messages = Message.query.filter(
                time_filter,
                Message.sender_type == 'user'
            ).count()
            
            bot_messages = Message.query.filter(
                time_filter,
                Message.sender_type == 'bot'
            ).count()
            
            # Average response time
            avg_response_time = db.session.query(
                func.avg(
                    func.extract('epoch', Message.timestamp) - 
                    func.extract('epoch', func.lag(Message.timestamp).over(
                        partition_by=Message.conversation_id,
                        order_by=Message.timestamp
                    ))
                )
            ).filter(
                time_filter,
                Message.sender_type == 'bot'
            ).scalar() or 0
            
            # Conversion metrics
            total_conversions = ConversionEvent.query.filter(
                ConversionEvent.timestamp >= start_date
            ).count()
            
            conversion_by_type = db.session.query(
                ConversionEvent.event_type,
                func.count(ConversionEvent.id)
            ).filter(
                ConversionEvent.timestamp >= start_date
            ).group_by(ConversionEvent.event_type).all()
            
            # Session metrics
            total_sessions = AppSession.query.filter(
                AppSession.started_at >= start_date
            ).count()
            
            avg_session_duration = db.session.query(
                func.avg(AppSession.duration_seconds)
            ).filter(
                AppSession.started_at >= start_date
            ).scalar() or 0
            
            # Feature usage
            feature_usage = db.session.query(
                FeatureUsage.feature_name,
                func.sum(FeatureUsage.usage_count),
                func.count(func.distinct(FeatureUsage.user_id))
            ).filter(
                FeatureUsage.last_used_at >= start_date
            ).group_by(FeatureUsage.feature_name).all()
            
            # Daily active users trend
            daily_active_users = db.session.query(
                func.date(Message.timestamp).label('date'),
                func.count(func.distinct(Conversation.user_id)).label('active_users')
            ).join(Conversation).filter(
                time_filter
            ).group_by(func.date(Message.timestamp)).all()
            
            # Hourly message distribution
            hourly_distribution = db.session.query(
                func.extract('hour', Message.timestamp).label('hour'),
                func.count(Message.id).label('count')
            ).filter(
                time_filter
            ).group_by(func.extract('hour', Message.timestamp)).all()
            
            # User retention (returning users)
            returning_users = db.session.query(
                func.count(func.distinct(Conversation.user_id))
            ).filter(
                Conversation.id.in_(
                    db.session.query(Conversation.id).join(Message).filter(
                        Message.timestamp >= start_date - timedelta(days=30),
                        Message.timestamp < start_date
                    )
                ),
                Conversation.id.in_(
                    db.session.query(Conversation.id).join(Message).filter(time_filter)
                )
            ).scalar()
            
            # Calculate metrics
            metrics = {
                'overview': {
                    'total_users': total_users,
                    'active_users': active_users,
                    'total_messages': total_messages,
                    'user_messages': user_messages,
                    'bot_messages': bot_messages,
                    'total_sessions': total_sessions,
                    'avg_session_duration_seconds': float(avg_session_duration),
                    'avg_response_time_seconds': float(avg_response_time),
                    'total_conversions': total_conversions,
                    'returning_users': returning_users,
                    'engagement_rate': (active_users / total_users * 100) if total_users > 0 else 0
                },
                'conversions': {
                    'total': total_conversions,
                    'by_type': [
                        {'type': event_type, 'count': count}
                        for event_type, count in conversion_by_type
                    ],
                    'conversion_rate': (total_conversions / active_users * 100) if active_users > 0 else 0
                },
                'features': [
                    {
                        'name': name,
                        'total_uses': uses,
                        'unique_users': users
                    }
                    for name, uses, users in feature_usage
                ],
                'trends': {
                    'daily_active_users': [
                        {'date': date.isoformat(), 'users': users}
                        for date, users in daily_active_users
                    ],
                    'hourly_distribution': [
                        {'hour': int(hour), 'messages': count}
                        for hour, count in hourly_distribution
                    ]
                },
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'range': time_range
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error generating dashboard metrics: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def track_event(
        user_id: int,
        event_type: str,
        event_category: str = None,
        event_data: Dict = None,
        session_id: str = None,
        platform: str = None
    ) -> bool:
        """Track a custom analytics event"""
        try:
            event = AnalyticsEvent(
                user_id=user_id,
                event_type=event_type,
                event_category=event_category,
                event_data=event_data or {},
                session_id=session_id,
                platform=platform,
                timestamp=datetime.utcnow()
            )
            db.session.add(event)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error tracking event: {e}")
            return False
    
    @staticmethod
    def get_user_journey(user_id: int, limit: int = 100) -> List[Dict]:
        """Get user's interaction journey"""
        try:
            # Get all events for user
            events = db.session.query(
                AnalyticsEvent.event_type,
                AnalyticsEvent.event_category,
                AnalyticsEvent.event_data,
                AnalyticsEvent.timestamp
            ).filter(
                AnalyticsEvent.user_id == user_id
            ).order_by(
                AnalyticsEvent.timestamp.desc()
            ).limit(limit).all()
            
            # Get messages
            messages = db.session.query(
                Message.content,
                Message.sender_type,
                Message.timestamp,
                Conversation.id
            ).join(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(
                Message.timestamp.desc()
            ).limit(limit).all()
            
            # Combine and sort
            journey = []
            
            for event_type, category, data, timestamp in events:
                journey.append({
                    'type': 'event',
                    'event_type': event_type,
                    'category': category,
                    'data': data,
                    'timestamp': timestamp.isoformat()
                })
            
            for content, sender, timestamp, conv_id in messages:
                journey.append({
                    'type': 'message',
                    'sender': sender,
                    'content': content[:100],  # Truncate for preview
                    'conversation_id': conv_id,
                    'timestamp': timestamp.isoformat()
                })
            
            # Sort by timestamp
            journey.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return journey[:limit]
            
        except Exception as e:
            logger.error(f"Error getting user journey: {e}")
            return []
    
    @staticmethod
    def get_funnel_metrics() -> Dict[str, Any]:
        """Get conversion funnel metrics"""
        try:
            # Define funnel stages
            stages = [
                ('app_open', 'App Opened'),
                ('chat_started', 'Started Chat'),
                ('engaged', 'Engaged (5+ messages)'),
                ('interest_shown', 'Showed Interest'),
                ('demo_scheduled', 'Scheduled Demo'),
                ('converted', 'Converted')
            ]
            
            funnel_data = []
            
            for stage_key, stage_name in stages:
                if stage_key == 'app_open':
                    count = User.query.count()
                elif stage_key == 'chat_started':
                    count = db.session.query(
                        func.count(func.distinct(Conversation.user_id))
                    ).scalar()
                elif stage_key == 'engaged':
                    # Users with 5+ messages
                    count = db.session.query(
                        func.count(func.distinct(Conversation.user_id))
                    ).join(Message).group_by(
                        Conversation.user_id
                    ).having(
                        func.count(Message.id) >= 5
                    ).count()
                elif stage_key in ['interest_shown', 'demo_scheduled', 'converted']:
                    count = ConversionEvent.query.filter(
                        ConversionEvent.event_type.like(f'%{stage_key}%')
                    ).count()
                else:
                    count = 0
                
                funnel_data.append({
                    'stage': stage_name,
                    'count': count,
                    'percentage': 0  # Will calculate after
                })
            
            # Calculate percentages
            if funnel_data[0]['count'] > 0:
                for i, stage in enumerate(funnel_data):
                    stage['percentage'] = (stage['count'] / funnel_data[0]['count']) * 100
                    if i > 0:
                        stage['conversion_rate'] = (
                            (stage['count'] / funnel_data[i-1]['count'] * 100)
                            if funnel_data[i-1]['count'] > 0 else 0
                        )
            
            return {
                'funnel': funnel_data,
                'overall_conversion': funnel_data[-1]['percentage'] if funnel_data else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating funnel metrics: {e}")
            return {'funnel': [], 'overall_conversion': 0}
