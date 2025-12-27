import React, { useState, useEffect } from 'react';
import { apiClient } from '../utils/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';

const DriftDashboard = () => {
  const [driftReport, setDriftReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeWindow, setTimeWindow] = useState(1);

  useEffect(() => {
    fetchDriftData();
    const interval = setInterval(fetchDriftData, 15000); // Refresh every 15 seconds
    return () => clearInterval(interval);
  }, [timeWindow]);

  const fetchDriftData = async () => {
    try {
      const data = await apiClient.getDriftReport(timeWindow);
      setDriftReport(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching drift data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading drift data...</div>
      </div>
    );
  }

  if (!driftReport) {
    return (
      <div className="text-center text-slate-400 py-8">
        No drift data available
      </div>
    );
  }

  const featureDriftData = driftReport.feature_drift?.map(f => ({
    name: f.feature_name,
    psi: f.drift_score,
    threshold: driftReport.feature_drift[0]?.threshold || 0.25,
    status: f.status
  })) || [];

  const getBarColor = (status) => {
    switch (status) {
      case 'drifted': return '#ef4444';
      case 'stable': return '#10b981';
      default: return '#64748b';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Time Window Selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Drift Detection</h2>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-slate-400">Time Window:</span>
          <select
            value={timeWindow}
            onChange={(e) => setTimeWindow(Number(e.target.value))}
            className="bg-slate-800 text-white border border-slate-700 rounded px-3 py-2 text-sm"
          >
            <option value={1}>1 Hour</option>
            <option value={3}>3 Hours</option>
            <option value={6}>6 Hours</option>
            <option value={24}>24 Hours</option>
          </select>
        </div>
      </div>

      {/* Overall Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatusCard
          label="Data Drift"
          status={driftReport.overall_status?.data_drift_detected ? 'detected' : 'stable'}
        />
        <StatusCard
          label="Concept Drift"
          status={driftReport.overall_status?.concept_drift_detected ? 'detected' : 'stable'}
        />
        <StatusCard
          label="Performance"
          status={driftReport.overall_status?.performance_degraded ? 'degraded' : 'stable'}
        />
      </div>

      {/* Feature Drift Chart */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">Feature Drift (PSI Scores)</h3>
        <p className="text-sm text-slate-400 mb-6">
          PSI &lt; 0.1: No change | 0.1-0.25: Moderate | &gt; 0.25: Significant change
        </p>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={featureDriftData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="name"
              stroke="#94a3b8"
              angle={-45}
              textAnchor="end"
              height={100}
              style={{ fontSize: '12px' }}
            />
            <YAxis stroke="#94a3b8" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '0.5rem',
              }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Bar dataKey="psi" name="PSI Score">
              {featureDriftData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.status)} />
              ))}
            </Bar>
            <Bar dataKey="threshold" name="Threshold" fill="#fbbf24" opacity={0.3} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Feature Drift Details */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">Feature Drift Details</h3>
        <div className="space-y-4">
          {driftReport.feature_drift?.map((feature, index) => (
            <FeatureDriftCard key={index} feature={feature} />
          ))}
        </div>
      </div>

      {/* Prediction Drift */}
      {driftReport.prediction_drift && (
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Prediction Distribution Drift</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-slate-400">KS Statistic</p>
              <p className="text-2xl font-bold text-white">
                {driftReport.prediction_drift.statistic?.toFixed(4)}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-400">P-Value</p>
              <p className="text-2xl font-bold text-white">
                {driftReport.prediction_drift.p_value?.toFixed(4)}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-400">Baseline Fraud Rate</p>
              <p className="text-2xl font-bold text-blue-400">
                {(driftReport.prediction_drift.baseline_fraud_rate * 100)?.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-400">Current Fraud Rate</p>
              <p className={`text-2xl font-bold ${
                driftReport.prediction_drift.status === 'drifted' ? 'text-red-400' : 'text-green-400'
              }`}>
                {(driftReport.prediction_drift.current_fraud_rate * 100)?.toFixed(2)}%
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const StatusCard = ({ label, status }) => {
  const isGood = status === 'stable';
  const bgColor = isGood ? 'bg-green-500/10' : 'bg-red-500/10';
  const borderColor = isGood ? 'border-green-500/50' : 'border-red-500/50';
  const textColor = isGood ? 'text-green-400' : 'text-red-400';

  return (
    <div className={`${bgColor} rounded-lg p-4 border ${borderColor}`}>
      <p className="text-sm text-slate-400">{label}</p>
      <p className={`text-xl font-bold ${textColor} mt-2 capitalize`}>
        {status}
      </p>
    </div>
  );
};

const FeatureDriftCard = ({ feature }) => {
  const severityColors = {
    high: 'border-red-500/50 bg-red-500/5',
    medium: 'border-yellow-500/50 bg-yellow-500/5',
    low: 'border-blue-500/50 bg-blue-500/5',
    none: 'border-slate-700 bg-slate-800/50'
  };

  return (
    <div className={`p-4 rounded-lg border ${severityColors[feature.severity]}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="text-white font-medium">{feature.feature_name}</h4>
          <p className="text-sm text-slate-400 mt-1">
            PSI: {feature.drift_score?.toFixed(4)} | Status: {feature.status}
          </p>
        </div>
        <span className={`px-2 py-1 text-xs rounded ${
          feature.severity === 'high' ? 'bg-red-500 text-white' :
          feature.severity === 'medium' ? 'bg-yellow-500 text-black' :
          feature.severity === 'low' ? 'bg-blue-500 text-white' :
          'bg-slate-600 text-white'
        }`}>
          {feature.severity}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-slate-400">Baseline Mean</p>
          <p className="text-white font-mono">{feature.baseline_stats?.mean?.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-slate-400">Current Mean</p>
          <p className="text-white font-mono">{feature.current_stats?.mean?.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-slate-400">Mean Change</p>
          <p className={`font-mono ${
            Math.abs(feature.distribution_shift?.mean_change_pct || 0) > 20 ? 'text-red-400' : 'text-green-400'
          }`}>
            {feature.distribution_shift?.mean_change_pct?.toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-slate-400">Std Change</p>
          <p className="text-white font-mono">
            {feature.distribution_shift?.std_change_pct?.toFixed(1)}%
          </p>
        </div>
      </div>
    </div>
  );
};

export default DriftDashboard;

