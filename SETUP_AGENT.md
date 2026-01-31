# Setting Up Your Self-Hosted Azure DevOps Agent

Since Microsoft's hosted agents are blocked, we will turn your current machine into a build agent.

## 1. Create the Agent Pool (In Azure DevOps)
1.  Go to **Project Settings** (Bottom Left).
2.  Under **Pipelines**, click **Agent pools**.
3.  Click **Add pool**.
    *   **Pool type**: `Self-hosted`
    *   **Name**: `MyLaptopPool`
    *   **Description**: `Local agent`
    *   Check **"Grant access permission to all pipelines"**.
    *   Click **Create**.

## 2. Get a Personal Access Token (PAT)
1.  Click the **User Settings** icon (Top Right, next to your profile picture).
2.  Click **Personal access tokens**.
3.  Click **New Token**.
    *   **Name**: `AgentToken`
    *   **Scopes**: Select **Running tasks in Agent Pools** (or *Full Access* if easiest).
    *   Click **Create**.
4.  **COPY THIS TOKEN IMMEDIATELY**. You will need it in the next step.

## 3. Install and Run the Agent (In Terminal)
Run these commands in a **new terminal tab** (`Ctrl+Shift+5`):

```bash
# 1. Create a folder for the agent
mkdir myagent && cd myagent

# 2. Download the agent (Linux x64)
wget https://vstsagentpackage.azureedge.net/agent/3.232.0/vsts-agent-linux-x64-3.232.0.tar.gz

# 3. Extract it
tar zxvf vsts-agent-linux-x64-3.232.0.tar.gz

# 4. Configure it (Interactive Step)
./config.sh
```

**During Configuration, answer these prompts:**
*   **Server URL**: `https://dev.azure.com/{your-organization-name}` (e.g., https://dev.azure.com/johndoe)
*   **Authentication type**: Press Enter (default is PAT).
*   **PAT**: Paste the token you copied in Step 2.
*   **Agent Pool**: Enter `MyLaptopPool`.
*   **Agent Name**: Press Enter (default is fine).
*   **Work folder**: Press Enter.

## 4. Start the Agent
Once configured, start it:
```bash
./run.sh
```
*Leave this terminal running!* It is now listening for jobs.

## 5. Rerun the Pipeline
Go back to your pipeline in Azure DevOps and click **"Run"**. It should meaningful pick up use your local machine to build and deploy!
