from rest_framework import serializers
from .models import Template, Variable

class VariableSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Variable
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'user', 'historique_template']
        read_only_fields = ['id', 'created_at', 'updated_at', 'historique_template', 'user']

    def create(self, validated_data):
        # Remove read-only fields from validated_data
        validated_data.pop('id', None)
        validated_data.pop('user', None)
        validated_data.pop('created_at', None)
        validated_data.pop('updated_at', None)
        validated_data.pop('historique_template', None)
        
        # Create the variable with the validated data
        variable = Variable.objects.create(
            **validated_data,
            user=self.context['request'].user
        )
        return variable

    def update(self, instance, validated_data):
        # Remove read-only fields from validated_data
        validated_data.pop('id', None)
        validated_data.pop('user', None)
        validated_data.pop('created_at', None)
        validated_data.pop('updated_at', None)
        validated_data.pop('historique_template', None)
        
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        return instance

class TemplateSerializer(serializers.ModelSerializer):
    variables = VariableSerializer(many=True, required=False, read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Template
        fields = ['id', 'name', 'content', 'variables', 'user', 'created_at', 'updated_at', 'historique_template']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'historique_template']

    def create(self, validated_data):
        # Remove read-only fields from validated_data
        validated_data.pop('id', None)
        validated_data.pop('user', None)
        validated_data.pop('created_at', None)
        validated_data.pop('updated_at', None)
        validated_data.pop('variables', None)
        validated_data.pop('historique_template', None)
        
        # Create the template with the validated data
        template = Template.objects.create(
            **validated_data,
            user=self.context['request'].user
        )
        return template

    def update(self, instance, validated_data):
        # Remove read-only fields from validated_data
        validated_data.pop('id', None)
        validated_data.pop('user', None)
        validated_data.pop('created_at', None)
        validated_data.pop('updated_at', None)
        validated_data.pop('variables', None)
        validated_data.pop('historique_template', None)
        
        instance.name = validated_data.get('name', instance.name)
        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance 