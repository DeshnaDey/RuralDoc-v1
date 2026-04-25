'use client';

import React, { useState, useEffect, useRef } from 'react';

export default function BackendTester() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [status, setStatus] = useState('Disconnected');
  const [logs, setLogs] = useState<{ type: string; message: string; timestamp: string }[]>([]);
  const [customJson, setCustomJson] = useState('{\n  "type": "order_test",\n  "test_name": "blood_pressure"\n}');
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const addLog = (type: 'System' | 'Sent' | 'Received', message: string) => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { type, message, timestamp: time }]);
  };

  const connect = () => {
    if (ws) ws.close();
    
    // Assuming your FastAPI server runs on 8000
    const socket = new WebSocket('ws://localhost:8000/ws'); 
    
    socket.onopen = () => {
      setStatus('Connected');
      addLog('System', 'Connected to ws://localhost:8000/ws');
    };
    
    socket.onmessage = (event) => {
      // Try to pretty-print JSON if possible
      try {
        const parsed = JSON.parse(event.data);
        addLog('Received', JSON.stringify(parsed, null, 2));
      } catch {
        addLog('Received', event.data);
      }
    };
    
    socket.onclose = () => {
      setStatus('Disconnected');
      addLog('System', 'Connection closed');
      setWs(null);
    };

    socket.onerror = (error) => {
      addLog('System', 'WebSocket Error. Is the Python backend running?');
    };

    setWs(socket);
  };

  const disconnect = () => {
    if (ws) ws.close();
  };

  const sendPayload = (payload: any) => {
    if (!ws || status !== 'Connected') {
      addLog('System', 'Cannot send: Not connected to backend.');
      return;
    }
    const message = JSON.stringify(payload);
    ws.send(message);
    addLog('Sent', JSON.stringify(payload, null, 2));
  };

  return (
    <div className="h-screen flex flex-col bg-slate-900 text-slate-300 font-mono text-sm">
      
      {/* Header Bar */}
      <div className="bg-slate-950 p-4 border-b border-slate-800 flex justify-between items-center z-10">
        <div>
          <h1 className="text-lg font-bold text-teal-400">RuralDoc Backend Tester</h1>
          <p className="text-xs text-slate-500">WebSocket / RL Environment Console</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className={`h-3 w-3 rounded-full ${status === 'Connected' ? 'bg-teal-500 shadow-[0_0_8px_rgba(20,184,166,0.8)]' : 'bg-red-500'}`}></span>
            <span className="font-semibold">{status}</span>
          </div>
          {status === 'Connected' ? (
            <button onClick={disconnect} className="bg-red-900/50 hover:bg-red-900 text-red-200 px-4 py-2 rounded transition-colors border border-red-800">Disconnect</button>
          ) : (
            <button onClick={connect} className="bg-teal-900/50 hover:bg-teal-900 text-teal-200 px-4 py-2 rounded transition-colors border border-teal-800">Connect to Backend</button>
          )}
        </div>
      </div>

      {/* Main Console Area */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Panel: Logs */}
        <div className="flex-1 border-r border-slate-800 flex flex-col bg-slate-950/50">
          <div className="p-3 border-b border-slate-800 font-bold text-slate-400 bg-slate-900">Communication Log</div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {logs.length === 0 && <p className="text-slate-600 italic">No activity yet. Connect and send an action.</p>}
            
            {logs.map((log, i) => (
              <div key={i} className="flex flex-col">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                    log.type === 'Sent' ? 'bg-blue-900/50 text-blue-400' : 
                    log.type === 'Received' ? 'bg-teal-900/50 text-teal-400' : 
                    'bg-slate-800 text-slate-400'
                  }`}>
                    {log.type}
                  </span>
                  <span className="text-xs text-slate-600">{log.timestamp}</span>
                </div>
                <pre className="bg-slate-900 p-3 rounded border border-slate-800 text-slate-300 overflow-x-auto whitespace-pre-wrap">
                  {log.message}
                </pre>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>

        {/* Right Panel: Controls */}
        <div className="w-96 flex flex-col bg-slate-900">
          <div className="p-3 border-b border-slate-800 font-bold text-slate-400">Quick Actions</div>
          
          <div className="p-4 space-y-4 border-b border-slate-800">
            <button 
              onClick={() => sendPayload({ type: "reset" })}
              className="w-full bg-slate-800 hover:bg-slate-700 p-2 rounded text-left border border-slate-700 transition-colors"
            >
              <span className="block font-bold text-slate-200">env.reset()</span>
              <span className="text-xs text-slate-500">Initialize a new patient scenario</span>
            </button>
            
            <button 
              onClick={() => sendPayload({ type: "order_test", test_name: "rapid_malaria_test" })}
              className="w-full bg-slate-800 hover:bg-slate-700 p-2 rounded text-left border border-slate-700 transition-colors"
            >
              <span className="block font-bold text-blue-300">env.step(order_test)</span>
              <span className="text-xs text-slate-500">Test: rapid_malaria_test</span>
            </button>

            <button 
              onClick={() => sendPayload({ type: "diagnose", diagnosis: "malaria" })}
              className="w-full bg-slate-800 hover:bg-slate-700 p-2 rounded text-left border border-slate-700 transition-colors"
            >
              <span className="block font-bold text-teal-300">env.step(diagnose)</span>
              <span className="text-xs text-slate-500">Diagnosis: malaria</span>
            </button>
          </div>

          <div className="p-4 flex-1 flex flex-col">
            <label className="font-bold text-slate-400 mb-2 block">Custom JSON Payload</label>
            <textarea 
              value={customJson}
              onChange={(e) => setCustomJson(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-800 rounded p-3 text-slate-300 focus:outline-none focus:border-teal-500 resize-none font-mono text-xs"
              spellCheck="false"
            />
            <button 
              onClick={() => {
                try {
                  const payload = JSON.parse(customJson);
                  sendPayload(payload);
                } catch {
                  addLog('System', 'Invalid JSON syntax. Please fix and try again.');
                }
              }}
              className="mt-4 bg-teal-600 hover:bg-teal-500 text-white font-bold py-2 px-4 rounded transition-colors"
            >
              Send Custom Action
            </button>
            <button 
              onClick={() => setLogs([])}
              className="mt-2 text-slate-500 hover:text-slate-300 text-xs py-2 transition-colors"
            >
              Clear Logs
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}