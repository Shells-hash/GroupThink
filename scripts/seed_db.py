"""
Seed the database with sample data for development.
Run from the project root: python scripts/seed_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.engine import SessionLocal, init_db
from backend.services.auth_service import register_user
from backend.services.group_service import create_group, invite_user
from backend.models.thread import Thread
from backend.models.message import Message

init_db()
db = SessionLocal()

try:
    # Users
    alice = register_user(db, "alice", "alice@example.com", "password123")
    bob = register_user(db, "bob", "bob@example.com", "password123")
    carol = register_user(db, "carol", "carol@example.com", "password123")
    print(f"Created users: alice (id={alice.id}), bob (id={bob.id}), carol (id={carol.id})")

    # Group
    group = create_group(db, "Weekend Trip", "Planning our camping trip", alice.id)
    invite_user(db, group.id, alice.id, "bob")
    invite_user(db, group.id, alice.id, "carol")
    print(f"Created group '{group.name}' (id={group.id})")

    # Thread
    thread = Thread(group_id=group.id, title="Where should we go?", created_by=alice.id)
    db.add(thread)
    db.flush()

    # Sample messages
    messages = [
        Message(thread_id=thread.id, user_id=alice.id, content="Hey everyone! Where should we go for the camping trip?"),
        Message(thread_id=thread.id, user_id=bob.id, content="I was thinking Yosemite — incredible views and not too far."),
        Message(thread_id=thread.id, user_id=carol.id, content="Yosemite sounds amazing! But it can get crowded. Maybe Big Sur?"),
        Message(thread_id=thread.id, user_id=alice.id, content="@ai Can you help us decide between Yosemite and Big Sur for a weekend camping trip with 3 people?"),
    ]
    for m in messages:
        db.add(m)

    db.commit()
    print(f"Created thread '{thread.title}' with {len(messages)} messages")
    print("\nSeed complete! Login with alice/password123, bob/password123, or carol/password123")
finally:
    db.close()
