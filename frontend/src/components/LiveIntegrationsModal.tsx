import React, { useState, useEffect } from 'react';
import {
  getIntegrationsStatus,
  connectSlack,
  connectGitHub,
  getGitHubRepos,
  syncSlack,
  syncGitHub,
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

  // GitHub repository selection state
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [selectedRepos, setSelectedRepos] = useState<string[]>([]);
  const [repoSearch, setRepoSearch] = useState('');

  // Derive slug ID from human name
  const computeUserId = (name: string) => {
    const slug = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    return slug;
  };

  const handleSaveName = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanName = nameInput.trim();
    if (!cleanName) return;
    const newId = computeUserId(cleanName);
    onUserChange(cleanName, newId);
  };

  const fetchRepos = async (uid: string) => {
    setLoadingRepos(true);
    try {
      const res = await getGitHubRepos(uid);
      const fetched = res.repositories || [];
      setRepos(fetched);
      // Select all by default on first load
      setSelectedRepos((prev) => (prev.length === 0 && fetched.length > 0 ? fetched.map((r) => r.full_name || r.name) : prev));
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
      if (gh && gh.status === 'ACTIVE') {
        fetchRepos(userId);
      }
    } catch (err) {
      console.error('Failed to fetch integrations status', err);
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setNameInput(userName);
      if (userId) {
        fetchStatus();
      }
    }
  }, [isOpen, userId]);

  const getStatus = (toolkit: string): IntegrationStatusItem => {
    return integrations.find((i) => i.toolkit.toLowerCase() === toolkit.toLowerCase()) || {
      toolkit,
      status: 'DISCONNECTED',
    };
  };

  const toggleRepo = (repoKey: string) => {
    setSelectedRepos((prev) =>
      prev.includes(repoKey) ? prev.filter((k) => k !== repoKey) : [...prev, repoKey],
    );
  };

  const handleSelectAllRepos = () => {
    setSelectedRepos(repos.map((r) => r.full_name || r.name));
  };

  const handleDeselectAllRepos = () => {
    setSelectedRepos([]);
  };

  const handleConnect = async (toolkit: 'slack' | 'github') => {
    let effectiveUserId = userId;
    if (!effectiveUserId && nameInput.trim()) {
      effectiveUserId = computeUserId(nameInput);
      onUserChange(nameInput.trim(), effectiveUserId);
    }
    if (!effectiveUserId) {
      setSyncMessage('Please enter and save your name first to create your personal workspace.');
      return;
    }
    try {
      const res = toolkit === 'slack' ? await connectSlack(effectiveUserId) : await connectGitHub(effectiveUserId);
      if (res.auth_url) {
        window.open(res.auth_url, '_blank', 'width=800,height=700');
        setSyncMessage(`Opened authorization window for ${toolkit.toUpperCase()}. Complete authentication and click 'Refresh Status'.`);
      }
    } catch (err: any) {
      setSyncMessage(`Failed to initiate ${toolkit} connection: ${err.message || err}`);
    }
  };

  const handleSync = async (toolkit: 'slack' | 'github' | 'all') => {
    let effectiveUserId = userId;
    if (!effectiveUserId && nameInput.trim()) {
      effectiveUserId = computeUserId(nameInput);
      onUserChange(nameInput.trim(), effectiveUserId);
    }
    if (!effectiveUserId) {
      setSyncMessage('Please enter and save your name first to create your personal workspace.');
      return;
    }

    setSyncingSource(toolkit);
    setSyncMessage(null);
    setSyncDetails(null);
    try {
      let res;
      const targetRepos = selectedRepos.length > 0 ? selectedRepos : undefined;

      if (toolkit === 'slack') {
        res = await syncSlack(effectiveUserId);
      } else if (toolkit === 'github') {
        res = await syncGitHub(effectiveUserId, { selectedRepos: targetRepos });
      } else {
        res = await syncAll(effectiveUserId, { selectedRepos: targetRepos });
      }

      setSyncDetails(res);
      setSyncMessage(`Successfully synchronized ${toolkit.toUpperCase()} data into your personal HydraDB graph!`);
      if (onSyncComplete) {
        onSyncComplete();
      }
      fetchStatus();
    } catch (err: any) {
      setSyncMessage(`Sync failed: ${err.message || err}`);
    } finally {
      setSyncingSource(null);
    }
  };

  if (!isOpen) return null;

  const slackInfo = getStatus('slack');
  const githubInfo = getStatus('github');

  const isSlackActive = slackInfo.status === 'ACTIVE';
  const isGithubActive = githubInfo.status === 'ACTIVE';

  const filteredRepos = repos.filter((r) => {
    const q = repoSearch.toLowerCase();
    return (
      (r.name && r.name.toLowerCase().includes(q)) ||
      (r.full_name && r.full_name.toLowerCase().includes(q)) ||
      (r.description && r.description.toLowerCase().includes(q))
    );
  });

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2>Personal Workspace & Live Integrations</h2>
            <p className="modal-subtitle">
              Connect your own SaaS accounts. You can select specific repositories to sync into Company Brain.
            </p>
          </div>
          <button className="btn-close" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        <div className="modal-body">
          {/* User Name / Workspace Configuration */}
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
                      if (clean) {
                        onUserChange(clean, computeUserId(clean));
                      }
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
                Isolated Workspace ID: <code>{userId || (nameInput.trim() ? computeUserId(nameInput) : 'Not configured yet')}</code>
              </p>
            </form>
          </section>

          {/* Integrations Cards Grid */}
          <div className="integrations-grid">
            {/* Slack Card */}
            <div className={`integration-card ${isSlackActive ? 'card-active' : ''}`}>
              <div className="card-top">
                <div className="app-icon slack-icon">💬</div>
                <div>
                  <h3>Slack</h3>
                  <p className="app-desc">Channels, threaded conversations & attachments</p>
                </div>
                <span className={`status-pill pill-${slackInfo.status.toLowerCase()}`}>
                  {slackInfo.status === 'ACTIVE' ? '🟢 Connected' : (slackInfo.status === 'INITIATED' ? '🟡 Authorizing' : '⚪ Disconnected')}
                </span>
              </div>

              {slackInfo.account_name && (
                <div className="account-info">
                  Account: <strong>{slackInfo.account_name}</strong>
                </div>
              )}

              <div className="card-actions">
                <button
                  className={`btn btn-sm ${isSlackActive ? 'btn-outline' : 'btn-primary'}`}
                  onClick={() => handleConnect('slack')}
                >
                  {isSlackActive ? 'Reconnect Slack' : 'Connect Slack'}
                </button>

                <button
                  className="btn btn-sm btn-secondary"
                  disabled={!isSlackActive || syncingSource !== null}
                  onClick={() => handleSync('slack')}
                >
                  {syncingSource === 'slack' ? 'Syncing...' : 'Sync Slack'}
                </button>
              </div>
            </div>

            {/* GitHub Card */}
            <div className={`integration-card ${isGithubActive ? 'card-active' : ''}`}>
              <div className="card-top">
                <div className="app-icon github-icon">🐙</div>
                <div>
                  <h3>GitHub</h3>
                  <p className="app-desc">Repositories, pull requests & issues</p>
                </div>
                <span className={`status-pill pill-${githubInfo.status.toLowerCase()}`}>
                  {githubInfo.status === 'ACTIVE' ? '🟢 Connected' : (githubInfo.status === 'INITIATED' ? '🟡 Authorizing' : '⚪ Disconnected')}
                </span>
              </div>

              {githubInfo.account_name && (
                <div className="account-info">
                  Account: <strong>{githubInfo.account_name}</strong>
                </div>
              )}

              <div className="card-actions">
                <button
                  className={`btn btn-sm ${isGithubActive ? 'btn-outline' : 'btn-primary'}`}
                  onClick={() => handleConnect('github')}
                >
                  {isGithubActive ? 'Reconnect GitHub' : 'Connect GitHub'}
                </button>

                <button
                  className="btn btn-sm btn-secondary"
                  disabled={!isGithubActive || syncingSource !== null}
                  onClick={() => handleSync('github')}
                >
                  {syncingSource === 'github' ? 'Syncing...' : 'Sync Selected Repos'}
                </button>
              </div>
            </div>
          </div>

          {/* GitHub Repository Selection Panel (when GitHub is Connected) */}
          {isGithubActive && (
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
                  <button type="button" className="btn-link" onClick={handleSelectAllRepos}>
                    Select All
                  </button>
                  <button type="button" className="btn-link" onClick={handleDeselectAllRepos}>
                    Clear
                  </button>
                </div>
              </div>

              {repos.length > 5 && (
                <input
                  type="search"
                  className="field field-sm repo-search-input"
                  placeholder="Filter repositories by name or description..."
                  value={repoSearch}
                  onChange={(e) => setRepoSearch(e.target.value)}
                />
              )}

              {loadingRepos ? (
                <div className="repo-loading">Loading your GitHub repositories...</div>
              ) : repos.length === 0 ? (
                <div className="repo-empty">No accessible repositories found for this account.</div>
              ) : (
                <div className="repo-list">
                  {filteredRepos.map((repo) => {
                    const key = repo.full_name || repo.name;
                    const isChecked = selectedRepos.includes(key);
                    return (
                      <label key={key} className={`repo-item ${isChecked ? 'repo-item-selected' : ''}`}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleRepo(key)}
                        />
                        <div className="repo-meta">
                          <div className="repo-name-row">
                            <span className="repo-full-name">{repo.full_name || repo.name}</span>
                            {repo.private && <span className="pill-private">Private</span>}
                          </div>
                          {repo.description && (
                            <p className="repo-desc">{repo.description}</p>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          {/* Combined Sync Actions */}
          <div className="sync-all-bar">
            <button className="btn btn-outline btn-sm" onClick={fetchStatus} disabled={loadingStatus}>
              {loadingStatus ? 'Checking...' : '🔄 Refresh Connection Status'}
            </button>

            {(isSlackActive || isGithubActive) ? (
              <button
                className="btn btn-primary"
                disabled={syncingSource !== null}
                onClick={async () => {
                  await handleSync('all');
                  setTimeout(() => {
                    onClose();
                  }, 1200);
                }}
              >
                {syncingSource === 'all' ? 'Ingesting & Vectorizing...' : '🚀 Start Live Ingestion & Launch Dashboard'}
              </button>
            ) : (
              <p className="sync-hint muted small">
                Connect your Slack or GitHub account above to enable live ingestion.
              </p>
            )}
          </div>

          {/* Sync Status Banner & Summary */}
          {syncMessage && (
            <div className={`sync-banner ${syncMessage.includes('failed') ? 'banner-error' : 'banner-success'}`}>
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
                    <span>🔗 {syncDetails.resolution.same_as_edges} SAME_AS · ⚡ {syncDetails.resolution.supersedes_edges} SUPERSEDES</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
