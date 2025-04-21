from BUDjangoProxyApp.models import *
from BUDjangoProxy.settings import DYNAMIC_APPS_DIR, os
from BUDjangoProxyApp.services.DynamicLoader import *

class VersionControl():
    def file_integrity_check(self, api_instance):
        api_version = api_instance.get_instance_version()
        try:
            api_version_metadata = APIVersion.objects.only("id","updated_at").get(id=api_version.id)
        except APIVersion.DoesNotExist:
            return False

        print(f"{DYNAMIC_APPS_DIR}/{api_instance.id}/api_version.json")
        if os.path.exists(f"{DYNAMIC_APPS_DIR}/{api_instance.id}/api_version.json"):
            version_file = helpers.load_into_dict(f"{DYNAMIC_APPS_DIR}/{api_instance.id}/api_version.json")
            if str(api_version_metadata.updated_at) != version_file['updated_at']:
                self.file_reload(api_instance, api_version_metadata, api_version)
                return False
            else:
                return True
        else:
            self.file_reload(api_instance, api_version_metadata, api_version)
            return False


    def file_reload(self, api_instance,api_version_metadata, api_version):
        helper_data = {
            "api_id": api_version.api.id,
            "api_version_id": api_version.id,
            "summary": api_version_metadata.summary,
            "description": api_version_metadata.description,
            "stable": api_version_metadata.stable,
            "resources": api_version_metadata.resources,
            "routes": api_version_metadata.version_urls,
            "options": api_version_metadata.options,
            "created_at": str(api_version_metadata.created_at),
            "updated_at": str(api_version_metadata.updated_at),
        }
        helpers.save_result_file(f"{DYNAMIC_APPS_DIR}/{api_instance.id}/api_version.json", helper_data)