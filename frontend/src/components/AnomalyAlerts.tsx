import { AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function AnomalyAlerts({ anomalies }: { anomalies: any[] }) {
  if (!anomalies || anomalies.length === 0) {
    return (
       <div className="bg-surface border border-zinc-800 rounded-xl p-5">
           <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-zinc-500" />
              <h3 className="text-lg font-bold">Anomaly Alerts</h3>
           </div>
           <p className="text-zinc-500 text-sm">No recent cost anomalies detected.</p>
       </div>
    );
  }

  return (
    <div className="bg-surface border border-zinc-800 rounded-xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
         <AlertTriangle className="w-5 h-5 text-danger" />
         <h3 className="text-lg font-bold">Anomaly Alerts</h3>
         <span className="ml-auto bg-danger/10 text-danger text-xs px-2 py-1 rounded-full font-medium">
            {anomalies.length} New
         </span>
      </div>
      
      <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
         <AnimatePresence>
            {anomalies.map((anomaly, idx) => (
              <motion.div 
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-3 rounded-lg border l-4 text-sm ${
                    anomaly.severity === 'high' ? 'bg-danger/5 border-danger border-l-4 text-danger' :
                    anomaly.severity === 'medium' ? 'bg-warning/5 border-warning border-l-4 text-warning' :
                    'bg-primary/5 border-primary border-l-4 text-primary'
                }`}
              >
                 <div className="flex justify-between items-start">
                    <span className="font-semibold text-zinc-200">Cost Spike Detected</span>
                    <span className="text-xs opacity-70">{anomaly.date}</span>
                 </div>
                 <p className="mt-1 text-zinc-400">
                    Expected ~${anomaly.expected || 'N/A'}, Actual: <span className="font-bold text-zinc-200">${anomaly.cost}</span>
                 </p>
              </motion.div>
            ))}
         </AnimatePresence>
      </div>
    </div>
  );
}
