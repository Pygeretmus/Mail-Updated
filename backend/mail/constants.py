SYSTEM_LABELS = ['inbox', 'sent', 'archive', 'spam', 'starred']

# Names a user can't take: the system labels, plus "trash", which the client uses for the trash view
RESERVED_LABEL_NAMES = [*SYSTEM_LABELS, 'trash']

# How long a trashed entry is kept before the cleanup task removes it for good
TRASH_RETENTION_DAYS = 30
