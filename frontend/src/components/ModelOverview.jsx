import React, { useState, useEffect } from 'react';
import { apiClient } from '../utils/api';
import { useWebSocket } from '../hooks/useWebSocket';

const ModelOverview = () => {
  const [modelInfo, setModelInfo] = useState(null);
  const [health, setHealth] = useState(null);
  const [driftReport, setDriftReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const { lastMessage, connectionStatus } = useWebSocket();

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [modelData, healthData, driftData] = await Promise.all([
        apiClient.getModelInfo(),
        apiClient.getHealth(),
        apiClient.getDriftReport(1)
      ]);
      
      setModelInfo(modelData);
      setHealth(healthData);
      setDriftReport(driftData);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading...</div>
      </div>
    );
  }

  const getHealthColor = (status) => {
    switch (status) {
      case 'healthy': return 'bg-green-500';
      case 'warning': return 'bg-yellow-500';
      case 'critical': return 'bg-red-500';
      default: return 'bg-slate-500';
    }
  };

  const getHealthStatus = () => {
    if (!driftReport || !driftReport.overall_status) return 'unknown';
    return driftReport.overall_status.health;
  };

  return (
    <div className="space-y-6">
      {/* System Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">System Health</p>
              <p className="text-2xl font-bold text-white mt-1 capitalize">
                {getHealthStatus()}
              </p>
            </div>
            <div className={`w-12 h-12 rounded-full ${getHealthColor(getHealthStatus())} flex items-center justify-center`}>
              <span className="text-2xl">
                {getHealthStatus() === 'healthy' ? '✓' : getHealthStatus() === 'warning' ? '⚠' : '✗'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">WebSocket</p>
              <p className="text-2xl font-bold text-white mt-1 capitalize">
                {connectionStatus}
              </p>
            </div>
            <div className={`w-3 h-3 rounded-full ${
              connectionStatus === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-slate-500'
            }`}></div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Predictions (1h)</p>
              <p className="text-2xl font-bold text-white mt-1">
                {driftReport?.total_predictions || 0}
              </p>
            </div>
            <div className="text-3xl">📊</div>
          </div>
        </div>
      </div>

      {/* Model Information */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">Model Information</h3>
        {modelInfo && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-slate-400">Version</p>
              <p className="text-white font-mono">{modelInfo.version}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">Type</p>
              <p className="text-white">{modelInfo.model_type}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">Features</p>
              <p className="text-white">{modelInfo.feature_count}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">Training Samples</p>
              <p className="text-white">{modelInfo.training_samples?.toLocaleString()}</p>
            </div>
          </div>
        )}
      </div>

      {/* Performance Metrics */}
      {modelInfo?.metrics && (
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Model Performance (Training)</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <MetricCard label="Accuracy" value={modelInfo.metrics.accuracy} />
            <MetricCard label="Precision" value={modelInfo.metrics.precision} />
            <MetricCard label="Recall" value={modelInfo.metrics.recall} />
            <MetricCard label="F1 Score" value={modelInfo.metrics.f1} />
            <MetricCard label="AUC-ROC" value={modelInfo.metrics.auc_roc} />
          </div>
        </div>
      )}

      {/* Alerts Summary */}
      {driftReport?.alerts && driftReport.alerts.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Recent Alerts</h3>
          <div className="space-y-3">
            {driftReport.alerts.map((alert, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${
                  alert.severity === 'high'
                    ? 'bg-red-500/10 border-red-500/50'
                    : alert.severity === 'medium'
                    ? 'bg-yellow-500/10 border-yellow-500/50'
                    : 'bg-blue-500/10 border-blue-500/50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-white font-medium">{alert.type.replace('_', ' ').toUpperCase()}</p>
                    <p className="text-sm text-slate-300 mt-1">{alert.message}</p>
                    {alert.recommendation && (
                      <p className="text-xs text-slate-400 mt-2">
                        💡 {alert.recommendation}
                      </p>
                    )}
                  </div>
                  <span
                    className={`px-2 py-1 text-xs rounded ${
                      alert.severity === 'high'
                        ? 'bg-red-500 text-white'
                        : alert.severity === 'medium'
                        ? 'bg-yellow-500 text-black'
                        : 'bg-blue-500 text-white'
                    }`}
                  >
                    {alert.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const MetricCard = ({ label, value }) => {
  const percentage = value ? (value * 100).toFixed(2) : 'N/A';
  const color = value > 0.9 ? 'text-green-400' : value > 0.8 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div>
      <p className="text-sm text-slate-400">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>
        {value ? `${percentage}%` : 'N/A'}
      </p>
    </div>
  );
};

export default ModelOverview;

