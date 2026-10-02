const LABELS = {
  processed: 'Processed',
  processing: 'Processing',
  failed: 'Failed',
  'needs-review': 'Needs review',
}

export default function Badge({ status }) {
  return <span className={'badge ' + status}>{LABELS[status]}</span>
}
