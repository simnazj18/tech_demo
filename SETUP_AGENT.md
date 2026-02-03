# Setting Up Your Self-Hosted Agent (The Easy Docker Way)

We will run the agent inside a Docker container. This avoids all the network/download issues we faced earlier.

## 1. Create the Agent Pool (If you haven't already)
1.  Go to Azure DevOps -> **Project Settings** -> **Agent pools**.
2.  Add pool -> **Self-hosted** -> Name: `MyLaptopPool`.
3.  Check **"Grant access permission to all pipelines"**.

## 2. Get a Personal Access Token (PAT)
1.  User Settings (Top Right) -> **Personal access tokens**.
2.  **New Token** -> Name: `AgentToken` -> **Full Access** (for simplicity).
3.  **COPY THIS TOKEN**.

## 3. Run the Agent
Copy and paste this command into your terminal. Replace `{org}` and `{token}` with your details.

```bash
# Example: https://dev.azure.com/johndoe
export AZP_URL="https://dev.azure.com/{YOUR_ORG_NAME}"
export AZP_TOKEN="{YOUR_PAT_TOKEN}"
export AZP_POOL="MyLaptopPool"

docker run -d --restart always --name myagent \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e AZP_URL=$AZP_URL \
  -e AZP_TOKEN=$AZP_TOKEN \
  -e AZP_POOL=$AZP_POOL \
  mcr.microsoft.com/azure-pipelines/vsts-agent:latest
```

**Why the `-v` flag?**
We mount `/var/run/docker.sock` so the agent can verify use *your* Docker to build the dashboard images.

## 4. Verify
1.  Run `docker logs -f myagent` to see it connecting.
2.  Go to Azure DevOps -> Pipelines -> Run your pipeline again.
