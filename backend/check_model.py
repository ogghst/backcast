import sys
sys.path.insert(0, '.')

from app.models.conversation import ConversationMessage

print('ConversationMessage fields:')
for field in ConversationMessage.__table__.columns:
    print(f'  - {field.name}: {field.type}')
