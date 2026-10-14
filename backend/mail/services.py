from typing import NamedTuple

from django.db import transaction
from rest_framework import serializers

from .models import Label, MailboxEntry, Message, Thread


class _Participant(NamedTuple):
    user: object
    role: str
    is_read: bool
    label_name: str


@transaction.atomic
def send_message(*, sender, subject: str, body: str, recipients: dict, thread=None, parent=None) -> Message:
    """
    Creates a Message and one MailboxEntry per participant (including
    the sender). There are no drafts: a message either doesn't exist
    yet or has already been sent.

    recipients: {"to": [User, ...], "cc": [...], "bcc": [...]}
    thread: pass an existing Thread when replying within a conversation,
            otherwise a new one is created.
    parent: the Message being replied to (for reply/reply_all).
    """
    if thread is None:
        thread = Thread.objects.create()
    message = Message.objects.create(thread=thread, parent=parent, sender=sender, subject=subject, body=body)

    participants = [_Participant(sender, MailboxEntry.Role.SENDER, True, 'sent')]
    for field, role in (('to', MailboxEntry.Role.TO), ('cc', MailboxEntry.Role.CC), ('bcc', MailboxEntry.Role.BCC)):
        participants += [_Participant(user, role, False, 'inbox') for user in recipients.get(field, [])]

    labels = {
        (label.user_id, label.name): label
        for label in Label.objects.filter(
            is_system=True,
            name__in=('sent', 'inbox'),
            user__in=[p.user for p in participants],
        )
    }

    entries = MailboxEntry.objects.bulk_create(
        [MailboxEntry(user=p.user, message=message, role=p.role, is_read=p.is_read) for p in participants]
    )

    EntryLabel = MailboxEntry.labels.through
    EntryLabel.objects.bulk_create(
        [
            EntryLabel(mailboxentry_id=entry.pk, label_id=labels[(p.user.pk, p.label_name)].pk)
            for entry, p in zip(entries, participants)
        ]
    )
    return message


def build_reply_recipients(parent_message: Message, replying_user, reply_all: bool = False) -> dict:
    is_own_message = parent_message.sender_id == replying_user.id
    sender = parent_message.sender
    to_users, cc_users = set(), set()
    if not is_own_message and sender is not None:
        to_users.add(sender)

    if reply_all or is_own_message:
        entries = (
            parent_message.entries.filter(role__in=[MailboxEntry.Role.TO, MailboxEntry.Role.CC])
            .exclude(user=replying_user)
            .select_related('user')
        )
        for entry in entries:
            if entry.role == MailboxEntry.Role.TO:
                to_users.add(entry.user)
            elif reply_all:
                cc_users.add(entry.user)

    # Everyone in 'to' may be gone (deleted accounts) while people in 'cc' remain: they become the addressees
    if not to_users and cc_users:
        to_users, cc_users = cc_users, set()

    if not to_users:
        raise serializers.ValidationError('There is nobody to reply to: the recipients accounts no longer exist.')

    return {'to': list(to_users), 'cc': list(cc_users)}
