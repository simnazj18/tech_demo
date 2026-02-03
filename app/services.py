import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from kubernetes import client, config
import base64


class SecretScanner:
    def __init__(self, vault_url: str, client_id: str = None, client_secret: str = None, tenant_id: str = None):
        self.vault_url = vault_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self._init_azure()
        self._init_k8s()


    def _init_azure(self):
        try:
            if self.client_id and self.client_secret and self.tenant_id:
                credential = ClientSecretCredential(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    tenant_id=self.tenant_id
                )
                print(f"Using Client Secret Credential for {self.vault_url}")
            else:
                credential = DefaultAzureCredential()
                print("Using Default Azure Credential")
                
            self.kv_client = SecretClient(vault_url=self.vault_url, credential=credential)
            print(f"Azure Key Vault Client initialized for {self.vault_url}")
        except Exception as e:
            print(f"Failed to init Azure: {e}")
            self.kv_client = None

    def _init_k8s(self):
        try:
            # Try loading in-cluster config first, then local kubeconfig
            try:
                config.load_incluster_config()
                print("Loaded K8s in-cluster config.")
            except config.ConfigException:
                config.load_kube_config()
                print("Loaded K8s local kube config.")
            
            self.v1 = client.CoreV1Api()
        except Exception as e:
            print(f"Failed to load K8s config: {e}")
            self.v1 = None

    def get_akv_secrets(self) -> List[Dict[str, Any]]:
        """Fetch all secret metadata from Azure Key Vault."""
        if not self.kv_client:
            return [{"name": "Error: Azure not connected", "enabled": False, "value": None}]
        
        secrets = []
        try:
            secret_properties = self.kv_client.list_properties_of_secrets()
            for s in secret_properties:
                # Fetch the value
                try:
                    secret_value = self.kv_client.get_secret(s.name).value
                except Exception:
                    secret_value = "**ACCESS DENIED**"
                
                # Calculate Expiry Status
                expiry_status = "Healthy"
                days_remaining = None
                
                if s.expires_on:
                    now = datetime.now(timezone.utc)
                    delta = s.expires_on - now
                    days_remaining = delta.days
                    
                    if delta.days < 0: # Expired
                         expiry_status = "Expired"
                         days_remaining = 0 # or negative? Let's keep 0 for simplified logic
                    elif days_remaining <= 2:
                        expiry_status = "Critical" # < 2 days
                    elif days_remaining <= 7:
                        expiry_status = "Warning" # < 7 days
                
                secrets.append({
                    "name": s.name,
                    "value": secret_value,
                    "enabled": s.enabled,
                    "updated_on": s.updated_on,
                    "expires_on": s.expires_on,
                    "status": expiry_status,
                    "days_remaining": days_remaining
                })
        except Exception as e:
            print(f"Error listing AKV secrets: {e}")
            return []
        return secrets

    def get_k8s_usage(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """Scan Pods to find which K8s secrets are being used."""
        if not self.v1:
            return []

        usage_map = []
        secret_cache = {} # Cache secret data to avoid repetitive API calls

        try:
            # List all pods
            pods = self.v1.list_namespaced_pod(namespace)
            for pod in pods.items:
                # Skip Terminating Pods
                if pod.metadata.deletion_timestamp:
                    continue

                pod_name = pod.metadata.name
                
                # Find Deployment Name (Owner Reference)
                deployment_name = None
                if pod.metadata.owner_references:
                    for ref in pod.metadata.owner_references:
                        if ref.kind == "ReplicaSet":
                            # Typically RS name is deploy-hash, so we need to find RS parent or guess
                            # For simplicity in this demo, strict mapping or look up RS owner
                            # Let's try to get the RS to find the Deployment
                            try:
                                apps_v1 = client.AppsV1Api()
                                rs = apps_v1.read_namespaced_replica_set(ref.name, namespace)
                                if rs.metadata.owner_references:
                                    deployment_name = rs.metadata.owner_references[0].name
                            except:
                                deployment_name = None 

                # Check volumes for secrets
                for volume in pod.spec.volumes:
                    if volume.secret:
                        usage_map.append({
                            "pod": pod_name,
                            "deployment": deployment_name,
                            "type": "Volume",
                            "secret_name": volume.secret.secret_name,
                            "mount_path": "N/A",
                            "value": None
                        })
                
                # Check env vars for secrets
                for container in pod.spec.containers:
                    if container.env:
                        for env in container.env:
                            if env.value_from and env.value_from.secret_key_ref:
                                s_name = env.value_from.secret_key_ref.name
                                s_key = env.value_from.secret_key_ref.key
                                
                                # Fetch value from K8s
                                s_val = None
                                if s_name not in secret_cache:
                                    try:
                                        k8s_secret = self.v1.read_namespaced_secret(s_name, namespace)
                                        secret_cache[s_name] = k8s_secret.data or {}
                                    except Exception:
                                        secret_cache[s_name] = {}
                                
                                if s_name in secret_cache and s_key in secret_cache[s_name]:
                                    try:
                                        s_val = base64.b64decode(secret_cache[s_name][s_key]).decode('utf-8')
                                    except:
                                        s_val = "**DECODE ERROR**"

                                usage_map.append({
                                    "pod": pod_name,
                                    "deployment": deployment_name,
                                    "type": "EnvVar",
                                    "secret_name": s_name,
                                    "key": s_key,
                                    "value": s_val
                                })
        except Exception as e:
            print(f"Error scanning K8s: {e}")
        
        return usage_map

    def get_dashboard_data(self):
        """Aggregate data for the dashboard (Flat Layout)."""
        print("DEBUG: Starting AKV Scan...")
        akv_secrets = self.get_akv_secrets()
        print(f"DEBUG: AKV Scan Complete. Found {len(akv_secrets)} secrets.")
        
        print("DEBUG: Starting K8s Scan...")
        k8s_usage = self.get_k8s_usage()
        print(f"DEBUG: K8s Scan Complete. Found {len(k8s_usage)} usages.")
        
        dashboard_rows = []
        for usage in k8s_usage:
            row = {
                "service_pod": usage['pod'],
                "deployment": usage.get('deployment'),
                "mechanism": usage['type'],
                "k8s_secret": usage['secret_name'],
                "akv_status": "Unknown (No Mapping)",
                "akv_name_ref": None,
                "akv_value": None,
                "akv_expiry_status": "Unknown",
                "days_remaining": None
            }
            
            match_found = False
            
            # 1. Exact Value Match
            if usage.get('value'):
                for akv in akv_secrets:
                    if akv.get('value') == usage.get('value'):
                        row['akv_status'] = f"Synced with: {akv['name']}"
                        row['akv_value'] = akv['value']
                        row['akv_name_ref'] = akv['name']
                        row['akv_expiry_status'] = akv['status']
                        row['days_remaining'] = akv['days_remaining']
                        match_found = True
                        break
            
            # 2. Key/Name Heuristic Match
            if not match_found:
                 for akv in akv_secrets:
                    name_match = akv['name'].lower() in usage['secret_name'].lower()
                    key_match = False
                    if usage.get('key'):
                        if usage['key'].lower() in akv['name'].lower():
                            key_match = True
                    
                    if name_match or key_match:
                         # Drift or Found
                         row['akv_status'] = f"Drift: {akv['name']}"
                         row['akv_value'] = akv['value']
                         row['akv_name_ref'] = akv['name']
                         row['akv_expiry_status'] = akv['status']
                         row['days_remaining'] = akv['days_remaining']
                         break
            
            dashboard_rows.append(row)

        return {
            "akv_secrets": akv_secrets,
            "k8s_usage": dashboard_rows
        }

    def rotate_secret(self, akv_secret_name: str, k8s_secret_name: str = None, deployment_name: str = None, namespace: str = "default", new_secret_value: str = None, new_expiry_date: datetime = None):
        """
        Safe Rotation Workflow:
        1. Generate New Secret (or use provided)
        2. Set Expiry Date (if provided)
        3. Update AKV (New Version)
        4. Update K8s Secret (if mapped)
        5. Restart Deployment (to pick up new secret)
        """
        import secrets
        import string

        print(f"Starting rotation for {akv_secret_name}...")
        
        # 1. Generate New Secret (if not provided)
        if not new_secret_value:
            alphabet = string.ascii_letters + string.digits + "!@#$%"
            new_secret_value = ''.join(secrets.choice(alphabet) for i in range(32))
            print("Generated random secret value.")
        else:
            print("Using user-provided new secret value.")
        
        # 2. Update AKV
        if self.kv_client:
            try:
                # set_secret creates a new version. We can pass expires_on.
                self.kv_client.set_secret(akv_secret_name, new_secret_value, expires_on=new_expiry_date)
                print(f"AKV Secret {akv_secret_name} updated successfully (Expires: {new_expiry_date}).")
            except Exception as e:
                return {"success": False, "message": f"Failed to update AKV: {e}"}
        else:
             return {"success": False, "message": "AKV Client not initialized"}

        # 3. Update K8s Secret (if mapped)
        if k8s_secret_name and self.v1:
            try:
                # Encode value
                encoded_value = base64.b64encode(new_secret_value.encode('utf-8')).decode('utf-8')
                
                # We need to find the KEY in the K8s secret that maps to this AKV secret.
                # For this demo, we can try to infer it or just update specific keys if known.
                # LIMITATION: We don't know the exact key from the dashboard row data passed here easily unless we lookup.
                # Let's fetch the secret first to see keys.
                k8s_secret = self.v1.read_namespaced_secret(k8s_secret_name, namespace)
                
                if k8s_secret.data:
                    # HEURISTIC: Update ALL keys that have "password" in name OR just update the first key?
                    # Better: Update the key that matches the AKV name?
                    # For Demo: lets update 'password' or 'secret' or just the first key if single.
                    
                    target_key = None
                    for key in k8s_secret.data:
                        if 'password' in key.lower() or 'secret' in key.lower() or akv_secret_name.lower() in key.lower():
                            target_key = key
                            break
                    
                    if not target_key and len(k8s_secret.data) > 0:
                        target_key = list(k8s_secret.data.keys())[0] # Fallback to first key
                        
                    if target_key:
                        patch_body = {
                            "data": {
                                target_key: encoded_value
                            }
                        }
                        self.v1.patch_namespaced_secret(k8s_secret_name, namespace, patch_body)
                        print(f"K8s Secret {k8s_secret_name} (key: {target_key}) updated.")
                    else:
                        print("Could not determine key to update in K8s Secret.")
            except Exception as e:
                print(f"Failed to update K8s secret: {e}")
                # We continue to restart deployment anyway, though it might fail to pick up new val.

        # 4. Restart Deployment
        if deployment_name:
            try:
                # Trigger rollout restart via patch (annotation)
                apps_v1 = client.AppsV1Api()
                now = datetime.now(timezone.utc).isoformat()
                patch_body = {
                    "spec": {
                        "template": {
                            "metadata": {
                                "annotations": {
                                    "kubectl.kubernetes.io/restartedAt": now
                                }
                            }
                        }
                    }
                }
                apps_v1.patch_namespaced_deployment(deployment_name, namespace, patch_body)
                print(f"Deployment {deployment_name} restarted.")
            except Exception as e:
                return {"success": True, "message": f"Secret rotated but Deployment restart failed: {e}"}

        return {"success": True, "message": f"Successfully rotated {akv_secret_name} and restarted services."}
