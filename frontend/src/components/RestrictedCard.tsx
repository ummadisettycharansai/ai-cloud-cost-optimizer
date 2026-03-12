import React from 'react';
import { Lock } from 'lucide-react';

interface RestrictedCardProps {
    title?: string;
    message?: string;
    className?: string;
}

const RestrictedCard: React.FC<RestrictedCardProps> = ({
    title = "Restricted Access",
    message = "You don't have the required permissions to view this section.",
    className = ""
}) => {
    return (
        <div className={`bg-zinc-900/50 border border-zinc-800 rounded-xl p-8 flex flex-col items-center justify-center text-center gap-4 min-h-[200px] ${className}`}>
            <div className="p-4 bg-zinc-800 rounded-full">
                <Lock className="w-8 h-8 text-zinc-500" />
            </div>
            <div>
                <h3 className="text-zinc-200 font-semibold">{title}</h3>
                <p className="text-sm text-zinc-500 max-w-xs mx-auto mt-1">{message}</p>
            </div>
        </div>
    );
};

export default RestrictedCard;
