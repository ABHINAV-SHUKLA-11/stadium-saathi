// React UMD imports are global: React, ReactDOM, lucide

const { useState, useEffect, useRef } = React;

// Simple helper to generate a session ID
function generateSessionId() {
    return 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
}

// ----------------------------------------------------
// Icon Component to wrapper Lucide icons
// ----------------------------------------------------
function Icon({ name, className = '', size = 20 }) {
    useEffect(() => {
        // Trigger lucide icon replacement
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }, [name]);
    return <i data-lucide={name} className={className} style={{ width: size, height: size, display: 'inline-block' }}></i>;
}

// ----------------------------------------------------
// SVG Stadium Map Component
// ----------------------------------------------------
function StadiumMap({ path = [], currentLocId = 'gate_a' }) {
    // Fictional coordinate map based on stadium_layout.json
    const nodes = {
        "gate_a": { x: 150, y: 35, name: "Gate A", type: "gate" },
        "gate_b": { x: 270, y: 150, name: "Gate B", type: "gate" },
        "gate_c": { x: 150, y: 265, name: "Gate C", type: "gate" },
        "gate_d": { x: 30, y: 150, name: "Gate D", type: "gate" },
        "ground_first_aid": { x: 150, y: 150, name: "Ground First Aid", type: "first_aid" },
        "esc_g1_ne": { x: 225, y: 75, name: "Escalator NE (G-L1)", type: "escalator" },
        "esc_g1_sw": { x: 75, y: 225, name: "Escalator SW (G-L1)", type: "escalator" },
        "l1_esc_g1_ne": { x: 225, y: 75, name: "Concourse NE", type: "escalator" },
        "l1_esc_g1_sw": { x: 75, y: 225, name: "Concourse SW", type: "escalator" },
        "food_stall_1": { x: 150, y: 50, name: "Burgers & Beers", type: "food_stall" },
        "food_stall_2": { x: 250, y: 150, name: "Taco Time", type: "food_stall" },
        "food_stall_3": { x: 150, y: 250, name: "Curry Express", type: "food_stall" },
        "food_stall_4": { x: 50, y: 150, name: "Cafe Paris", type: "food_stall" },
        "washroom_l1_east": { x: 240, y: 120, name: "L1 East Washroom", type: "washroom" },
        "washroom_l1_west": { x: 60, y: 180, name: "L1 West Washroom", type: "washroom" },
        "section_101": { x: 195, y: 105, name: "Section 101", type: "section" },
        "section_102": { x: 195, y: 195, name: "Section 102", type: "section" },
        "section_103": { x: 105, y: 195, name: "Section 103", type: "section" },
        "section_104": { x: 105, y: 105, name: "Section 104", type: "section" },
        "l1_esc_12_nw": { x: 75, y: 75, name: "Escalator NW (L1-L2)", type: "escalator" },
        "l1_esc_12_se": { x: 225, y: 225, name: "Escalator SE (L1-L2)", type: "escalator" },
        "l2_esc_12_nw": { x: 75, y: 75, name: "Upper NW", type: "escalator" },
        "l2_esc_12_se": { x: 225, y: 225, name: "Upper SE", type: "escalator" },
        "food_stall_5": { x: 210, y: 60, name: "Halal Cart", type: "food_stall" },
        "food_stall_6": { x: 90, y: 240, name: "Pizza Palace", type: "food_stall" },
        "washroom_l2_north": { x: 135, y: 45, name: "L2 North Washroom", type: "washroom" },
        "washroom_l2_south": { x: 165, y: 255, name: "L2 South Washroom", type: "washroom" },
        "section_201": { x: 150, y: 75, name: "Section 201", type: "section" },
        "section_202": { x: 225, y: 150, name: "Section 202", type: "section" },
        "section_203": { x: 150, y: 225, name: "Section 203", type: "section" },
        "section_204": { x: 75, y: 150, name: "Section 204", type: "section" }
    };

    // Draw active path links
    const pathLinks = [];
    for (let i = 0; i < path.length - 1; i++) {
        const startNode = nodes[path[i].location_id];
        const endNode = nodes[path[i+1].location_id];
        if (startNode && endNode) {
            pathLinks.push(
                <line 
                    key={`link-${i}`} 
                    x1={startNode.x} 
                    y1={startNode.y} 
                    x2={endNode.x} 
                    y2={endNode.y} 
                    className="svg-connection path"
                />
            );
        }
    }

    return (
        <div className="map-card glass-card">
            <h3 className="card-title">
                <Icon name="map" className="text-blue" /> Stadium Map Preview
            </h3>
            <div className="map-container">
                <svg viewBox="0 0 300 300" className="stadium-svg">
                    {/* Fictional Pitch Outer Rim */}
                    <rect x="90" y="90" width="120" height="120" rx="60" className="svg-stadium-ring" />
                    <rect x="110" y="110" width="80" height="80" rx="40" style={{ fill: 'none', stroke: 'rgba(255,255,255,0.03)', strokeWidth: 4 }} />
                    
                    {/* Draw Grid Zones */}
                    {/* North Zone */}
                    <path d="M 30,30 L 270,30 L 150,150 Z" className="svg-zone" style={{ fill: 'rgba(0, 212, 255, 0.005)' }} />
                    
                    {/* Draw connections */}
                    {Object.keys(nodes).map(nodeId => {
                        const node = nodes[nodeId];
                        return node.nearby_ids?.map((nearId, idx) => {
                            const target = nodes[nearId];
                            if (target) {
                                return (
                                    <line 
                                        key={`${nodeId}-conn-${idx}`} 
                                        x1={node.x} 
                                        y1={node.y} 
                                        x2={target.x} 
                                        y2={target.y} 
                                        className="svg-connection" 
                                    />
                                );
                            }
                            return null;
                        });
                    })}

                    {/* Draw calculated path links */}
                    {pathLinks}

                    {/* Draw nodes */}
                    {Object.keys(nodes).map(nodeId => {
                        const node = nodes[nodeId];
                        const isCurrent = nodeId === currentLocId;
                        const isPartOfPath = path.some(p => p.location_id === nodeId);
                        
                        let fillVal = 'rgba(255, 255, 255, 0.2)';
                        let strokeVal = 'rgba(255,255,255,0.4)';
                        let size = 4;
                        
                        if (isCurrent) {
                            fillVal = '#00d4ff';
                            strokeVal = '#00d4ff';
                            size = 8;
                        } else if (isPartOfPath) {
                            fillVal = '#00ff87';
                            strokeVal = '#00ff87';
                            size = 6;
                        } else if (node.type === 'gate') {
                            fillVal = '#9aa4bf';
                            size = 5;
                        } else if (node.type === 'food_stall') {
                            fillVal = '#ffb700';
                            size = 4.5;
                        } else if (node.type === 'first_aid') {
                            fillVal = '#ff3b30';
                            size = 6;
                        } else if (node.type === 'washroom') {
                            fillVal = '#ae00ff';
                            size = 4.5;
                        }

                        return (
                            <g key={nodeId} className="svg-node">
                                <circle 
                                    cx={node.x} 
                                    cy={node.y} 
                                    r={size} 
                                    fill={fillVal} 
                                    stroke={strokeVal} 
                                    strokeWidth={isCurrent || isPartOfPath ? 2 : 0} 
                                />
                                {(isCurrent || isPartOfPath) && (
                                    <text 
                                        x={node.x} 
                                        y={node.y - 10} 
                                        textAnchor="middle" 
                                        style={{ fill: '#f1f3f9', fontSize: '8px', fontWeight: 600, fontFamily: 'Outfit' }}
                                    >
                                        {node.name}
                                    </text>
                                )}
                            </g>
                        );
                    })}
                </svg>
            </div>
            <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#00d4ff' }}></span> Start
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#00ff87' }}></span> Route
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ffb700' }}></span> Food
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ff3b30' }}></span> Medical
                </span>
            </div>
        </div>
    );
}

