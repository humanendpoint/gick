## Bot!

Screenshots soon!

### Background

This is actually just created to see how much more useful info and usability you can get out of a GitHub integration with Slack.

### Features

When a GitHub PR is created:
  - we should output a message with `Approve` and `Request Changes` buttons to your channel
    - Assigned users tagged by Slack ID (approx match GH user vs Okta email)
    - includes links to the file diffs in the PR
    - kinda sorta imitates the official integration output design
  - includes a comment button (like the official integration)
  - when `Approve` or `Request Changes` is clicked, the buttons change to `Merge`/`Squash`.  
    - Once either button is clicked at that stage, we replace the buttons with a message that the PR has been merged/squashed.
  - tests for PR check results and waits until runs are done to update the initial message
  - more to come!

### Setup

#### You'll need:
- A GitHub App with token to access your team and repo (needs to be able to read teams)
- GitHub webhooks to trigger on Pull Requests
- An Okta token to access your team members
- A Slack app
  - permissions: send msg, edit and retrieve history from a supposed private Slack channel

#### Steps
1. Complete the `config.yaml` keys and edit `deployment.yml` if you are using GCF
      - or use the same keys in the `.yaml` file as env vars wherever you host this
      - Run the workflow!

2. Setup a gcloud function and edit your Slack app for interaction and events  
3. Wait for any output!
