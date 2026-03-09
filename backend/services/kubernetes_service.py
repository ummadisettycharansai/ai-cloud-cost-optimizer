import logging
import random

logger = logging.getLogger(__name__)

class KubernetesService:
    def __init__(self):
        self.use_mock = True
        
    def fetch_namespace_costs(self):
        """
        Simulates fetching cost breakdowns by namespace using tools like Kubecost
        """
        namespaces = ["production", "staging", "development", "kube-system"]
        
        costs = []
        for ns in namespaces:
             costs.append({
                 "cluster_name": "primary-eks-cluster",
                 "namespace": ns,
                 "monthly_cost": round(random.uniform(100, 1500), 2),
                 "cpu_utilization": round(random.uniform(20, 90), 2),
                 "memory_utilization": round(random.uniform(30, 85), 2)
             })
        return costs
