import sys

with open("frontend/src/lib/firebase.ts", "r") as f:
    content = f.read()

# Add check for empty config
new_content = content.replace(
    'export const auth = isFirebaseConfigured && app ? getAuth(app) : null;',
    '''export const auth = isFirebaseConfigured && app ? getAuth(app) : null;

// Helper to check if Firebase is fully operational
export const isFirebaseReady = () => isFirebaseConfigured && !!app;'''
)

# Improve error logging
new_content = new_content.replace(
    'console.warn("Firebase initialization failed:", e);',
    'console.error("Firebase initialization failed. Configuration may be invalid.", e);'
)

with open("frontend/src/lib/firebase.ts", "w") as f:
    f.write(new_content)
