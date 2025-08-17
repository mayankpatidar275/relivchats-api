from sqlalchemy.orm import Session
from . import models, schemas

def store_user_on_login(db: Session, user: schemas.UserStore):
    # Check if the user already exists
    db_user = db.query(models.User).filter(models.User.user_id == user.user_id).first()

    if db_user:
        # If user exists, we can update any details
        # For now, let's just return the existing user
        return db_user
    else:
        # Create a new user record
        db_user = models.User(
            user_id=user.user_id,
            email=user.email,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user