// ----------------------------------------------------
// Fan Chat Page Component
// ----------------------------------------------------
function FanChat({ sessionId, crowdData, currentLoc, setCurrentLoc }) {
    const [messages, setMessages] = useState([
        {
            sender: 'assistant',
            text: 'Hello! Namaste! ¡Hola! I am "Stadium Saathi", your smart GenAI-powered assistant for FIFA World Cup 2026. Ask me questions about facilities, washrooms, food stalls, gates, or seek directions in Hindi, English, Spanish, Arabic, or any other language.',
            detected_language: 'English',
            intent: 'greeting',
            is_emergency: false
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const chatEndRef = useRef(null);

    const quickChips = [
        "🚻 Find nearest Washroom",
        "🍔 Where is Burgers & Beers?",
        "📍 Directions to Section 102",
        "🚑 Where is First-Aid?",
        "🚶 How do I get to Gate D?"
    ];

    const activeNavigationSteps = messages[messages.length - 1]?.navigation_steps || [];

    useEffect(() => {
        // Auto-scroll chat to bottom
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    const handleSend = async (messageText) => {
        const text = messageText || input;
        if (!text.trim()) return;

        setInput('');
        setLoading(true);

        // Add user message to state
        const userMsg = {
            sender: 'user',
            text: text
        };
        setMessages(prev => [...prev, userMsg]);

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    session_id: sessionId,
                    current_location_id: currentLoc
                })
            });
            const data = await res.json();

            // Add assistant response to state
            setMessages(prev => [...prev, {
                sender: 'assistant',
                text: data.response,
                detected_language: data.detected_language,
                intent: data.intent,
                is_emergency: data.is_emergency,
                navigation_steps: data.navigation_steps,
                crowd_alert: data.crowd_alert
            }]);
        } catch (error) {
            console.error("Error sending chat:", error);
            setMessages(prev => [...prev, {
                sender: 'assistant',
                text: "Sorry, I had trouble connecting to my central stadium system. Please try again.",
                detected_language: "English",
                intent: "other",
                is_emergency: false
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-page">
            <div className="chat-section glass-card">
                <div className="chat-history">
                    {messages.map((msg, index) => (
                        <div key={index} className={`message-row ${msg.sender} ${msg.is_emergency ? 'emergency' : ''}`}>
                            <div style={{ display: 'flex', flexDirection: 'column', maxWidth: '75%' }}>
                                <div className="message-bubble">
                                    <p>{msg.text}</p>
                                    
                                    {/* Render navigation steps box inside chat bubbles if present */}
                                    {msg.navigation_steps && msg.navigation_steps.length > 0 && (
                                        <div className="nav-steps-box">
                                            <div className="nav-steps-header">
                                                <Icon name="navigation" size={14} /> Path Directions
                                            </div>
                                            {msg.navigation_steps.map((step, idx) => (
                                                <div key={idx} className="nav-step-item">
                                                    <div className="nav-step-icon">{idx + 1}</div>
                                                    <div className="nav-step-content">
                                                        <span>{step.instruction}</span>
                                                        <span className="nav-step-badge">Level {step.level} • {step.zone} Zone</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                {msg.sender === 'assistant' && (
                                    <div className="message-meta">
                                        <span className="meta-badge">Language: {msg.detected_language}</span>
                                        <span className="meta-badge">Intent: {msg.intent}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="message-row assistant">
                            <div className="message-bubble">
                                <div className="typing-indicator">
                                    <span className="typing-dot"></span>
                                    <span className="typing-dot"></span>
                                    <span className="typing-dot"></span>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>

                <div className="chat-input-area">
                    <div className="quick-queries">
                        {quickChips.map((chip, idx) => (
                            <button key={idx} className="query-chip" onClick={() => handleSend(chip.substring(2))} disabled={loading}>
                                {chip}
                            </button>
                        ))}
                    </div>
                    <div className="input-box-wrapper">
                        {/* Current start location selector to simulate navigation inputs */}
                        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                            <label style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Current Gate:</label>
                            <select 
                                value={currentLoc} 
                                onChange={(e) => setCurrentLoc(e.target.value)}
                                style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '0.25rem', fontSize: '0.75rem' }}
                            >
                                <option value="gate_a">Gate A (North)</option>
                                <option value="gate_b">Gate B (East)</option>
                                <option value="gate_c">Gate C (South)</option>
                                <option value="gate_d">Gate D (West)</option>
                            </select>
                        </div>
                        <input
                            type="text"
                            className="chat-input"
                            placeholder="Type a question in any language (e.g., 'mujhe section 102 jaana hai')..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            disabled={loading}
                        />
                        <button className="send-btn" onClick={() => handleSend()} disabled={loading}>
                            <Icon name="send" className="text-dark" size={18} />
                        </button>
                    </div>
                </div>
            </div>

            <div className="info-sidebar">
                {/* Real-time Crowd Warning Alerts */}
                <div className="crowd-alerts-card glass-card">
                    <h3 className="card-title">
                        <Icon name="alert-triangle" className="text-amber" /> Live Crowd Conditions
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {crowdData.length === 0 ? (
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Connecting to crowd tracking sensors...</p>
                        ) : (
                            crowdData.map(zone => {
                                const isCritical = zone.density > 90;
                                const isHigh = zone.density > 75 && zone.density <= 90;
                                const statusClass = isCritical ? 'critical' : (isHigh ? 'warning' : '');
                                return (
                                    <div key={zone.zone_id} className={`alert-indicator ${statusClass}`}>
                                        <span className={`alert-status-dot ${zone.status.toLowerCase()}`}></span>
                                        <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                                            <span style={{ fontWeight: 600 }}>{zone.zone_id} Zone</span>
                                            <span style={{ color: isCritical ? 'var(--accent-red)' : (isHigh ? 'var(--accent-amber)' : 'var(--text-secondary)') }}>
                                                {zone.status} ({zone.density}%)
                                            </span>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* SVG Stadium Map Navigation */}
                <StadiumMap path={activeNavigationSteps} currentLocId={currentLoc} />
            </div>
        </div>
    );
}

// ----------------------------------------------------
// Staff Dashboard Page Component
// ----------------------------------------------------
function StaffDashboard({ crowdData }) {
    const [stats, setStats] = useState(null);
    const [frequentQueries, setFrequentQueries] = useState([]);
    const [emergencies, setEmergencies] = useState([]);
    const [error, setError] = useState('');
    
    const fetchStats = async () => {
        const token = localStorage.getItem('saathi_token');
        if (!token) return;

        try {
            const headers = { 'Authorization': `Bearer ${token}` };
            
            const statsRes = await fetch('/api/dashboard/stats', { headers });
            if (!statsRes.ok) throw new Error("Unauthorized");
            const statsData = await statsRes.json();
            setStats(statsData);

            const freqRes = await fetch('/api/dashboard/frequent-queries', { headers });
            const freqData = await freqRes.json();
            setFrequentQueries(freqData);

            const emergRes = await fetch('/api/dashboard/emergencies', { headers });
            const emergData = await emergRes.json();
            setEmergencies(emergData);
        } catch (err) {
            console.error("Dashboard data load error:", err);
            setError("Session expired or unauthorized. Please re-authenticate.");
            localStorage.removeItem('saathi_token');
        }
    };

    useEffect(() => {
        fetchStats();
        // Poll dashboard logs and statistics every 8 seconds
        const interval = setInterval(fetchStats, 8000);
        return () => clearInterval(interval);
    }, []);

    if (error) {
        return (
            <div className="dashboard-page text-center">
                <div className="glass-card" style={{ padding: '2rem', maxWidth: '400px', margin: '100px auto' }}>
                    <Icon name="lock" size={48} className="text-red" style={{ marginBottom: '1rem' }} />
                    <p style={{ marginBottom: '1.5rem' }}>{error}</p>
                    <button className="auth-btn" onClick={() => window.location.reload()}>Re-Login</button>
                </div>
            </div>
        );
    }

    if (!stats) {
        return (
            <div className="dashboard-page text-center">
                <div style={{ margin: '150px auto' }}>
                    <div className="typing-indicator" style={{ justifyContent: 'center' }}>
                        <span className="typing-dot"></span>
                        <span className="typing-dot"></span>
                        <span className="typing-dot"></span>
                    </div>
                    <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Loading Dashboard Analytics...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-page">
            <div className="dashboard-header">
                <div>
                    <h2>Stadium Command & Response</h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Real-time crowd tracking and GenAI assistant logs</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <span className="brand-badge" style={{ backgroundColor: 'rgba(0, 255, 135, 0.1)', color: 'var(--accent-green)', borderColor: 'rgba(0, 255, 135, 0.2)' }}>
                        ● Live Sensors Connected
                    </span>
                </div>
            </div>

            {/* Total metric cards row */}
            <div className="stats-grid">
                <div className="stat-card glass-card">
                    <div className="stat-info">
                        <span className="stat-value">{stats.total_queries}</span>
                        <span className="stat-label">Total Fan Chats</span>
                    </div>
                    <div className="stat-icon-box blue">
                        <Icon name="message-square" size={24} />
                    </div>
                </div>

                <div className="stat-card glass-card">
                    <div className="stat-info">
                        <span className="stat-value">{stats.active_sessions}</span>
                        <span className="stat-label">Active Users</span>
                    </div>
                    <div className="stat-icon-box green">
                        <Icon name="users" size={24} />
                    </div>
                </div>

                <div className="stat-card glass-card" style={{ borderColor: stats.emergency_count > 0 ? 'rgba(255, 59, 48, 0.4)' : 'var(--border-color)' }}>
                    <div className="stat-info">
                        <span className="stat-value" style={{ color: stats.emergency_count > 0 ? 'var(--accent-red)' : 'var(--text-primary)' }}>
                            {stats.emergency_count}
                        </span>
                        <span className="stat-label">Flagged Emergencies</span>
                    </div>
                    <div className={stats.emergency_count > 0 ? 'stat-icon-box red' : 'stat-icon-box amber'}>
                        <Icon name="shield-alert" size={24} />
                    </div>
                </div>
            </div>

            {/* Heatmap and emergency panel */}
            <div className="analytics-grid">
                <div className="heatmap-card glass-card">
                    <h3 className="card-title">
                        <Icon name="activity" className="text-blue" /> Stadium Zone Density Heatmap
                    </h3>
                    <div className="grid-stadium-layout">
                        {/* Grid cells representing physical zone layout */}
                        {crowdData.map(zone => {
                            const isCritical = zone.density > 90;
                            const isHigh = zone.density > 75 && zone.density <= 90;
                            const isMedium = zone.density > 40 && zone.density <= 75;
                            const densityClass = isCritical ? 'density-critical' : (isHigh ? 'density-high' : (isMedium ? 'density-medium' : 'density-low'));
                            
                            return (
                                <div key={zone.zone_id} className={`zone-grid-cell ${densityClass}`}>
                                    <span className="zone-name">{zone.zone_id}</span>
                                    <span className="zone-percentage">{zone.density}%</span>
                                    <div className="zone-status-bar"></div>
                                </div>
                            );
                        })}
                        {/* Center field spacer */}
                        <div className="zone-grid-cell center-field">
                            <span style={{ fontSize: '0.8rem' }}>PITCH</span>
                        </div>
                    </div>
                </div>

                <div className="emergency-card glass-card">
                    <h3 className="card-title" style={{ color: 'var(--accent-red)' }}>
                        <Icon name="heart-handshake" className="text-red" /> Staff Emergency Alerts
                    </h3>
                    <div className="emergency-feed">
                        {emergencies.length === 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                                <Icon name="check-circle" size={40} className="text-green" style={{ marginBottom: '0.5rem' }} />
                                <p style={{ fontSize: '0.85rem' }}>No active emergency flags.</p>
                            </div>
                        ) : (
                            emergencies.map(log => (
                                <div key={log.id} className="emergency-item">
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span className="emergency-time">
                                            {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                        </span>
                                        <span className="brand-badge" style={{ fontSize: '0.6rem', padding: '0.05rem 0.25rem', backgroundColor: 'rgba(255, 59, 48, 0.1)', color: 'var(--accent-red)', borderColor: 'rgba(255, 59, 48, 0.2)' }}>
                                            {log.detected_language}
                                        </span>
                                    </div>
                                    <p className="emergency-text"><strong>User:</strong> "{log.fan_message}"</p>
                                    <p className="emergency-response"><strong>AI response:</strong> {log.ai_response}</p>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Bottom Row - Frequent queries & Language Distribution */}
            <div className="queries-row">
                <div className="panel-card glass-card">
                    <h3 className="card-title">
                        <Icon name="bar-chart-2" className="text-green" /> Frequently Asked Fan Intents
                    </h3>
                    <div className="frequent-list">
                        {frequentQueries.length === 0 ? (
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No data logged yet.</p>
                        ) : (
                            frequentQueries.map((item, idx) => (
                                <div key={idx} className="frequent-item">
                                    <span className="frequent-intent">{item.intent.replace('_', ' ')}</span>
                                    <span className="frequent-count">{item.count} hits</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className="panel-card glass-card">
                    <h3 className="card-title">
                        <Icon name="languages" className="text-blue" /> Language Distribution
                    </h3>
                    <div className="lang-list">
                        {Object.keys(stats.language_breakdown).length === 0 ? (
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No data logged yet.</p>
                        ) : (
                            Object.keys(stats.language_breakdown).map(lang => {
                                const count = stats.language_breakdown[lang];
                                const percentage = Math.round((count / stats.total_queries) * 100);
                                return (
                                    <div key={lang} className="lang-item">
                                        <div className="lang-header">
                                            <span style={{ fontWeight: 600 }}>{lang}</span>
                                            <span style={{ color: 'var(--text-secondary)' }}>{count} ({percentage}%)</span>
                                        </div>
                                        <div className="lang-progress-bg">
                                            <div className="lang-progress-fill" style={{ width: `${percentage}%` }}></div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

// ----------------------------------------------------
// Password Login Overlay Component
// ----------------------------------------------------
function PasswordGate({ onAuthSuccess }) {
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const res = await fetch('/api/dashboard/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });
            const data = await res.json();

            if (data.success) {
                localStorage.setItem('saathi_token', data.token);
                onAuthSuccess(data.token);
            } else {
                setError(data.message || 'Invalid Admin Password.');
            }
        } catch (err) {
            console.error("Login request failed:", err);
            setError('System error verifying password. Please check backend connection.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-overlay">
            <div className="auth-card glass-card">
                <div className="auth-icon">
                    <Icon name="lock" size={28} />
                </div>
                <div className="auth-title">Staff Dashboard</div>
                <div className="auth-desc">Please enter the administration password to access real-time crowd metrics and user alerts.</div>
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <input
                        type="password"
                        className="auth-input"
                        placeholder="••••••••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        disabled={loading}
                        autoFocus
                    />
                    {error && <span className="auth-error">{error}</span>}
                    <button type="submit" className="auth-btn" disabled={loading}>
                        {loading ? 'Authenticating...' : 'Access Dashboard'}
                    </button>
                </form>
            </div>
        </div>
    );
}

// ----------------------------------------------------
// Root App Controller Component
// ----------------------------------------------------
function App() {
    const [page, setPage] = useState('fan'); // 'fan' or 'dashboard'
    const [sessionId] = useState(generateSessionId());
    const [crowdData, setCrowdData] = useState([]);
    const [authToken, setAuthToken] = useState(localStorage.getItem('saathi_token') || '');
    const [currentLoc, setCurrentLoc] = useState('gate_a');

    useEffect(() => {
        // SSE connection for real-time crowd updates
        const sse = new EventSource('/api/crowd/stream');
        
        sse.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // Sort zones consistently for display
                const sorted = data.sort((a, b) => a.zone_id.localeCompare(b.zone_id));
                setCrowdData(sorted);
            } catch (err) {
                console.error("Error parsing crowd SSE event:", err);
            }
        };

        sse.onerror = (err) => {
            console.error("Crowd stream SSE error, reconnecting:", err);
        };

        return () => {
            sse.close();
        };
    }, []);

    return (
        <div className="app-container">
            <nav className="navbar">
                <div className="brand">
                    <div className="brand-logo">⚽</div>
                    <div>
                        <span className="brand-name">Stadium Saathi</span>
                        <span className="brand-badge" style={{ marginLeft: '0.5rem' }}>FIFA 2026</span>
                    </div>
                </div>
                <div className="nav-links">
                    <button 
                        className={`nav-btn ${page === 'fan' ? 'active' : ''}`} 
                        onClick={() => setPage('fan')}
                    >
                        <Icon name="message-square" size={16} /> Fan Assistant
                    </button>
                    <button 
                        className={`nav-btn ${page === 'dashboard' ? 'active' : ''}`} 
                        onClick={() => setPage('dashboard')}
                    >
                        <Icon name="line-chart" size={16} /> Staff Dashboard
                    </button>
                </div>
            </nav>

            {page === 'fan' ? (
                <FanChat 
                    sessionId={sessionId} 
                    crowdData={crowdData} 
                    currentLoc={currentLoc}
                    setCurrentLoc={setCurrentLoc}
                />
            ) : (
                !authToken ? (
                    <PasswordGate onAuthSuccess={(token) => setAuthToken(token)} />
                ) : (
                    <StaffDashboard crowdData={crowdData} />
                )
            )}
        </div>
    );
}

// Render React App
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
