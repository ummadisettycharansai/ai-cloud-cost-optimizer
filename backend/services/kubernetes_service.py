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
                 "monthly_cost": round(float(random.uniform(100, 1500)), 2),  # pyre-ignore[6]
                 "cpu_utilization": round(float(random.uniform(20, 90)), 2),  # pyre-ignore[6]
                 "memory_utilization": round(float(random.uniform(30, 85)), 2)  # pyre-ignore[6]
             })
        return costs
