import React, { useState, useEffect } from 'react';
import {
  getIntegrationsStatus,
  connectSlack,
  connectGitHub,
  connectDiscord,
  connectGmail,
  connectGoogleDrive,
  getGitHubRepos,
  syncSlack,
  syncGitHub,
  syncDiscord,
  syncGmail,
  syncGoogleDrive,
  syncAll,
} from '../lib/api';
import type { IntegrationStatusItem, GitHubRepo } from '../lib/types';
import './LiveIntegrationsModal.css';

interface LiveIntegrationsModalProps {
  isOpen: boolean;
  onClose: () => void;
  userName: string;
  userId: string;
  onUserChange: (name: string, id: string) => void;
  onSyncComplete?: () => void;
}

type ToolkitKey = 'slack' | 'github' | 'discord' | 'gmail' | 'googledrive';

const TOOLKIT_META: Record<ToolkitKey, { label: string; icon: string; desc: string; color: string }> = {
  slack:       { label: 'Slack',         icon: '💬', desc: 'Channels, threaded conversations & attachments',  color: '#4a154b' },
  github:      { label: 'GitHub',        icon: '🐙', desc: 'Repositories, pull requests & issues',           color: '#161b22' },
  discord:     { label: 'Discord',       icon: '🎮', desc: 'Server channels, messages & embeds',             color: '#5865f2' },
  gmail:       { label: 'Gmail',         icon: '✉️',  desc: 'Inbox emails, threads & attachments',           color: '#ea4335' },
  googledrive: { label: 'Google Drive',  icon: '📂', desc: 'Docs, Sheets, Slides & text files',             color: '#0f9d58' },
};

