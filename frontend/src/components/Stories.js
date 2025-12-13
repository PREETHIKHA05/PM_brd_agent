import React, { useState } from 'react';

function Stories({ data }) {
    const [activeTab, setActiveTab] = useState('stories');

    let storiesData = data.stories;
    if (typeof storiesData === 'string') {
        try {

            const cleanJson = storiesData.replace(/```json\n?|```/g, '');
            storiesData = JSON.parse(cleanJson);
        } catch (e) {
            console.error("Failed to parse stories JSON", e);

            storiesData = { epics: [], stories: [], nfrs: [] };
        }
    }

    const { epics = [], stories = [], nfrs = [] } = storiesData || {};

    return (
        <div className="content-card">
            <h2 className="page-title">Generated User Stories</h2>
            <p className="page-subtitle">Here are the generated Epics, User Stories, and NFRs based on your BRD.</p>

            <div className="metric-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                <div className="metric-card">
                    <div className="metric-value">{epics.length}</div>
                    <div className="metric-label">Epics</div>
                </div>
                <div className="metric-card" style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' }}>
                    <div className="metric-value">{stories.length}</div>
                    <div className="metric-label">User Stories</div>
                </div>
                <div className="metric-card" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' }}>
                    <div className="metric-value">{nfrs.length}</div>
                    <div className="metric-label">NFRs</div>
                </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', borderBottom: '2px solid #e2e8f0' }}>
                <button
                    className={`btn ${activeTab === 'stories' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ width: 'auto', borderRadius: '10px 10px 0 0', borderBottom: 'none' }}
                    onClick={() => setActiveTab('stories')}
                >
                    User Stories
                </button>
                <button
                    className={`btn ${activeTab === 'epics' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ width: 'auto', borderRadius: '10px 10px 0 0', borderBottom: 'none' }}
                    onClick={() => setActiveTab('epics')}
                >
                    Epics
                </button>
                <button
                    className={`btn ${activeTab === 'nfrs' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ width: 'auto', borderRadius: '10px 10px 0 0', borderBottom: 'none' }}
                    onClick={() => setActiveTab('nfrs')}
                >
                    NFRs
                </button>
            </div>

            <div className="tab-content">
                {activeTab === 'stories' && (
                    <div className="stories-list">
                        {stories.map((story, index) => (
                            <div key={index} className="story-card">
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                    <div className="story-title">{story.id}: {story.i_want}</div>
                                    <span style={{
                                        padding: '0.25rem 0.75rem',
                                        borderRadius: '20px',
                                        fontSize: '0.8rem',
                                        fontWeight: '600',
                                        background: story.priority === 'High' ? '#fee2e2' : story.priority === 'Medium' ? '#fef3c7' : '#d1fae5',
                                        color: story.priority === 'High' ? '#991b1b' : story.priority === 'Medium' ? '#92400e' : '#065f46'
                                    }}>
                                        {story.priority} Priority
                                    </span>
                                </div>

                                <div className="story-content">
                                    <p><strong>As a</strong> {story.as_a}</p>
                                    <p><strong>I want to</strong> {story.i_want}</p>
                                    <p><strong>So that</strong> {story.so_that}</p>

                                    <div style={{ marginTop: '1rem' }}>
                                        <strong>Acceptance Criteria:</strong>
                                        <ul style={{ paddingLeft: '1.5rem', marginTop: '0.5rem' }}>
                                            {story.acceptance_criteria.map((ac, i) => (
                                                <li key={i}>
                                                    {typeof ac === 'string' ? ac : JSON.stringify(ac)}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {activeTab === 'epics' && (
                    <div className="epics-list">
                        {epics.map((epic, index) => (
                            <div key={index} className="story-card">
                                <div className="story-title">
                                    {typeof epic.id === 'string' ? epic.id : JSON.stringify(epic.id)}: {typeof epic.name === 'string' ? epic.name : JSON.stringify(epic.name)}
                                </div>
                                <div className="story-content">
                                    <p><strong>Related Stories:</strong></p>
                                    <ul style={{ paddingLeft: '1.5rem', marginTop: '0.5rem' }}>
                                        {stories.filter(s => s.epic_id === epic.id).map((s, i) => (
                                            <li key={i}>
                                                {typeof s.id === 'string' ? s.id : JSON.stringify(s.id)}: {typeof s.i_want === 'string' ? s.i_want : JSON.stringify(s.i_want)}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {activeTab === 'nfrs' && (
                    <div className="nfrs-list">
                        <div className="story-card">
                            <h3 className="story-title">Non-Functional Requirements</h3>
                            <ul style={{ paddingLeft: '1.5rem' }}>
                                {nfrs.map((nfr, index) => (
                                    <li key={index} style={{ marginBottom: '0.5rem', color: '#4a5568' }}>
                                        {typeof nfr === 'string' ? nfr : JSON.stringify(nfr)}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default Stories;
