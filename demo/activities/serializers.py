from smartmodels.drf.serializers import ResourceSerializer
from .models import Activity


class ActivitySerializer(ResourceSerializer):
    class Meta:
        model = Activity
