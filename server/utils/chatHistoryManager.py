from upstash_redis import Redis
import json
from datetime import datetime

class ChatHistoryManager:
    def __init__(self, redis_url, redis_token):
        """
        Initialize the Redis client using environment variables.
        Raises an error if the required environment variables are not set.
        """
       

        if not redis_url or not redis_token:
            raise ValueError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set in the environment")

        self.redis = Redis(url=redis_url, token=redis_token)

    def save_message(self, user_id: str, conversation_id: str, message: str, message_type: str):
        """
        Save a message to the chat history for a specific user and conversation.

        Args:
            user_id (str): The ID of the user.
            conversation_id (str): The ID of the conversation.
            message (str): The message to save.
            message_type (str): The type of message ('user' or 'assistant').

        Returns:
            bool: True if the message was saved successfully, False otherwise.
        """
        try:
            timestamp = datetime.now().isoformat()  # Unique timestamp
            message_for_redis = json.dumps({
                "type": message_type,
                "data": {
                    "content": message,
                },
                "timestamp": timestamp
            })
            
            # Combine user_id and conversation_id to create a unique Redis key
            redis_key = f"{user_id}:{conversation_id}"
            
            # Save the message to the Redis list for the specific conversation
            self.redis.lpush(redis_key, message_for_redis)
            
            return True
        except Exception as e:
            print(f"Error saving message: {e}")
            return False

    def retrieve_conversation_keys(self, user_id: str):
        """
        Retrieve all conversation keys for a specific user.

        Args:
            user_id (str): The ID of the user.

        Returns:
            list: A list of conversation keys (e.g., {user_id}:{conversation_id}-*).
        """
        try:
             
            conversation_keys = self.redis.keys(f"{user_id}:*")
            return conversation_keys
        except Exception as e:
            print(f"Error retrieving conversation keys: {e}")
            return []

    def get_all_messages(self, user_id: str, conversation_id: str):
        """
        Retrieve all messages from a specific conversation for a user.

        Args:
            user_id (str): The ID of the user.
            conversation_id (str): The ID of the conversation.

        Returns:
            list: A list of all messages for the specified conversation.
        """
        try:
            # Combine user_id and conversation_id to create a unique Redis key
            redis_key = f"{user_id}:{conversation_id}"
            
            # Retrieve all messages for the given conversation key
            messages = self.redis.lrange(redis_key, 0, -1)
            
            return [json.loads(msg) for msg in messages]
        except Exception as e:
            print(f"Error retrieving all messages: {e}")
            return []