import React, { useState, useEffect } from 'react';
import { finalizeRiskReview } from '../services/api';
import { getErrorMessage } from '../utils/errorHandler';

function RiskReview({ data, onComplete }) {
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (data.suggestions) {
            setSuggestions(data.suggestions.map(s => ({
                ...s,
                status: s.status || 'pending'
            })));
        }
    }, [data.suggestions]);

    const handleStatusChange = (index, status) => {
        const newSuggestions = [...suggestions];
        newSuggestions[index].status = status;
        setSuggestions(newSuggestions);
    };

    const handleCommentChange = (index, comment) => {
        const newSuggestions = [...suggestions];
        newSuggestions[index].comment = comment;
        setSuggestions(newSuggestions);
    };

    const handleSubmit = async () => {
        setLoading(true);
        setError('');

        try {
            const response = await finalizeRiskReview(data.riskReviewId, suggestions);
            const { updated_brd } = response.data;

            onComplete({
                updatedBrd: updated_brd,
                suggestions: suggestions
            });
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to finalize review'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="content-card">
            <h2 className="page-title">Risk Review</h2>
            <p className="page-subtitle">Review and accept AI-generated suggestions to improve your BRD.</p>

            {error && <div className="error-message">{error}</div>}

            <div className="grid-2">
                <div>
                    <h3 className="section-title" style={{ color: '#4a5568' }}>Suggestions</h3>
                    {suggestions.map((suggestion, index) => (
                        <div key={index} className="suggestion-card">
                            <div className="suggestion-header">
                                {index + 1}. {suggestion.category}
                            </div>

                            <textarea
                                className="form-input"
                                value={suggestion.comment}
                                onChange={(e) => handleCommentChange(index, e.target.value)}
                                rows={3}
                            />

                            <div className="suggestion-actions">
                                <button
                                    className={`btn btn-small ${suggestion.status === 'accepted' ? 'btn-accept' : 'btn-secondary'}`}
                                    onClick={() => handleStatusChange(index, 'accepted')}
                                >
                                    Accept
                                </button>
                                <button
                                    className={`btn btn-small ${suggestion.status === 'rejected' ? 'btn-reject' : 'btn-secondary'}`}
                                    onClick={() => handleStatusChange(index, 'rejected')}
                                >
                                    Reject
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                <div>
                    <h3 className="section-title" style={{ color: '#4a5568' }}>Original BRD</h3>
                    <div className="textarea-large" style={{ background: '#f7fafc', fontSize: '0.9rem' }}>
                        {data.originalBrd}
                    </div>
                </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2rem' }}>
                <button
                    className="btn btn-primary"
                    style={{ width: 'auto' }}
                    onClick={handleSubmit}
                    disabled={loading}
                >
                    {loading ? 'Finalizing...' : 'Finalize & Continue'}
                </button>
            </div>
        </div>
    );
}

export default RiskReview;
