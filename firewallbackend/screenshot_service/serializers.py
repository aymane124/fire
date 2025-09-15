from rest_framework import serializers


class ScreenshotRequestSerializer(serializers.Serializer):
    url = serializers.URLField(required=False)
    ip_address = serializers.IPAddressField(required=False)
    protocol = serializers.ChoiceField(choices=['http', 'https'], required=False, default='https')
    path = serializers.CharField(required=False, allow_blank=True, default='/login')
    post_login_path = serializers.CharField(required=False, allow_blank=True, default='')
    auto_follow_redirects = serializers.BooleanField(required=False, default=True)
    username = serializers.CharField(required=False, allow_blank=True, default='')
    password = serializers.CharField(required=False, allow_blank=True, write_only=True, default='')
    username_selector = serializers.CharField(required=False, allow_blank=True, default='')
    password_selector = serializers.CharField(required=False, allow_blank=True, default='')
    submit_selector = serializers.CharField(required=False, allow_blank=True, default='')
    wait_selector = serializers.CharField(required=False, allow_blank=True, default='')
    extract_selector = serializers.CharField(required=False, allow_blank=True, default='')
    viewport_width = serializers.IntegerField(required=False, min_value=320, default=1366)
    viewport_height = serializers.IntegerField(required=False, min_value=480, default=768)
    full_page = serializers.BooleanField(required=False, default=True)
    timeout_ms = serializers.IntegerField(required=False, min_value=1000, max_value=120000, default=30000)
    ignore_https_errors = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if not attrs.get('url') and not attrs.get('ip_address'):
            raise serializers.ValidationError('Provide either url or ip_address')
        return attrs


class ScreenshotResponseSerializer(serializers.Serializer):
    image_base64 = serializers.CharField()
    width = serializers.IntegerField()
    height = serializers.IntegerField()
    url = serializers.URLField()

