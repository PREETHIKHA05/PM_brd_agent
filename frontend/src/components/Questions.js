import React, { useState, useEffect } from 'react';
import { generateQuestions, generateStories } from '../services/api';
import { getErrorMessage } from '../utils/errorHandler';

function Questions({ data, onComplete }) {
    const [questions, setQuestions] = useState([]);
    const [answers, setAnswers] = useState({});
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState('');
    const [runId, setRunId] = useState(null);

    useEffect(() => {
        const fetchQuestions = async () => {
            setGenerating(true);
            try {
                const response = await generateQuestions(data.riskReviewId);
                setQuestions(response.data.questions);
                setRunId(response.data.run_id);

                const initialAnswers = {};
                response.data.questions.forEach(q => {
                    initialAnswers[q] = '';
                });
                setAnswers(initialAnswers);
            } catch (err) {
                setError('Failed to generate questions');
            } finally {
                setGenerating(false);
            }
        };

        if (!data.questions || data.questions.length === 0) {
            fetchQuestions();
        } else {
            setQuestions(data.questions);
            setAnswers(data.answers || {});
        }
    }, [data.riskReviewId, data.questions, data.answers]);

    const handleAnswerChange = (question, answer) => {
        setAnswers(prev => ({
            ...prev,
            [question]: answer
        }));
    };
    const handleSubmit = async () => {
        setLoading(true);
        setError('');

        try {
            const response = await generateStories(runId, answers);

            onComplete({
                runId: runId,
                questions: questions,
                answers: answers,
                stories: response.data.stories
            });
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to generate stories'));
        } finally {
            setLoading(false);
        }
    };

    if (generating) {
        return (
            <div className="content-card">
                <div className="loading">
                    <div className="spinner"></div>
                    <p>Analyzing BRD and generating clarifying questions...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="content-card">
            <h2 className="page-title">Clarifying Questions</h2>
            <p className="page-subtitle">Please answer these questions to help generate better user stories.</p>

            {error && <div className="error-message">{error}</div>}

            <div className="questions-list">
                {questions.map((question, index) => (
                    <div key={index} className="question-card">
                        <div className="question-number">Question {index + 1}</div>
                        <div className="question-text">{question}</div>
                        <textarea
                            className="form-input"
                            value={answers[question] || ''}
                            onChange={(e) => handleAnswerChange(question, e.target.value)}
                            placeholder="Type your answer here..."
                            rows={3}
                        />
                    </div>
                ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2rem' }}>
                <button
                    className="btn btn-primary"
                    style={{ width: 'auto' }}
                    onClick={handleSubmit}
                    disabled={loading}
                >
                    {loading ? 'Generating Stories...' : 'Generate User Stories'}
                </button>
            </div>
        </div>
    );
}

export default Questions;
