import React, { useState, useEffect } from 'react';
import { apiClient } from '../utils/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const PerformanceMetrics = () => {
  const [metricsData, setMetricsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(24);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 15000);
    return () => clearInterval(interval);
  }, [timeRange]);

  const fetchMetrics = async () => {
    try {
      const endTime = new Date().toISOString();
      const startTime = new Date(Date.now() - timeRange * 60 * 60 * 1000).toISOString();
      
      const data = await apiClient.getMetricsTimeseries(startTime, endTime, '1h');
      setMetricsData(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching metrics:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading performance metrics...</div>
      </div>
    );
  }

  const chartData = metricsData?.data_points?.map(point => ({
    time: new Date(point.timestamp).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    }),
    accuracy: point.accuracy ? (point.accuracy * 100).toFixed(2) : null,
    precision: point.precision ? (point.precision * 100).toFixed(2) : null,
    recall: point.recall ? (point.recall * 100).toFixed(2) : null,
    auc: point.auc_roc ? (point.auc_roc * 100).toFixed(2) : null,
    psi: point.max_psi,
    predictions: point.predictions_count,
  })) || [];

  const latestMetrics = chartData[chartData.length - 1] || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Performance Metrics</h2>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-slate-400">Time Range:</span>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="bg-slate-800 text-white border border-slate-700 rounded px-3 py-2 text-sm"
          >
            <option value={6}>6 Hours</option>
            <option value={12}>12 Hours</option>
            <option value={24}>24 Hours</option>
            <option value={72}>3 Days</option>
          </select>
        </div>
      </div>

      {/* Current Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <MetricCard
          label="Accuracy"
          value={latestMetrics.accuracy}
          unit="%"
          color="text-blue-400"
        />
        <MetricCard
          label="Precision"
          value={latestMetrics.precision}
          unit="%"
          color="text-green-400"
        />
        <MetricCard
          label="Recall"
          value={latestMetrics.recall}
          unit="%"
          color="text-purple-400"
        />
        <MetricCard
          label="AUC-ROC"
          value={latestMetrics.auc}
          unit="%"
          color="text-yellow-400"
        />
        <MetricCard
          label="Max PSI"
          value={latestMetrics.psi?.toFixed(3)}
          unit=""
          color="text-red-400"
        />
      </div>

      {/* Model Performance Over Time */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">
          Model Performance Over Time
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="time"
              stroke="#94a3b8"
              style={{ fontSize: '12px' }}
            />
            <YAxis stroke="#94a3b8" domain={[0, 100]} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '0.5rem',
              }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="accuracy"
              name="Accuracy"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="precision"
              name="Precision"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="recall"
              name="Recall"
              stroke="#a855f7"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="auc"
              name="AUC-ROC"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Prediction Volume */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">
          Prediction Volume
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="time"
              stroke="#94a3b8"
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
            <Legend />
            <Line
              type="monotone"
              dataKey="predictions"
              name="Predictions/Hour"
              stroke="#06b6d4"
              strokeWidth={2}
              dot={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Drift Score Trend */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">
          Drift Score Trend (PSI)
        </h3>
        <p className="text-sm text-slate-400 mb-4">
          Threshold: 0.25 (values above indicate significant drift)
        </p>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="time"
              stroke="#94a3b8"
              style={{ fontSize: '12px' }}
            />
            <YAxis stroke="#94a3b8" domain={[0, 'auto']} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '0.5rem',
              }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="psi"
              name="Max PSI"
              stroke="#ef4444"
              strokeWidth={2}
              dot={true}
            />
            {/* Threshold line */}
            <Line
              type="monotone"
              data={chartData.map(d => ({ ...d, threshold: 0.25 }))}
              dataKey="threshold"
              name="Threshold"
              stroke="#fbbf24"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

const MetricCard = ({ label, value, unit, color }) => {
  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <p className="text-sm text-slate-400">{label}</p>
      <p className={`text-2xl font-bold ${color} mt-2`}>
        {value !== null && value !== undefined ? `${value}${unit}` : 'N/A'}
      </p>
    </div>
  );
};

export default PerformanceMetrics;

