"""
Handles checking and awarding achievements.
"""
from app.database import db, User, Achievement, UserAchievement, GameResult, Kviz

# A list of all achievements in the system.
# We will populate them in the DB when the app starts.
ALL_ACHIEVEMENTS = [
    {
        "id": "professor",
        "name": "Profesor",
        "description": "Získej 100% skóre v jakémkoli kvízu.",
        "icon_class": "fa-graduation-cap"
    },
    {
        "id": "warrior",
        "name": "Bojovník",
        "description": "Dokonči 3 soutěžní (plánované) kvízy.",
        "icon_class": "fa-shield-alt"
    },
    {
        "id": "veteran",
        "name": "Veterán",
        "description": "Dokonči 10 libovolných kvízů.",
        "icon_class": "fa-medal"
    }
]

def check_and_award_achievements(user_id: int, new_result: GameResult):
    """
    Checks all achievement conditions for a user after they finish a quiz.
    Runs in a separate try/except block so it never crashes the game.
    """
    try:
        # Get all achievements the user *already* has
        existing_ach_ids = {
            ua.achievement_id_fk for ua in
            UserAchievement.query.filter_by(user_id_fk=user_id).all()
        }

        newly_awarded = []

        # --- 1. Check "Professor" ---
        if "professor" not in existing_ach_ids:
            if new_result.score == new_result.total_questions:
                newly_awarded.append(UserAchievement(
                    user_id_fk=user_id, achievement_id_fk="professor"
                ))
                existing_ach_ids.add("professor") # Add for next check

        # --- 2. Get all user results for aggregate checks ---
        all_results = GameResult.query.filter_by(user_id_fk=user_id).all()

        # --- 3. Check "Veteran" ---
        if "veteran" not in existing_ach_ids:
            if len(all_results) >= 10:
                newly_awarded.append(UserAchievement(
                    user_id_fk=user_id, achievement_id_fk="veteran"
                ))
                existing_ach_ids.add("veteran")

        # --- 4. Check "Warrior" ---
        if "warrior" not in existing_ach_ids:
            # We need the full quiz objects for this check
            scheduled_quiz_ids = {
                k.kviz_id for k in db.session.query(Kviz.kviz_id).filter_by(quiz_mode="scheduled").all()
            }
            completed_scheduled_count = sum(
                1 for res in all_results if res.kviz_id_fk in scheduled_quiz_ids
            )
            if completed_scheduled_count >= 3:
                newly_awarded.append(UserAchievement(
                    user_id_fk=user_id, achievement_id_fk="warrior"
                ))
                existing_ach_ids.add("warrior")

        # --- Commit new achievements ---
        if newly_awarded:
            db.session.add_all(newly_awarded)
            db.session.commit()
            print(f"Awarded {len(newly_awarded)} new achievements to user {user_id}")

    except Exception as e:
        # Log the error but don't crash the request
        print(f"CRITICAL: Error during achievement check for user {user_id}: {e}")
        db.session.rollback()

def init_achievements():
    """
    Populates the Achievement table if it's empty.
    Called on app startup.
    """
    if Achievement.query.count() == 0:
        print("Populating achievements table...")
        for ach_data in ALL_ACHIEVEMENTS:
            db.session.add(Achievement(**ach_data))
        db.session.commit()
