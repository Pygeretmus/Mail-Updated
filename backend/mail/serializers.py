from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from configuration.serializers import CustomModelSerializer, LowerEmailField

from .constants import RESERVED_LABEL_NAMES
from .models import Label, MailboxEntry, Message
from .services import send_message

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


class MessageComposeSerializer(serializers.Serializer):
    to = serializers.ListField(child=LowerEmailField(), allow_empty=False)
    cc = serializers.ListField(child=LowerEmailField(), required=False, default=list)
    bcc = serializers.ListField(child=LowerEmailField(), required=False, default=list)
    subject = serializers.CharField(allow_blank=True, required=False, default='', max_length=255)
    body = serializers.CharField(allow_blank=False, required=True)

    def validate(self, attrs):
        sender = self.context['request'].user
        emails = [*attrs['to'], *attrs['cc'], *attrs['bcc']]
        unique = set(emails)

        if len(emails) != len(unique):
            raise serializers.ValidationError('The same recipient cannot be listed twice.')
        if sender.email in unique:
            raise serializers.ValidationError('You cannot add yourself as a recipient.')

        users = {u.email: u for u in User.objects.filter(email__in=unique)}
        if missing := unique - users.keys():
            raise serializers.ValidationError(f'Unknown recipients: {", ".join(sorted(missing))}')

        for field in ('to', 'cc', 'bcc'):
            attrs[field] = [users[email] for email in attrs[field]]
        return attrs

    def create(self, validated_data):
        return send_message(
            sender=self.context['request'].user,
            subject=validated_data['subject'],
            body=validated_data['body'],
            recipients={f: validated_data[f] for f in ('to', 'cc', 'bcc')},
        )


class RecipientSerializer(serializers.Serializer):
    """One line in the list of email recipients (excluding the sender)"""

    email = LowerEmailField(source='user.email', allow_null=True)
    role = serializers.CharField(max_length=255)


class MessageSerializer(CustomModelSerializer):
    sender = LowerEmailField(source='sender.email', allow_null=True, read_only=True)
    recipients = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'thread', 'parent', 'sender', 'subject', 'body', 'created_at', 'recipients')
        read_only_fields = fields

    @extend_schema_field(RecipientSerializer(many=True))
    def get_recipients(self, obj):
        request = self.context['request']

        can_see_bcc = obj.sender_id == request.user.id
        entries = [
            e
            for e in obj.entries.all()  # uses the prefetch cache when present
            if e.role != MailboxEntry.Role.SENDER and (can_see_bcc or e.role != MailboxEntry.Role.BCC)
        ]
        return RecipientSerializer(entries, many=True).data


class MailboxEntryDetailSerializer(CustomModelSerializer):
    message = MessageSerializer(read_only=True)
    labels = LabelSerializer(many=True, read_only=True)

    class Meta:
        model = MailboxEntry
        fields = ('id', 'message', 'role', 'is_read', 'deleted_at', 'labels')
        read_only_fields = ('message', 'role', 'is_read', 'deleted_at')
