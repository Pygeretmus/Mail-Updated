SYSTEM_LABELS = ['inbox', 'sent', 'archive', 'spam', 'starred']

# Names a user can't take: the system labels, plus "trash", which the client uses for the trash view
RESERVED_LABEL_NAMES = [*SYSTEM_LABELS, 'trash']
