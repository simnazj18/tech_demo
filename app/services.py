import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from kubernetes import client, config
import base64

class SecretScanner:
    def __init__(self, vault_url: str):
        self.vault_url = vault_url
        self._init_azure()
        self._init_k8s()

    def _init_azure(self):
        try:
            credential = DefaultAzureCredential()
            # Validate credential functionality
            # credential.get_token("https://vault.azure.net/.default") 
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
                    if s.expires_on < now:
                        expiry_status = "Expired"
                    else:
                        delta = s.expires_on - now
                        days_remaining = delta.days
                        if days_remaining <= 1:
                            expiry_status = "Expiring Soon (Auto-Rotation Triggered)"
                            # TODO: Call self.rotate_secret(s.name) here
                
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
                pod_name = pod.metadata.name
                # Check volumes for secrets
                for volume in pod.spec.volumes:
                    if volume.secret:
                        usage_map.append({
                            "pod": pod_name,
                            "type": "Volume",
                            "secret_name": volume.secret.secret_name,
                            "mount_path": "N/A",
                            "value": None # Hard to read volume content without exec
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
                                    "type": "EnvVar",
                                    "secret_name": s_name,
                                    "key": s_key,
                                    "value": s_val
                                })
        except Exception as e:
            print(f"Error scanning K8s: {e}")
        
        return usage_map

    def get_dashboard_data(self):
        """Aggregate data for the dashboard."""
        akv_secrets = self.get_akv_secrets()
        k8s_usage = self.get_k8s_usage()
        
        # Simple correlation: Map K8s secret names to AKV secret names 
        # (Assuming 1:1 naming for this demo, or some mapping logic)
        
        dashboard_rows = []
        for usage in k8s_usage:
            # Find matching AKV secret
            k8s_secret_name = usage['secret_name']
            
            # Fuzzy match or direct match? Let's try direct match first.
            # In a real scenario, K8s secret might be 'db-pass' but AKV is 'DatabasePassword'
            # We'll just look for *any* AKV secret that might be relevant or list them side-by-side.
            
            # For now, let's just create a flat list of "Detected Usage"
            dashboard_rows.append({
                "service_pod": usage['pod'],
                "mechanism": usage['type'],
                "k8s_secret": usage['secret_name'],
                "akv_status": "Unknown (No Mapping)" 
            })
            
            # Attempt to find if this K8s secret exists in AKV (by name)
            # Match by Value (Intelligent Detection)
            match_found = False
            
            # First, try to match by value if we have it
            if usage.get('value'):
                for akv in akv_secrets:
                    if akv.get('value') == usage.get('value'):
                        dashboard_rows[-1]['akv_status'] = f"Synced with: {akv['name']}"
                        dashboard_rows[-1]['akv_value'] = akv['value']
                        match_found = True
                        break
            
            # Fallback to name matching if value not found or not available (e.g. Volume)
            if not match_found:
                 for akv in akv_secrets:
                    if akv['name'].lower() in k8s_secret_name.lower():
                         dashboard_rows[-1]['akv_status'] = f"Found: {akv['name']}"
                         dashboard_rows[-1]['akv_value'] = akv['value']
                         break

        return {
            "akv_secrets": akv_secrets,
            "k8s_usage": dashboard_rows
        }
