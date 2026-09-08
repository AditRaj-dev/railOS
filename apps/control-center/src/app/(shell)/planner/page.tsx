'use client';

import React, { Suspense } from 'react';
import { BlockPlannerView } from '@/components/BlockPlannerView';

export default function PlannerPage() {
  return (
    <Suspense fallback={null}>
      <BlockPlannerView />
    </Suspense>
  );
}
