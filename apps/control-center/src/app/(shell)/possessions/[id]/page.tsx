'use client';

import { useParams } from 'next/navigation';
import { PossessionDetailView } from '../../../../components/PossessionDetailView';

export default function PossessionDetailPage() {
  const params = useParams<{ id?: string }>();
  const possessionId = params?.id ? decodeURIComponent(params.id) : '';

  return <PossessionDetailView possessionId={possessionId} />;
}
