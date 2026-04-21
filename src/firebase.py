import firebase_admin
from firebase_admin import auth, credentials, firestore
from google.cloud.firestore import Client

_app: firebase_admin.App | None = None


def get_app() -> firebase_admin.App:
    """
    Initialise the Firebase Admin SDK once using Application Default Credentials.
    Subsequent calls return the already-initialised app.
    """
    global _app
    if _app is None:
        # ADC: reads GOOGLE_APPLICATION_CREDENTIALS env var automatically.
        # GOOGLE_CLOUD_PROJECT must also be set so the SDK knows which project to use.
        cred = credentials.ApplicationDefault()
        _app = firebase_admin.initialize_app(cred)
    return _app


def get_db() -> Client:
    """Return a Firestore client, initialising the app if necessary."""
    get_app()
    return firestore.client()
