import os

# Set testing flag to prevent starting the Discord bot thread during unit testing
os.environ["TESTING"] = "true"
