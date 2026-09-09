import { EvidenceGalleryView } from '@/components/EvidenceGalleryView';

export const metadata = {
  title: 'Evidence Verification — Photos & Videos | Railblock Control Center',
  description: 'Visual gallery of captured field evidence media for geospatial and cryptographic verification',
};

export default function EvidenceMediaPage() {
  return <EvidenceGalleryView />;
}
