import React, { useState } from 'react';
import { uploadBRD } from '../services/api';
import { getErrorMessage } from '../utils/errorHandler';

function BRDUpload({ onComplete }) {
    const [text, setText] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async () => {
        if (!text.trim()) {
            setError('Please enter BRD content');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const response = await uploadBRD(text);
            const { brd_id, risk_review_id, suggestions } = response.data;

            onComplete({
                brdId: brd_id,
                riskReviewId: risk_review_id,
                originalBrd: text,
                suggestions: suggestions
            });
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to upload BRD'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="content-card">
            <h2 className="page-title">Upload BRD</h2>
            <p className="page-subtitle">Paste your Business Requirements Document below to start the analysis.</p>

            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
                <textarea
                    className="textarea-large"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Paste your BRD content here..."
                />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                    className="btn btn-primary"
                    style={{ width: 'auto' }}
                    onClick={handleSubmit}
                    disabled={loading}
                >
                    {loading ? 'Analyzing...' : 'Start Analysis'}
                </button>
            </div>
        </div>
    );
}

export default BRDUpload;
