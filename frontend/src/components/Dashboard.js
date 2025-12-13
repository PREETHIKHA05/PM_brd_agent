import React, { useState } from 'react';
import BRDUpload from './BRDUpload';
import RiskReview from './RiskReview';
import Questions from './Questions';
import Stories from './Stories';

function Dashboard({ user, onLogout }) {
    const [activeStep, setActiveStep] = useState('upload');
    const [workflowData, setWorkflowData] = useState({
        brdId: null,
        riskReviewId: null,
        runId: null,
        originalBrd: '',
        updatedBrd: '',
        suggestions: [],
        questions: [],
        answers: {},
        stories: null
    });

    const steps = [
        { id: 'upload', label: '1. Upload BRD' },
        { id: 'review', label: '2. Risk Review' },
        { id: 'questions', label: '3. Clarifying Questions' },
        { id: 'stories', label: '4. User Stories' }
    ];

    const handleStepComplete = (step, data) => {
        setWorkflowData(prev => ({ ...prev, ...data }));

        const currentIndex = steps.findIndex(s => s.id === step);
        if (currentIndex < steps.length - 1) {
            setActiveStep(steps[currentIndex + 1].id);
        }
    };

    return (
        <div className="dashboard">
            <aside className="sidebar">
                <div className="sidebar-header">
                    <h1 className="sidebar-title">PM Agent</h1>
                    <div className="sidebar-user">Welcome, {user.username}</div>
                </div>

                <div className="sidebar-section">
                    <h3 className="section-title">Workflow</h3>
                    <div className="workflow-steps">
                        {steps.map((step, index) => (
                            <div
                                key={step.id}
                                className={`step ${activeStep === step.id ? 'active' : ''}`}
                                onClick={() => workflowData.brdId && setActiveStep(step.id)}
                            >
                                {step.label}
                            </div>
                        ))}
                    </div>
                </div>

                <div className="sidebar-section" style={{ marginTop: 'auto' }}>
                    <button onClick={onLogout} className="btn btn-secondary" style={{ background: 'rgba(255,255,255,0.1)', color: 'white', border: 'none' }}>
                        Sign Out
                    </button>
                </div>
            </aside>

            <main className="main-content">
                {activeStep === 'upload' && (
                    <BRDUpload
                        onComplete={(data) => handleStepComplete('upload', data)}
                    />
                )}

                {activeStep === 'review' && (
                    <RiskReview
                        data={workflowData}
                        onComplete={(data) => handleStepComplete('review', data)}
                    />
                )}

                {activeStep === 'questions' && (
                    <Questions
                        data={workflowData}
                        onComplete={(data) => handleStepComplete('questions', data)}
                    />
                )}

                {activeStep === 'stories' && (
                    <Stories
                        data={workflowData}
                    />
                )}
            </main>
        </div>
    );
}

export default Dashboard;
