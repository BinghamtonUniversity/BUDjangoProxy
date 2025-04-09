import json
from django.contrib import admin
from django import forms
from .models import API, APIVersion, APIInstance, Environment, User, Resource, APIUser

class JSONCodeContentAdminFormsss(forms.ModelForm):
    """
    Custom form for APIVersion to allow admins to input models and views separately,
    then encode them into a JSON string for `code_content`.
    """
    model_codes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'cols': 80}),
        required=True,
        help_text="Write the models code here."
    )
    view_codes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'cols': 80}),
        required=True,
        help_text="Write the views code here."
    )
    url_codes = forms.JSONField(
        widget=forms.Textarea(attrs={'rows': 10, 'cols': 80}),
        required=True,
        help_text="Write the URLs code here. Example:\n\nfrom django.urls import path\nfrom .views import example_view\nurlpatterns = [path('example/', example_view)]"
    )
    resource_codes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'cols': 80}),
        required=True,
        # help_text="Write the URLs code here. Example:\n\nfrom django.urls import path\nfrom .views import example_view\nurlpatterns = [path('example/', example_view)]"
    )
    # resources = forms.

    class Meta:
        model = APIVersion
        fields = ('api', 'model_codes', 'view_codes', 'url_codes', 'resource_codes', 'created_by', 'updated_by')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:  # Check if editing an existing instance
            try:
                # Decode the JSON strings and populate the fields
                version_models_data =self.instance.version_models
                version_views_data = self.instance.version_views
                version_urls_data = self.instance.version_urls
                resources_data = self.instance.resources

                # Set initial values for the fields
                self.fields['model_codes'].initial = version_models_data.get('content', '')
                self.fields['view_codes'].initial = version_views_data
                self.fields['url_codes'].initial = version_urls_data
                self.fields['resource_codes'].initial = resources_data

            except (ValueError, TypeError, json.JSONDecodeError):
                # If decoding fails, leave the fields empty
                self.fields['model_codes'].initial = ''
                self.fields['view_codes'].initial = ''
                self.fields['url_codes'].initial = []
                self.fields['resource_codes'].initial = ''

    def save(self, commit=True):
        """
        Override the save method to encode models_code and views_code as JSON
        in the `code_content` field.
        """
        version = super().save(commit=False)

        # Encode models_code and views_code as JSON
        # code_content = {
        # print((self.cleaned_data.get('version_codes', '')))
        version.version_models = {'content': self.cleaned_data.get('model_codes', '')}
        version.version_views = self.cleaned_data.get('view_codes', '')

        version.version_urls = self.cleaned_data.get('url_codes', '')
        version.resources = self.cleaned_data.get('resource_codes', '')
        # print('saving')
        # print(version.version_urls)
        if commit:
            version.save()
        return version

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('name', 'unique_id')
    search_fields = ('name', 'unique_id')
    list_filter = ('unique_id','name')

@admin.register(APIVersion)
class APIVersionAdmin(admin.ModelAdmin):
    """
    Admin configuration for APIVersion with custom form to handle JSON encoding.
    """
    form = JSONCodeContentAdminFormsss
    list_display = ('api', 'created_at', 'updated_at', 'created_by', 'updated_by')
    search_fields = ('api__name',)
    list_filter = ('created_at', 'updated_at')


@admin.register(API)
class APIAdmin(admin.ModelAdmin):
    """
    Admin configuration for API.
    """
    list_display = ('name', 'description', 'created_by', 'updated_by')
    search_fields = ('name', 'description')
    # list_filter = ('run_migrations',)
    autocomplete_fields = ('created_by', 'updated_by')


class APIInstanceAdminForm(forms.ModelForm):
    """
    Custom form for APIInstance to filter resources dynamically based on the environment and API version.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            # Get environment type from the instance
            type = self.instance.environment.type

            # Get resources related to the selected API version
            api_version_resources = list(self.instance.api_version.resources)

            # Filter resources by environment type and resources in the API version
            self.fields['resources'].queryset = Resource.objects.filter(
                type=type,
                name__in=[res for res in api_version_resources],
            )
        else:
            # Default to no resources if instance is not yet created
            self.fields['resources'].queryset = Resource.objects.none()

    class Meta:
        model = APIInstance
        fields = '__all__'


@admin.register(APIInstance)
class APIInstanceAdmin(admin.ModelAdmin):
    """
    Admin for APIInstance with a dynamic resource filter.
    """
    form = APIInstanceAdminForm
    list_display = ('name', 'route', 'api', 'api_version', 'environment', 'public', 'created_at', 'updated_at')
    search_fields = ('name', 'route')
    # list_filter = ('environment__type',  'public')
    # filter_horizontal = ('authorized_users',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Environment.
    """
    list_display = ('name', 'type', 'domain', 'created_at', 'updated_at')
    search_fields = ('name', 'type', 'domain')
    list_filter = ('type',)

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    # list_filter = ('environment__type','type')
    list_display = ('name','config','type', 'created_at', 'updated_at')


# Set the user admin form
class APIUserAdminAdminForm(forms.ModelForm):
    class Meta:
        model = APIUser
        fields = '__all__'
        list_display = ('environment','is_active' 'app_name', 'created_at', 'updated_at')
        search_fields = ('app_name',)
        list_filter = ('created_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Filter the queryset for the filter_horizontal field
            self.fields['api_instances'].queryset = APIInstance.objects.filter(environment=self.instance.environment)

@admin.register(APIUser)
class APIUserAdmin(admin.ModelAdmin):
    """
    Admin interface for managing APIUser accounts.
    """
    form = APIUserAdminAdminForm
    filter_horizontal = ('api_instances',)

    def save_model(self, request, obj, form, change):
        """
        Ensure passwords are hashed when creating or updating APIUser objects.
        """
        if 'password' in form.cleaned_data and form.cleaned_data['password']:
            obj.set_password(form.cleaned_data['password'])
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        """
        Make certain fields readonly for existing objects.
        """
        if obj:  # Editing an existing object
            return ['created_at', 'updated_at']
        return []