import os
from slack_bolt import App
from google.cloud import secretmanager_v1
import json

# Initialize the Slack Bolt app with your signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Initialize the Google Cloud Secret Manager client
secret_manager_client = secretmanager_v1.SecretManagerServiceClient()

# Function to set default organization and repository for a user
def set_default_org_repo(user_id, org, repo):
    # Prepare the secret payload
    payload = {
        "default_org": org,
        "default_repo": repo
    }
    # Convert payload to JSON
    json_payload = json.dumps(payload)
    # Build the secret name
    secret_name = f"users/{user_id}/default_org_repo"
    # Create the secret
    parent = f"projects/{os.environ.get('GOOGLE_CLOUD_PROJECT')}"
    secret = {
        "name": secret_name,
        "payload": {"data": json_payload.encode("UTF-8")}
    }
    response = secret_manager_client.add_secret_version(request={"parent": parent, "payload": secret})

    return response.name

# Function to get default organization and repository for a user
def get_default_org_repo(user_id):
    # Build the secret name
    secret_name = f"projects/{os.environ.get('GOOGLE_CLOUD_PROJECT')}/secrets/users/{user_id}/default_org_repo/versions/latest"
    # Access the secret
    response = secret_manager_client.access_secret_version(request={"name": secret_name})
    # Decode and parse the secret payload
    payload = json_format.Parse(response.payload.data.decode("UTF-8"), {})
    default_org = payload.get("default_org")
    default_repo = payload.get("default_repo")

    return default_org, default_repo

# Define the handler for the slash command to set default org and repo
@app.command("/set-default")
def set_default_org_repo_command(ack, body, client, command):
    ack()  # Acknowledge the slash command request
    user_id = body["user_id"]
    text = command["text"]
    # Parse organization and repository from the command
    org, repo = text.split()
    # Set default org and repo for the user
    set_default_org_repo(user_id, org, repo)
    # Send a confirmation message visible only to the user
    client.chat_postEphemeral(user=user_id, text=f"Default organization set to `{org}` and repository set to `{repo}`.")

# Define the handler for the slash command to get default org and repo
@app.command("/get-default")
def get_default_org_repo_command(ack, body, client):
    ack()  # Acknowledge the slash command request
    user_id = body["user_id"]
    # Get default org and repo for the user
    default_org, default_repo = get_default_org_repo(user_id)
    # Send the default org and repo information visible only to the user
    client.chat_postEphemeral(user=user_id, text=f"Default organization: `{default_org}`, Default repository: `{default_repo}`.")

# Start the app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
