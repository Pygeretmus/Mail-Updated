from django.contrib.auth import get_user_model
from rest_framework import serializers

from configuration.serializers import CustomModelSerializer

from .constants import RESERVED_LABEL_NAMES
from .models import Label

User = get_user_model()


class LabelSerializer(CustomModelSerializer):
    class Meta:
        model = Label
        fields = ('id', 'name', 'is_system')
        read_only_fields = ('is_system',)

    def validate_name(self, value):
        if value.lower() in RESERVED_LABEL_NAMES:
            raise serializers.ValidationError('This label name is reserved.')
        qs = Label.objects.filter(user=self.context['request'].user, name__iexact=value)
        # Current name doesn't get flagged as a duplicate
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Label with this name already exists.')
        return value

    def create(self, validated_data):
        return Label.objects.create(user=self.context['request'].user, **validated_data)
