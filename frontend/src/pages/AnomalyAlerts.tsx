import AnomalyAlertsComponent from '../components/AnomalyAlerts';
import { useAuth } from '../context/AuthContext';
import RestrictedCard from '../components/RestrictedCard';

export default function AnomalyAlerts({ anomalies }: any) {
  const { permissions } = useAuth();

  if (!permissions.canSeeAnomalies) {
    return (
      <div className="p-12 flex items-center justify-center h-full">
        <RestrictedCard title="Anomaly Detection Restricted" className="max-w-md" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto w-full">
      <h1 className="text-2xl font-bold mb-6">Cost Anomalies</h1>
      <AnomalyAlertsComponent anomalies={anomalies} />
    </div>
  );
}
