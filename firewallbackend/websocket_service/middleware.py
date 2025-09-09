import json
import jwt
from django.contrib.auth import get_user_model
from django.conf import settings
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

User = get_user_model()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Get token from query parameters
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if token:
            try:
                # Decode JWT token
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                user_id = payload.get('user_id')
                
                if user_id:
                    # Get user from database
                    user = await self.get_user(user_id)
                    if user:
                        scope['user'] = user
                        return await super().__call__(scope, receive, send)
            except jwt.ExpiredSignatureError:
                pass
            except jwt.InvalidTokenError:
                pass
            except Exception:
                pass

        # If no valid token, set anonymous user
        scope['user'] = None
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
