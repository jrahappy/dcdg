from django.core.management.base import BaseCommand
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from chat.consumers import ChatConsumer
from chat.models import ChatRoom
import asyncio
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Test WebSocket consumer'

    def handle(self, *args, **options):
        asyncio.run(self.test_websocket())

    async def test_websocket(self):
        self.stdout.write(self.style.SUCCESS('Testing WebSocket consumer...'))
        
        try:
            # Get a test user and chat room
            user = await database_sync_to_async(User.objects.first)()
            chat_room = await database_sync_to_async(ChatRoom.objects.first)()
            
            if not user or not chat_room:
                self.stdout.write(self.style.ERROR('No user or chat room found in database'))
                return
            
            # Create a WebSocket communicator
            communicator = WebsocketCommunicator(
                ChatConsumer.as_asgi(),
                f"/ws/chat/{chat_room.id}/",
                {"user": user}
            )
            
            # Connect
            connected, _ = await communicator.connect()
            if connected:
                self.stdout.write(self.style.SUCCESS('✓ WebSocket connected successfully'))
            else:
                self.stdout.write(self.style.ERROR('✗ WebSocket connection failed'))
                return
            
            # Send a test message
            await communicator.send_json_to({
                "type": "message",
                "message": "Test message from WebSocket"
            })
            
            # Receive response
            response = await communicator.receive_json_from()
            self.stdout.write(self.style.SUCCESS(f'✓ Received response: {json.dumps(response, indent=2)}'))
            
            # Test typing indicator
            await communicator.send_json_to({
                "type": "typing",
                "is_typing": True
            })
            
            # Disconnect
            await communicator.disconnect()
            self.stdout.write(self.style.SUCCESS('✓ WebSocket disconnected successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))