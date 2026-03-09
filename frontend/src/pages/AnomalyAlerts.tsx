import AnomalyAlertsComponent from '../components/AnomalyAlerts';

export default function AnomalyAlerts({ anomalies }: any) {
  return (
    <div className="p-6 max-w-7xl mx-auto w-full">
      <h1 className="text-2xl font-bold mb-6">Cost Anomalies</h1>
      <AnomalyAlertsComponent anomalies={anomalies} />
    </div>
  );
}
