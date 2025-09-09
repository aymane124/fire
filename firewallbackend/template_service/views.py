from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Template, Variable, TemplateVariable
from .serializers import TemplateSerializer, VariableSerializer
import logging
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from datetime import datetime
from django.utils import timezone
import re

logger = logging.getLogger(__name__)

class TemplateViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing templates.
    """
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return Template.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        logger.info(f"Received template creation request: {request.data}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {request.headers}")
        logger.info(f"User: {request.user}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(user=self.request.user)
            instance.add_to_history(
                action='create',
                status='success',
                details=f'Created template: {instance.name}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.add_to_history(
            action='update',
            status='success',
            details=f'Updated template: {instance.name}',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        instance.add_to_history(
            action='delete',
            status='success',
            details=f'Deleted template: {instance.name}',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def add_variable(self, request, pk=None):
        template = self.get_object()
        variable_id = request.data.get('variable_id')
        
        if not variable_id:
            return Response(
                {"error": "Variable ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            variable = Variable.objects.get(id=variable_id)
            template.variables.add(variable)
            template.add_to_history(
                action='add_variable',
                status='success',
                details=f'Added variable {variable.name} to template {template.name}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({"status": "Variable added"})
        except Variable.DoesNotExist:
            return Response(
                {"error": "Variable not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error adding variable to template: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def remove_variable(self, request, pk=None):
        template = self.get_object()
        variable_id = request.data.get('variable_id')
        
        if not variable_id:
            return Response(
                {"error": "Variable ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            variable = Variable.objects.get(id=variable_id)
            template.variables.remove(variable)
            template.add_to_history(
                action='remove_variable',
                status='success',
                details=f'Removed variable {variable.name} from template {template.name}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({"status": "Variable removed"})
        except Variable.DoesNotExist:
            return Response(
                {"error": "Variable not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error removing variable from template: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def download_excel(self, request, pk=None):
        try:
            template = self.get_object()
            
            # Extract unique variables from template content
            variable_pattern = r'{{([^}]+)}}'
            variables_in_content = sorted(set(re.findall(variable_pattern, template.content)))
            
            # Create Excel writer
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Create a new worksheet
                workbook = writer.book
                worksheet = workbook.add_worksheet('Template Variables')
                
                # Add some formatting
                variable_format = workbook.add_format({
                    'bg_color': '#E6F3FF',
                    'border': 1,
                    'align': 'center',
                    'valign': 'vcenter'
                })
                
                # Write variables in columns
                for col_num, var in enumerate(variables_in_content):
                    worksheet.write(0, col_num, var.strip(), variable_format)
                    worksheet.set_column(col_num, col_num, 25)
            
            # Prepare the response
            output.seek(0)
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=template_variables_{template.name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
            template.add_to_history(
                action='download_excel',
                status='success',
                details=f'Downloaded Excel file for template {template.name}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating Excel file: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VariableViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing variables.
    """
    serializer_class = VariableSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Variable.objects.all()

    def get_queryset(self):
        return Variable.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        instance.add_to_history(
            action='create',
            status='success',
            details=f'Created variable: {instance.name}',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.add_to_history(
            action='update',
            status='success',
            details=f'Updated variable: {instance.name}',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        instance.add_to_history(
            action='delete',
            status='success',
            details=f'Deleted variable: {instance.name}',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

    def create(self, request, *args, **kwargs):
        try:
            logger.info(f"Received variable creation request: {request.data}")
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"Error creating variable: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            ) 