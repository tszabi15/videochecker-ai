import React from 'react';
import { CheckCircle2, Circle, Loader2, Clock } from 'lucide-react';
import { JobStatus } from '../../types';

export interface StageDefinition {
  id: JobStatus;
  name: string;
  desc: string;
}

interface StatusStepperProps {
  stages: StageDefinition[];
  currentStatus: JobStatus;
  isQuotaLimited: boolean;
}

const STAGE_ORDER: JobStatus[] = [
  'QUEUED', 'PREPROCESSING', 'TRANSCRIBING', 'ANALYZING', 'VALIDATING', 'FINALIZING', 'DONE',
];

export const StatusStepper: React.FC<StatusStepperProps> = ({ stages, currentStatus, isQuotaLimited }) => {
  const currentIndex = STAGE_ORDER.indexOf(currentStatus);

  const getStageState = (stageId: JobStatus): 'completed' | 'active' | 'pending' | 'failed' => {
    const stageIndex = STAGE_ORDER.indexOf(stageId);
    if (currentStatus === 'FAILED') return 'failed';
    if (currentStatus === 'DONE') return 'completed';
    if (stageIndex < currentIndex) return 'completed';
    if (stageIndex === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="space-y-6 relative before:absolute before:left-3 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800/80">
      {stages.map((stg) => {
        const state = getStageState(stg.id);
        const isBlockedByQuota = state === 'active' && isQuotaLimited;

        return (
          <div key={stg.id} className="flex items-start gap-4 relative z-10">
            <div className="mt-0.5 bg-slate-950 p-1 rounded-full">
              {state === 'completed' && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
              {state === 'active' && !isBlockedByQuota && <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />}
              {state === 'active' && isBlockedByQuota && <Clock className="w-6 h-6 text-amber-400 animate-bounce" />}
              {state === 'pending' && <Circle className="w-6 h-6 text-slate-700" />}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className={`font-semibold text-base ${
                  state === 'active'
                    ? isBlockedByQuota ? 'text-amber-300' : 'text-indigo-300'
                    : state === 'completed' ? 'text-slate-200' : 'text-slate-500'
                }`}>
                  {stg.name}
                </h3>
                {state === 'active' && !isBlockedByQuota && (
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 animate-pulse">
                    In Progress
                  </span>
                )}
                {isBlockedByQuota && (
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/30 text-amber-300 animate-pulse">
                    Backed Off
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">{stg.desc}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
