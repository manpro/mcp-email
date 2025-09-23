import React, { useState, useEffect } from 'react';
import './ModelSelector.css';

const ModelSelector = ({ apiUrl = 'http://localhost:3016' }) => {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);

  // Fetch available models
  const fetchModels = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiUrl}/api/models`);
      const data = await response.json();
      setModels(data.providers);

      // Find the currently active model
      const activeModel = data.providers.find(m => m.isActive && m.priority === 1);
      if (activeModel) {
        setSelectedModel(activeModel.id);
      }
    } catch (err) {
      setError('Failed to load models');
      console.error('Error fetching models:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  // Switch model
  const handleModelSwitch = async (modelId) => {
    try {
      setLoading(true);

      // First disable all other models
      for (const model of models) {
        if (model.id !== modelId && model.enabled) {
          await fetch(`${apiUrl}/api/models/switch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modelId: model.id, enabled: false })
          });
        }
      }

      // Then enable the selected model with highest priority
      await fetch(`${apiUrl}/api/models/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modelId, enabled: true })
      });

      await fetch(`${apiUrl}/api/models/priority`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modelId, priority: 1 })
      });

      setSelectedModel(modelId);
      await fetchModels(); // Refresh the list

      // Show success notification
      const notification = document.createElement('div');
      notification.className = 'model-notification success';
      notification.textContent = `Switched to ${models.find(m => m.id === modelId)?.name}`;
      document.body.appendChild(notification);

      setTimeout(() => {
        notification.remove();
      }, 3000);

    } catch (err) {
      setError('Failed to switch model');
      console.error('Error switching model:', err);
    } finally {
      setLoading(false);
    }
  };

  // Test model connectivity
  const testModel = async (modelId) => {
    try {
      const testEmail = {
        from: 'test@example.com',
        subject: 'Test Email for Model Verification',
        text: 'This is a test email to verify the AI model is working correctly.'
      };

      const response = await fetch(`${apiUrl}/api/categorize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testEmail)
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Model Test Successful!\n\nCategory: ${result.category}\nPriority: ${result.priority}\nProvider: ${result.provider || 'Unknown'}`);
      } else {
        alert('Model test failed');
      }
    } catch (err) {
      alert('Error testing model: ' + err.message);
    }
  };

  return (
    <div className="model-selector">
      <div className="model-selector-header">
        <h3>🤖 AI Model Selection</h3>
        <button onClick={fetchModels} className="refresh-btn" disabled={loading}>
          🔄 Refresh
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">Loading models...</div>
      ) : (
        <div className="models-grid">
          {models.map(model => (
            <div
              key={model.id}
              className={`model-card ${model.id === selectedModel ? 'selected' : ''} ${model.enabled ? 'enabled' : 'disabled'}`}
            >
              <div className="model-header">
                <h4>{model.name}</h4>
                <span className={`status-badge ${model.isActive ? 'active' : 'inactive'}`}>
                  {model.isActive ? '✅ Active' : '⭕ Inactive'}
                </span>
              </div>

              <div className="model-details">
                <p><strong>Model:</strong> {model.model}</p>
                <p><strong>URL:</strong> {model.url}</p>
                <p><strong>Priority:</strong> {model.priority}</p>
                <p><strong>Status:</strong> {model.enabled ? 'Enabled' : 'Disabled'}</p>
              </div>

              <div className="model-actions">
                <button
                  onClick={() => handleModelSwitch(model.id)}
                  disabled={loading || model.id === selectedModel}
                  className="switch-btn"
                >
                  {model.id === selectedModel ? '✓ Selected' : 'Select'}
                </button>
                <button
                  onClick={() => testModel(model.id)}
                  disabled={loading || !model.enabled}
                  className="test-btn"
                >
                  Test
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="model-selector-footer">
        <p>💡 Tip: Switching models will clear the cache to ensure new categorizations use the selected model.</p>
      </div>
    </div>
  );
};

export default ModelSelector;