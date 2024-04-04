## Bot!

### Background

This is actually just created to see how much more useful info and usability you can get out of a GitHub integration with Slack.

### Information

This Slack bot should output a message with `Approve` and `Request Changes` buttons to your channel whenever a PR is created.  
The message also includes links to the file diffs in the PR. When Approve or Request Changes is clicked, the buttons change to `Merge`/`Squash`.  
Once either button is clicked at that stage, we replace the buttons with a message that the PR has been merged.
It also offers a comment button (like the official integration).

### Setup

You'll need:
- A GitHub App with token to access your team and repo (needs to be able to read teams)
- An Okta token to access your team members
- A Slack app that has permissions to send, edit and retrieve history from a supposed private Slack channel

Fill in everything in config.yaml and in deployment.yml if you are using GCF
  - or use the same keys in the .yaml file as env vars wherever you host this
  - Run the workflow!

Setup a gcloud function and edit your Slack app for interaction and events  
Wait for any output!
