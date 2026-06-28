import React from 'react';

interface ScoreCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  colorClass?: string;
  large?: boolean;
  children?: React.ReactNode;
}

export const ScoreCard: React.FC<ScoreCardProps> = ({
  label, value, sublabel, colorClass = 'text-indigo-400', large = false, children,
}) => {
  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 text-center flex flex-col justify-between">
      <span className="text-xs font-semibold text-slate-400 uppercase">{label}</span>
      {children ? (
        <div className="my-2 flex justify-center">{children}</div>
      ) : (
        <div className={`${large ? 'text-4xl' : 'text-3xl'} font-extrabold font-mono ${colorClass} my-2`}>
          {typeof value === 'number' ? value.toFixed(1) : value}
        </div>
      )}
      {sublabel && <span className="text-[10px] text-slate-500">{sublabel}</span>}
    </div>
  );
};
