import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ChatRoom, ChatMessage, ChatNotification

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope["user"]

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send user connected message
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'user_id': self.user.id,
                'username': self.user.get_full_name() or self.user.username
            }
        )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Send user disconnected message
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_leave',
                'user_id': self.user.id,
                'username': self.user.get_full_name() or self.user.username
            }
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')

        if message_type == 'message':
            message = text_data_json['message']
            
            # Save message to database
            chat_message = await self.save_message(message)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'user_id': self.user.id,
                    'username': self.user.get_full_name() or self.user.username,
                    'timestamp': chat_message.created_at.isoformat(),
                    'message_id': chat_message.id
                }
            )
        elif message_type == 'typing':
            # Broadcast typing status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_status',
                    'user_id': self.user.id,
                    'username': self.user.get_full_name() or self.user.username,
                    'is_typing': text_data_json.get('is_typing', False)
                }
            )
        elif message_type == 'mark_read':
            # Mark messages as read
            message_ids = text_data_json.get('message_ids', [])
            await self.mark_messages_read(message_ids)

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id']
        }))

    async def typing_status(self, event):
        # Send typing status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def user_join(self, event):
        # Send user join notification
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'user_id': event['user_id'],
            'username': event['username']
        }))

    async def user_leave(self, event):
        # Send user leave notification
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'user_id': event['user_id'],
            'username': event['username']
        }))

    @database_sync_to_async
    def save_message(self, message):
        chat_room = ChatRoom.objects.get(pk=self.room_id)
        chat_message = ChatMessage.objects.create(
            chat_room=chat_room,
            sender=self.user,
            content=message,
            message_type='text'
        )
        
        # Create notification for the other user
        other_user = chat_room.customer if self.user == chat_room.manager else chat_room.manager
        if other_user:
            ChatNotification.objects.create(
                user=other_user,
                chat_room=chat_room,
                message=chat_message
            )
        
        return chat_message

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        ChatMessage.objects.filter(
            id__in=message_ids,
            chat_room_id=self.room_id
        ).exclude(
            sender=self.user
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # Mark notifications as seen
        ChatNotification.objects.filter(
            user=self.user,
            chat_room_id=self.room_id,
            message_id__in=message_ids
        ).update(
            is_seen=True
        )