/**
 * The documents the folder card fans out. Real source vocabulary from the
 * ingested corpus rather than colour swatches -- the card's whole claim is
 * "721 files from nine tools land in one format", and lorem tiles would
 * quietly undercut it.
 */
export interface SourceFile {
  id: string;
  source: string;
  title: string;
  /** A graph entity colour from tokens.css -- semantic, not decorative. */
  tint: string;
}

export const SOURCE_FILES: SourceFile[] = [
  { id: 'confluence', source: 'Confluence', title: 'Secret rotation runbook', tint: 'var(--n-document)' },
  { id: 'linear', source: 'Linear', title: 'ENG-4844 Rollback state machine', tint: 'var(--n-ticket)' },
  { id: 'slack', source: 'Slack', title: '#eng-releases', tint: 'var(--n-person)' },
  { id: 'gmail', source: 'Gmail', title: 'SDK retries and 429s', tint: 'var(--n-org)' },
  { id: 'github', source: 'GitHub', title: 'PR #42739 Stream resume', tint: 'var(--n-fact)' },
];
