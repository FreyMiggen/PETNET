from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging
from django.conf import settings
import os

logger = logging.getLogger('petnet')

if not logger.handlers:
    logger.setLevel(logging.INFO)

    # Create logs directory if it doesn't exist
    log_directory = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_directory, exist_ok=True)

    # Create file handler which logs info and error messages
    file_handler = logging.FileHandler(os.path.join(log_directory, 'notifications_consumer.log'))
    file_handler.setLevel(logging.INFO)

    # Create console handler for error messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Prevent the logger from propagating to the root logger
    logger.propagate = False


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            try:
                await self.channel_layer.group_add(
                    f"user_{self.user.id}",
                    self.channel_name
                )
                await self.accept()
                logger.info(f"User {self.user.id} connected successfully")
            except Exception as e:
                logger.error(f"Error during connect: {e}")
                await self.close()
        else:
            logger.info("Unauthenticated user connection attempt")
            await self.close()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            try:
                await self.channel_layer.group_discard(
                    f"user_{self.user.id}",
                    self.channel_name
                )
                logger.info(f"User {self.user.id} disconnected successfully")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")

    async def send_notification(self, event):
        try:
            message = event["message"]
            await self.send(text_data=json.dumps(message))
            logger.info(f"Notification sent to user {self.user.id}: {message}")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            await self.close()
