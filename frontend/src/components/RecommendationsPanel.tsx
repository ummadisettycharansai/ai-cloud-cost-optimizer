import { Lightbulb, ArrowRight, Server, Database, Cloud } from 'lucide-react';
import { motion } from 'framer-motion';

export default function RecommendationsPanel({ recommendations }: { recommendations: any[] }) {
  if (!recommendations || recommendations.length === 0) {
     return (
        <div className="bg-surface border border-zinc-800 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="w-5 h-5 text-zinc-500" />
              <h3 className="text-lg font-bold">Smart Optimizations</h3>
            </div>
            <p className="text-zinc-500 text-sm">Infrastructure is fully optimized.</p>
        </div>
     );
  }

  const getIcon = (service: string) => {
    if (service.includes('EC2')) return <Server className="w-4 h-4" />;
    if (service.includes('RDS')) return <Database className="w-4 h-4" />;
    return <Cloud className="w-4 h-4" />;
  }

  return (
    <div className="bg-surface border border-zinc-800 rounded-xl p-5 shadow-sm flex flex-col h-full">
      <div className="flex items-center gap-2 mb-4">
         <Lightbulb className="w-5 h-5 text-warning" />
         <h3 className="text-lg font-bold">Smart Optimizations</h3>
      </div>
      
      <div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar">
         {recommendations.map((rec, idx) => (
           <motion.div 
              key={idx}
              whileHover={{ scale: 1.01 }}
              className="p-4 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-warning/50 transition-colors cursor-pointer group"
           >
              <div className="flex justify-between items-start mb-2">
                 <div className="flex items-center gap-2 text-zinc-300 font-medium text-sm">
                    {getIcon(rec.service_name)}
                    {rec.service_name}
                 </div>
                 <div className="text-success text-sm font-bold">
                    Save ${rec.estimated_savings}/mo
                 </div>
              </div>
              <p className="text-sm text-zinc-400 leading-snug">
                 {rec.description}
              </p>
              
              <div className="mt-3 flex items-center gap-2 text-xs font-semibold text-warning opacity-0 group-hover:opacity-100 transition-opacity">
                 Apply Recommendation <ArrowRight className="w-3 h-3" />
              </div>
           </motion.div>
         ))}
      </div>
    </div>
  );
}