export default function LiveIntegrationsModal({
  isOpen,
  onClose,
  userName,
  userId,
  onUserChange,
  onSyncComplete,
}: LiveIntegrationsModalProps) {
  const [nameInput, setNameInput] = useState(userName);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [integrations, setIntegrations] = useState<IntegrationStatusItem[]>([]);
  const [syncingSource, setSyncingSource] = useState<string | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncDetails, setSyncDetails] = useState<any>(null);

  // GitHub repo selection
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [selectedRepos, setSelectedRepos] = useState<string[]>([]);
  const [repoSearch, setRepoSearch] = useState('');

  // Gmail query config
  const [gmailQuery, setGmailQuery] = useState('label:inbox');

  // Drive query config
  const [driveQuery, setDriveQuery] = useState('');

  // Discord guild id (optional override)
  const [discordGuildId, setDiscordGuildId] = useState('');

  const computeUserId = (name: string) =>
    name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');

  const handleSaveName = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanName = nameInput.trim();
    if (!cleanName) return;
    onUserChange(cleanName, computeUserId(cleanName));
  };

  const fetchRepos = async (uid: string) => {
    setLoadingRepos(true);
    try {
      const res = await getGitHubRepos(uid);
      const fetched = res.repositories || [];
      setRepos(fetched);
      setSelectedRepos((prev) =>
        prev.length === 0 && fetched.length > 0 ? fetched.map((r) => r.full_name || r.name) : prev,
      );
    } catch (err) {
      console.error('Failed to fetch GitHub repos', err);
    } finally {
      setLoadingRepos(false);
    }
  };

  const fetchStatus = async () => {
    if (!userId) return;
    setLoadingStatus(true);
    try {
      const res = await getIntegrationsStatus(userId);
      setIntegrations(res.integrations || []);
      const gh = (res.integrations || []).find((i) => i.toolkit.toLowerCase() === 'github');
      if (gh && gh.status === 'ACTIVE') fetchRepos(userId);
    } catch (err) {
      console.error('Failed to fetch integrations status', err);
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setNameInput(userName);
      if (userId) fetchStatus();
    }
  }, [isOpen, userId]);

  const getStatus = (toolkit: string): IntegrationStatusItem =>
    integrations.find((i) => i.toolkit.toLowerCase() === toolkit.toLowerCase()) || {
      toolkit,
      status: 'DISCONNECTED',
    };

  const toggleRepo = (repoKey: string) =>
    setSelectedRepos((prev) =>
      prev.includes(repoKey) ? prev.filter((k) => k !== repoKey) : [...prev, repoKey],
    );

  const ensureUserId = (): string | null => {
    let effectiveUserId = userId;
    if (!effectiveUserId && nameInput.trim()) {
      effectiveUserId = computeUserId(nameInput);
      onUserChange(nameInput.trim(), effectiveUserId);
    }
    if (!effectiveUserId) {
      setSyncMessage('Please enter and save your name first to create your personal workspace.');
      return null;
    }
    return effectiveUserId;
  };

  const handleConnect = async (toolkit: ToolkitKey) => {
    const uid = ensureUserId();
    if (!uid) return;
    try {
      const connectFns: Record<ToolkitKey, () => Promise<any>> = {
        slack:       () => connectSlack(uid),
        github:      () => connectGitHub(uid),
        discord:     () => connectDiscord(uid),
        gmail:       () => connectGmail(uid),
        googledrive: () => connectGoogleDrive(uid),
      };
      const res = await connectFns[toolkit]();
      if (res.auth_url) {
        window.open(res.auth_url, '_blank', 'width=800,height=700');
        setSyncMessage(
          `Opened authorization window for ${TOOLKIT_META[toolkit].label}. Complete authentication, then click 'Refresh Status'.`,
        );
      }
    } catch (err: any) {
      setSyncMessage(`Failed to initiate ${TOOLKIT_META[toolkit].label} connection: ${err.message || err}`);
    }
  };

  const handleSync = async (toolkit: ToolkitKey | 'all') => {
    const uid = ensureUserId();
    if (!uid) return;

    setSyncingSource(toolkit);
    setSyncMessage(null);
    setSyncDetails(null);
    try {
      let res: any;
      const targetRepos = selectedRepos.length > 0 ? selectedRepos : undefined;

      switch (toolkit) {
        case 'slack':
          res = await syncSlack(uid);
          break;
        case 'github':
          res = await syncGitHub(uid, { selectedRepos: targetRepos });
          break;
        case 'discord':
          res = await syncDiscord(uid, { guildId: discordGuildId || undefined });
          break;
        case 'gmail':
          res = await syncGmail(uid, { query: gmailQuery });
          break;
        case 'googledrive':
          res = await syncGoogleDrive(uid, { query: driveQuery || undefined });
          break;
        case 'all':
          res = await syncAll(uid, { selectedRepos: targetRepos });
          break;
      }

      setSyncDetails(res);
      const label = toolkit === 'all' ? 'all connected sources' : TOOLKIT_META[toolkit as ToolkitKey].label;
      setSyncMessage(`Successfully synchronized ${label} into your personal HydraDB graph!`);
      if (onSyncComplete) onSyncComplete();
      fetchStatus();
    } catch (err: any) {
      setSyncMessage(`Sync failed: ${err.message || err}`);
    } finally {
      setSyncingSource(null);
    }
  };

  if (!isOpen) return null;

  const statusMap = Object.fromEntries(
    (Object.keys(TOOLKIT_META) as ToolkitKey[]).map((k) => [k, getStatus(k)]),
  ) as Record<ToolkitKey, IntegrationStatusItem>;

  const isActive = (k: ToolkitKey) => statusMap[k].status === 'ACTIVE';
  const anyActive = (Object.keys(TOOLKIT_META) as ToolkitKey[]).some(isActive);

  const filteredRepos = repos.filter((r) => {
    const q = repoSearch.toLowerCase();
    return (
      (r.name && r.name.toLowerCase().includes(q)) ||
      (r.full_name && r.full_name.toLowerCase().includes(q)) ||
      (r.description && r.description.toLowerCase().includes(q))
    );
  });

  const statusPillLabel = (status: string) => {
    if (status === 'ACTIVE') return '🟢 Connected';
    if (status === 'INITIATED') return '🟡 Authorizing';
    return '⚪ Disconnected';
  };

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        {/* ── Header ── */}
        <div className="modal-header">
          <div>
            <h2>Personal Workspace &amp; Live Integrations</h2>
            <p className="modal-subtitle">
              Connect your SaaS accounts to ingest live data into your private HydraDB knowledge graph.
            </p>
          </div>
          <button className="btn-close" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        <div className="modal-body">
          {/* ── Workspace Identity ── */}
          <section className="user-profile-section">
            <form onSubmit={handleSaveName} className="user-profile-form">
              <div className="field-group">
                <label htmlFor="user-name-input">Enter Your Name / Workspace Identity</label>
                <div className="input-with-action">
                  <input
                    id="user-name-input"
                    type="text"
                    className="field"
                    value={nameInput}
                    onChange={(e) => {
                      setNameInput(e.target.value);
                      const clean = e.target.value.trim();
                      if (clean) onUserChange(clean, computeUserId(clean));
                    }}
                    placeholder="e.g. Alice Chen, Alex Morgan, Engineering"
                    required
                  />
                  <button type="submit" className="btn btn-primary">
                    Save
                  </button>
                </div>
              </div>
              <p className="user-id-badge">
                Isolated Workspace ID:{' '}
                <code>{userId || (nameInput.trim() ? computeUserId(nameInput) : 'Not configured yet')}</code>
              </p>
            </form>
          </section>

          {/* ── Integrations Grid — row 1: Slack + GitHub ── */}
          <div className="integrations-section-label">Communication &amp; Code</div>
          <div className="integrations-grid">
            {(['slack', 'github'] as ToolkitKey[]).map((tk) => {
              const info = statusMap[tk];
              const meta = TOOLKIT_META[tk];
              const active = isActive(tk);
              return (
                <div key={tk} className={`integration-card ${active ? 'card-active' : ''}`}>
                  <div className="card-top">
                    <div className="app-icon" style={{ background: `${meta.color}33` }}>
                      {meta.icon}
                    </div>
                    <div>
                      <h3>{meta.label}</h3>
                      <p className="app-desc">{meta.desc}</p>
                    </div>
                    <span className={`status-pill pill-${info.status.toLowerCase()}`}>
                      {statusPillLabel(info.status)}
                    </span>
                  </div>

                  {info.account_name && (
                    <div className="account-info">
                      Account: <strong>{info.account_name}</strong>
                    </div>
                  )}

                  <div className="card-actions">
                    <button
                      className={`btn btn-sm ${active ? 'btn-outline' : 'btn-primary'}`}
                      onClick={() => handleConnect(tk)}
                    >
                      {active ? `Reconnect` : `Connect ${meta.label}`}
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      disabled={!active || syncingSource !== null}
                      onClick={() => handleSync(tk)}
                    >
                      {syncingSource === tk ? 'Syncing...' : `Sync`}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* ── GitHub repo picker (when connected) ── */}
          {isActive('github') && (
            <section className="repo-selection-section">
              <div className="repo-header">
                <div>
                  <h4>Select Repositories to Sync</h4>
                  <p className="repo-subtitle">
                    Only selected repos and their PRs/issues will be ingested into HydraDB.
                  </p>
                </div>
                <div className="repo-bulk-actions">
                  <span className="selected-count-badge">
                    {selectedRepos.length} of {repos.length} selected
                  </span>
                  <button type="button" className="btn-link" onClick={() => setSelectedRepos(repos.map((r) => r.full_name || r.name))}>
                    Select All
                  </button>
                  <button type="button" className="btn-link" onClick={() => setSelectedRepos([])}>
                    Clear
                  </button>
                </div>
              </div>
              {repos.length > 5 && (
                <input
                  type="search"
                  className="field field-sm repo-search-input"
                  placeholder="Filter repositories..."
                  value={repoSearch}
                  onChange={(e) => setRepoSearch(e.target.value)}
                />
              )}
              {loadingRepos ? (
                <div className="repo-loading">Loading your GitHub repositories...</div>
              ) : repos.length === 0 ? (
                <div className="repo-empty">No accessible repositories found.</div>
              ) : (
                <div className="repo-list">
                  {filteredRepos.map((repo) => {
                    const key = repo.full_name || repo.name;
                    const isChecked = selectedRepos.includes(key);
                    return (
                      <label key={key} className={`repo-item ${isChecked ? 'repo-item-selected' : ''}`}>
                        <input type="checkbox" checked={isChecked} onChange={() => toggleRepo(key)} />
                        <div className="repo-meta">
                          <div className="repo-name-row">
                            <span className="repo-full-name">{key}</span>
                            {repo.private && <span className="pill-private">Private</span>}
                          </div>
                          {repo.description && <p className="repo-desc">{repo.description}</p>}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          {/* ── Row 2: Discord + Gmail + Google Drive ── */}
          <div className="integrations-section-label">Messaging &amp; Files</div>
          <div className="integrations-grid integrations-grid-3">
            {(['discord', 'gmail', 'googledrive'] as ToolkitKey[]).map((tk) => {
              const info = statusMap[tk];
              const meta = TOOLKIT_META[tk];
              const active = isActive(tk);
              return (
                <div key={tk} className={`integration-card ${active ? 'card-active' : ''}`}>
                  <div className="card-top">
                    <div className="app-icon" style={{ background: `${meta.color}33` }}>
                      {meta.icon}
                    </div>
                    <div>
                      <h3>{meta.label}</h3>
                      <p className="app-desc">{meta.desc}</p>
                    </div>
                    <span className={`status-pill pill-${info.status.toLowerCase()}`}>
                      {statusPillLabel(info.status)}
                    </span>
                  </div>

                  {info.account_name && (
                    <div className="account-info">
                      Account: <strong>{info.account_name}</strong>
                    </div>
                  )}

                  {/* Per-integration config ── Discord guild ID */}
                  {tk === 'discord' && active && (
                    <input
                      type="text"
                      className="field field-sm"
                      placeholder="Guild ID (optional — auto-detects)"
                      value={discordGuildId}
                      onChange={(e) => setDiscordGuildId(e.target.value)}
                    />
                  )}

                  {/* Per-integration config ── Gmail search query */}
                  {tk === 'gmail' && active && (
                    <input
                      type="text"
                      className="field field-sm"
                      placeholder="Gmail search (e.g. label:inbox)"
                      value={gmailQuery}
                      onChange={(e) => setGmailQuery(e.target.value)}
                    />
                  )}

                  {/* Per-integration config ── Drive query */}
                  {tk === 'googledrive' && active && (
                    <input
                      type="text"
                      className="field field-sm"
                      placeholder="Drive query (optional, e.g. type:document)"
                      value={driveQuery}
                      onChange={(e) => setDriveQuery(e.target.value)}
                    />
                  )}

                  <div className="card-actions">
                    <button
                      className={`btn btn-sm ${active ? 'btn-outline' : 'btn-primary'}`}
                      onClick={() => handleConnect(tk)}
                    >
                      {active ? 'Reconnect' : `Connect ${meta.label}`}
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      disabled={!active || syncingSource !== null}
                      onClick={() => handleSync(tk)}
                    >
                      {syncingSource === tk ? 'Syncing...' : 'Sync'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* ── Sync All Bar ── */}
          <div className="sync-all-bar">
            <button className="btn btn-outline btn-sm" onClick={fetchStatus} disabled={loadingStatus}>
              {loadingStatus ? 'Checking...' : '🔄 Refresh Status'}
            </button>

            {anyActive ? (
              <button
                className="btn btn-primary"
                disabled={syncingSource !== null}
                onClick={async () => {
                  await handleSync('all');
                  setTimeout(() => onClose(), 1200);
                }}
              >
                {syncingSource === 'all' ? 'Ingesting & Vectorizing...' : '🚀 Start Live Ingestion & Launch Dashboard'}
              </button>
            ) : (
              <p className="sync-hint muted small">
                Connect at least one source above to enable live ingestion.
              </p>
            )}
          </div>

          {/* ── Sync Status Banner ── */}
          {syncMessage && (
            <div className={`sync-banner ${syncMessage.toLowerCase().includes('fail') ? 'banner-error' : 'banner-success'}`}>
              <p>{syncMessage}</p>
              {syncDetails && (
                <div className="sync-summary-pills">
                  {syncDetails.documents_synced !== undefined && (
                    <span>📄 {syncDetails.documents_synced} Docs</span>
                  )}
                  {syncDetails.chunks_vectorized !== undefined && (
                    <span>🧩 {syncDetails.chunks_vectorized} Chunks</span>
                  )}
                  {syncDetails.facts_extracted !== undefined && (
                    <span>💡 {syncDetails.facts_extracted} Facts</span>
                  )}
                  {syncDetails.resolution && (
                    <span>
                      🔗 {syncDetails.resolution.same_as_edges} SAME_AS · ⚡{' '}
                      {syncDetails.resolution.supersedes_edges} SUPERSEDES
                    </span>
                  )}
                  {syncDetails.results && (
                    Object.entries(syncDetails.results as Record<string, any>).map(([src, r]: [string, any]) => (
                      r?.documents_synced != null && (
                        <span key={src}>
                          {TOOLKIT_META[src as ToolkitKey]?.icon ?? '📦'} {r.documents_synced} {src}
                        </span>
                      )
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {userId ? (
            <button
              type="button"
              className="btn btn-sm btn-danger-outline"
              onClick={async () => {
                const ok = window.confirm(
                  `Purge all live data for workspace '${userId}'?\n\nThis will delete all ingested graph nodes, vector embeddings, and staged files from HydraDB.`,
                );
                if (ok) {
                  try {
                    const { purgeWorkspace } = await import('../lib/api');
                    await purgeWorkspace(userId);
                    setSyncMessage(`Successfully purged all data for workspace '${userId}'. You can now sync fresh.`);
                    setSyncDetails(null);
                    if (onSyncComplete) onSyncComplete();
                  } catch (err: any) {
                    setSyncMessage(`Failed to purge workspace: ${err.message || err}`);
                  }
                }
              }}
            >
              🗑️ Purge &amp; Reset Workspace
            </button>
          ) : (
            <div />
          )}
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
