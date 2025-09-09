from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import User, SSHUser
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'phone_number', 'first_name', 'last_name')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        # Récupérer le mot de passe
        password = validated_data.pop('password')
        
        # Créer l'utilisateur sans stocker le mot de passe en clair
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            phone_number=validated_data.get('phone_number', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        
        # Définir le mot de passe (hachage sécurisé)
        user.set_password(password)
        
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            raise serializers.ValidationError("Username and password are required")

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")

        data['user'] = user
        return data

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    current_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, allow_blank=True)
    last_name = serializers.CharField(required=True, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login', 'password', 'current_password')
        read_only_fields = ('id', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login', 'username')

    def validate(self, data):
        # If password is being updated, validate current_password
        if 'password' in data and data['password']:
            if 'current_password' not in data or not data['current_password']:
                raise serializers.ValidationError({"current_password": "Current password is required to set a new password."})
            
            # Verify current password
            if not self.instance.check_password(data['current_password']):
                raise serializers.ValidationError({"current_password": "Current password is incorrect."})
        
        return data

    def update(self, instance, validated_data):
        # Handle password update
        password = validated_data.pop('password', None)
        validated_data.pop('current_password', None)  # Remove current_password as it's not a model field
        
        if password:
            instance.set_password(password)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class SSHUserSerializer(serializers.ModelSerializer):
    ssh_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = SSHUser
        fields = ('id', 'ssh_username', 'ssh_password', 'ssh_private_key', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        # Créer l'instance SSHUser avec les données exactes fournies
        ssh_user = SSHUser.objects.create(
            user=validated_data['user'],
            ssh_username=validated_data['ssh_username'],
            ssh_password=validated_data['ssh_password'],  # Stockage direct du mot de passe
            ssh_private_key=validated_data.get('ssh_private_key', None)
        )
        return ssh_user

    def update(self, instance, validated_data):
        # Mettre à jour l'instance avec les nouvelles données exactes
        instance.ssh_username = validated_data.get('ssh_username', instance.ssh_username)
        instance.ssh_password = validated_data.get('ssh_password', instance.ssh_password)
        instance.ssh_private_key = validated_data.get('ssh_private_key', instance.ssh_private_key)
        instance.save()
        return instance 

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Custom token refresh serializer to handle UUID user IDs properly
    """
    def validate(self, attrs):
        try:
            # Get the refresh token
            refresh = attrs.get('refresh')
            if not refresh:
                raise InvalidToken('Refresh token is required')
            
            # Decode the token to get user_id
            from rest_framework_simplejwt.tokens import RefreshToken
            from rest_framework_simplejwt.exceptions import TokenError
            
            try:
                token = RefreshToken(refresh)
                user_id = token.payload.get('user_id')
                
                # Verify user exists
                User = get_user_model()
                try:
                    user = User.objects.get(id=user_id)
                    if not user.is_active:
                        raise InvalidToken('User account is disabled')
                except User.DoesNotExist:
                    logger.error(f"User with ID {user_id} not found during token refresh")
                    raise InvalidToken('User not found')
                    
            except TokenError as e:
                logger.error(f"Invalid refresh token: {str(e)}")
                raise InvalidToken('Invalid refresh token')
            
            # Call parent validation
            return super().validate(attrs)
            
        except InvalidToken as e:
            # Log the error for debugging
            logger.error(f"Token refresh failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            raise InvalidToken('Token refresh failed') 